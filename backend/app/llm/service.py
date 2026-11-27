"""Chat flow: propose, validate, review, execute, persist."""

import logging

import db
from app.market import normalize_ticker
from app.services import portfolio, watchlist
from app.services.errors import ServiceError

from . import client, mock
from .schemas import ProposerResponse, ReviewerResponse

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 10
UNAVAILABLE_MESSAGE = "Sorry, the AI assistant is unavailable right now. Please try again."
MISSING_KEY_MESSAGE = "The AI assistant is unavailable: OPENROUTER_API_KEY is not set."
REVIEW_FAILED_REASON = "The safety review failed, so this action was not executed."
NO_VERDICT_REASON = "The reviewer did not return a verdict."
INTERNAL_REASON = "Something went wrong while processing this action."


async def handle_chat(state, user_id: str, user_message: str) -> dict:
    """Run one chat turn and return the POST /api/chat response."""
    history = db.list_chat_messages(user_id, limit=HISTORY_LIMIT)
    db.add_chat_message(user_id, "user", user_message)

    try:
        proposal = await _propose(state, user_id, history, user_message)
    except client.LLMError as exc:
        logger.warning("Proposer failed: %s", exc)
        missing_key = isinstance(exc, client.MissingAPIKeyError)
        message = MISSING_KEY_MESSAGE if missing_key else UNAVAILABLE_MESSAGE
        return _reply(user_id, message, [], [], "llm_unavailable")

    trades = [_trade_result(t) for t in proposal.trades]
    changes = [_change_result(c) for c in proposal.watchlist_changes]

    # Deterministic validation: only survivors reach the reviewer.
    survivors = [r for r in changes if _validate_change(state, user_id, r)]
    survivors += [r for r in trades if _validate_trade(state, user_id, r)]

    summary, error = None, None
    if survivors:
        try:
            previous = next(
                (m["content"] for m in reversed(history) if m["role"] == "assistant"), None
            )
            verdicts = await _review(state, user_id, user_message, survivors, previous)
            summary = verdicts.summary
            _apply_verdicts(survivors, verdicts)
        except client.LLMError as exc:
            logger.warning("Reviewer failed: %s", exc)
            error = "review_failed"
            for result in survivors:
                _reject(result, REVIEW_FAILED_REASON)
                result["review"] = {"verdict": "reject", "reason": REVIEW_FAILED_REASON}

    # Watchlist changes first, then trades; each stands alone.
    for result in changes:
        if _approved(result):
            await _execute_change(state, user_id, result)
    for result in trades:
        if _approved(result):
            await _execute_trade(state, user_id, result)

    message = _compose_message(proposal.message, summary, trades, changes)
    return _reply(user_id, message, trades, changes, error)


async def _propose(state, user_id: str, history: list[dict], user_message: str) -> ProposerResponse:
    if mock.is_enabled():
        return mock.propose(user_message)
    return await client.propose(
        portfolio.get_portfolio(state, user_id),
        watchlist.get_watchlist(state, user_id),
        history,
        user_message,
    )


async def _review(
    state, user_id: str, user_message: str, survivors: list[dict], previous_reply: str | None
) -> ReviewerResponse:
    actions = [_describe(index, result) for index, result in enumerate(survivors)]
    if mock.is_enabled():
        return mock.review(user_message, actions)
    account = portfolio.get_portfolio(state, user_id)
    return await client.review(account, user_message, actions, previous_reply)


def _trade_result(trade) -> dict:
    return {
        "ticker": normalize_ticker(trade.ticker),
        "side": trade.side,
        "quantity": trade.quantity,
        "amount": trade.amount,
        "status": "rejected",
        "price": None,
        "reason": None,
        "review": None,
    }


def _change_result(change) -> dict:
    return {
        "ticker": normalize_ticker(change.ticker),
        "action": change.action,
        "status": "rejected",
        "reason": None,
        "review": None,
    }


def _reject(result: dict, reason: str) -> None:
    result["status"] = "rejected"
    result["reason"] = reason


def _validate_trade(state, user_id: str, result: dict) -> bool:
    try:
        portfolio.check_trade(
            state,
            user_id,
            result["ticker"],
            result["side"],
            result["quantity"],
            result["amount"],
        )
    except ServiceError as exc:
        _reject(result, exc.message)
        return False
    except Exception:
        logger.exception("Trade validation failed")
        _reject(result, INTERNAL_REASON)
        return False
    return True


def _validate_change(state, user_id: str, result: dict) -> bool:
    try:
        result["ticker"] = watchlist.check_change(
            state, user_id, result["ticker"], result["action"]
        )
    except ServiceError as exc:
        _reject(result, exc.message)
        return False
    except Exception:
        logger.exception("Watchlist validation failed")
        _reject(result, INTERNAL_REASON)
        return False
    return True


def _describe(index: int, result: dict) -> dict:
    """One proposed action as the reviewer sees it."""
    if "side" in result:
        size = (
            {"quantity": result["quantity"]}
            if result["amount"] is None
            else {"amount_usd": result["amount"]}
        )
        fields = {"type": "trade", "side": result["side"], **size}
    else:
        fields = {"type": "watchlist_change", "action": result["action"]}
    return {"action_index": index, "ticker": result["ticker"], **fields}


def _apply_verdicts(survivors: list[dict], verdicts: ReviewerResponse) -> None:
    """Approve only on a matching approval with no matching rejection (fail closed)."""
    for index, result in enumerate(survivors):
        kind = _describe(index, result)["type"]
        matching = [r for r in verdicts.reviews if r.action_index == index and r.type == kind]
        if not matching:
            chosen = {"verdict": "reject", "reason": NO_VERDICT_REASON}
        else:
            pick = next((r for r in matching if r.verdict == "reject"), matching[0])
            chosen = {"verdict": pick.verdict, "reason": pick.reason}
        result["review"] = chosen
        if chosen["verdict"] == "reject":
            _reject(result, chosen["reason"])


def _approved(result: dict) -> bool:
    return result["review"] is not None and result["review"]["verdict"] == "approve"


async def _execute_trade(state, user_id: str, result: dict) -> None:
    try:
        response = await portfolio.execute_trade(
            state,
            user_id,
            result["ticker"],
            result["side"],
            result["quantity"],
            result["amount"],
        )
    except ServiceError as exc:
        _reject(result, exc.message)
    except Exception:
        logger.exception("Trade execution failed")
        _reject(result, INTERNAL_REASON)
    else:
        trade = response["trade"]
        result.update(status="executed", quantity=trade["quantity"], price=trade["price"])
        if result["amount"] is not None:
            result["amount"] = trade["value"]


async def _execute_change(state, user_id: str, result: dict) -> None:
    operation = watchlist.add_ticker if result["action"] == "add" else watchlist.remove_ticker
    try:
        await operation(state, user_id, result["ticker"])
    except ServiceError as exc:
        _reject(result, exc.message)
    except Exception:
        logger.exception("Watchlist change failed")
        _reject(result, INTERNAL_REASON)
    else:
        result["status"] = "executed"


def _compose_message(
    message: str, summary: str | None, trades: list[dict], changes: list[dict]
) -> str:
    """Append the reviewer's note and every rejection reason (no third LLM call)."""
    lines = [message.strip()]
    if summary and summary.strip():
        lines.append(summary.strip())
    for t in trades:
        if t["status"] == "rejected":
            lines.append(f"Rejected: {t['side']} {_order_text(t)} - {t['reason']}")
    for c in changes:
        if c["status"] == "rejected":
            lines.append(f"Rejected: {c['action']} {c['ticker']} - {c['reason']}")
    return "\n".join(lines)


def _order_text(trade: dict) -> str:
    if trade["amount"] is not None:
        return f"${trade['amount']:,.2f} of {trade['ticker']}"
    if trade["quantity"] is None:
        return trade["ticker"]
    quantity = f"{trade['quantity']:.6f}".rstrip("0").rstrip(".")
    return f"{quantity} {trade['ticker']}"


def _reply(
    user_id: str, message: str, trades: list[dict], changes: list[dict], error: str | None
) -> dict:
    actions = {"trades": trades, "watchlist_changes": changes, "error": error}
    db.add_chat_message(user_id, "assistant", message, actions)
    return {"message": message, **actions}

"""One chat turn: propose, check in code, review, execute, store."""

from __future__ import annotations

import json
import logging
from decimal import Decimal

from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import State

from app.errors import ApiError
from app.llm import ModelError, Proposal
from app.market import normalize_ticker
from app.market.interface import is_valid_symbol
from app.routes.portfolio import portfolio_view
from app.services import place_trade, unwatch, watch
from db import TradeError, add_exchange, cents, list_watchlist, recent_messages
from db.portfolio import check_quantity

logger = logging.getLogger(__name__)

HISTORY_SENT = 10
MAX_PER_KIND = 5

PROPOSER_PROMPT = (
    "You are FinAlly, an AI trading assistant for a simulated portfolio. Analyse composition, "
    "concentration and P&L, and answer in a few data-driven sentences. Propose trades or "
    "watchlist changes only when the user asks for them or agrees to them. At most 5 of each. "
    "A ticker must be watched or held to be traded; add it first if needed. Your actions are "
    "checked and reviewed after you answer, so never claim they have happened. The last message "
    "is JSON with the portfolio, watchlist prices and the user_message. Reply only with JSON "
    "matching the schema, using empty lists when there is nothing to do."
)
REVIEWER_PROMPT = (
    "You review actions proposed for a simulated trading account. For each action, approve or "
    "reject; you cannot change or add actions. Approve only if the user_message asked for or "
    "agreed to it, with the same ticker, side and size, and it is not an obvious error or a "
    "wildly large or concentrated position the user did not ask for. Give a one-sentence reason. "
    "Reply only with JSON matching the schema."
)


def _context(view: dict, watched: list[str], state: State) -> dict:
    return {
        "cash": view["cash"],
        "total_value": view["total_value"],
        "positions": [
            {
                "ticker": p["ticker"],
                "qty": p["quantity"],
                "avg_cost": p["avg_cost"],
                "price": p["price"],
                "pnl_percent": p["pnl_percent"],
            }
            for p in view["positions"]
        ],
        "watchlist": {t: state.price_cache.get_price(normalize_ticker(t)) for t in watched},
    }


def _describe(action: dict) -> str:
    if action["type"] == "trade":
        return f"{action['side']} {action['quantity']:g} {action['ticker']}"
    return f"{action['action']} {action['ticker']} on the watchlist"


def _history_text(message: dict) -> str:
    """Past outcomes go with the past answers, so the model knows what really happened."""
    text = message["content"][:1000]
    outcomes = [f"{_describe(a)}: {a['status']}" for a in message["actions"] or []]
    return f"{text}\n[Results: {'; '.join(outcomes)}]" if outcomes else text


def _actions(proposal: Proposal) -> list[dict]:
    """In execution order: additions first (a new ticker needs a price), removals last."""
    changes = [
        {"type": "watchlist", "ticker": normalize_ticker(c.ticker), "action": c.action}
        for c in proposal.watchlist_changes
    ]
    trades = [
        {
            "type": "trade",
            "ticker": normalize_ticker(t.ticker),
            "side": t.side,
            "quantity": t.quantity,
        }
        for t in proposal.trades
    ]
    for group in (changes, trades):
        for action in group[MAX_PER_KIND:]:
            _reject(action, f"Only {MAX_PER_KIND} of these are allowed per message.")
    adds = [c for c in changes if c["action"] == "add"]
    removes = [c for c in changes if c["action"] == "remove"]
    return adds + trades + removes


def _reject(action: dict, reason: str) -> None:
    action.update(status="rejected", reason=reason)


def check_actions(actions: list[dict], view: dict, watched: list[str], state: State) -> None:
    """Reject in code whatever could not work, before the reviewer sees it."""
    cash = Decimal(str(view["cash"]))
    held = {p["ticker"]: Decimal(str(p["quantity"])) for p in view["positions"]}
    adding: set[str] = set()
    for action in actions:
        if "status" in action:
            continue
        ticker = action["ticker"]
        if action["type"] == "watchlist":
            if not is_valid_symbol(ticker):
                _reject(action, "That is not a valid ticker symbol.")
            elif action["action"] == "add" and ticker in watched:
                _reject(action, f"{ticker} is already on your watchlist.")
            elif action["action"] == "remove" and ticker not in watched:
                _reject(action, f"{ticker} is not on your watchlist.")
            elif action["action"] == "add":
                adding.add(ticker)
            continue
        try:
            quantity = check_quantity(Decimal(str(action["quantity"])))
        except TradeError as refusal:
            _reject(action, refusal.message)
            continue
        price = state.price_cache.get_price(ticker)
        owned = held.get(ticker, Decimal(0))
        value = None if price is None else cents(quantity * Decimal(str(price)))
        if price is None and ticker not in adding:
            _reject(action, f"There is no current price for {ticker}.")
        elif action["side"] == "sell" and quantity > owned:
            _reject(action, f"Not enough shares: you hold {owned.normalize():f} {ticker}.")
        elif action["side"] == "buy" and value is not None and value > cash:
            _reject(action, f"Not enough cash: this costs ${value:,.2f}.")
        else:
            sign = 1 if action["side"] == "buy" else -1
            held[ticker] = owned + sign * quantity
            cash -= sign * (value or 0)


async def _review(state: State, question: str, view: dict, pending: list[dict]) -> str:
    """Mark every action the reviewer did not clearly approve. Returns its note."""
    payload = {
        "portfolio": {"cash": view["cash"], "positions": view["positions"]},
        "actions": [{"action_index": i, **action} for i, action in enumerate(pending)],
        "user_message": question,
    }
    try:
        result = await state.llm.review(
            [
                {"role": "system", "content": REVIEWER_PROMPT},
                {"role": "user", "content": json.dumps(payload)},
            ]
        )
    except Exception as error:  # fail closed, whatever went wrong
        if not isinstance(error, ModelError):
            logger.exception("Review failed")
        for action in pending:
            _reject(action, "The safety review failed, so nothing was executed.")
        return ""
    for index, action in enumerate(pending):
        verdicts = [r for r in result.reviews if r.action_index == index]
        approved = bool(verdicts) and all(r.verdict == "approve" for r in verdicts)
        reason = next(
            (r.reason for r in verdicts if r.verdict == "reject"),
            verdicts[0].reason if verdicts else "",
        )
        action["review"] = {"verdict": "approve" if approved else "reject", "reason": reason}
        if not approved:
            _reject(action, reason or "The reviewer did not approve it.")
    return result.summary


async def _execute(state: State, user_id: str, action: dict) -> None:
    try:
        if action["type"] == "trade":
            filled = await place_trade(
                state, user_id, action["ticker"], action["side"], action["quantity"]
            )
            action["price"] = filled["price"]
        elif action["action"] == "add":
            await watch(state, user_id, action["ticker"])
        else:
            await unwatch(state, user_id, action["ticker"])
        action.update(status="executed", reason="")
    except ApiError as refusal:
        _reject(action, refusal.message)
    except Exception:  # one failure must not stop the others
        logger.exception("Could not execute a chat action")
        _reject(action, "It could not be executed.")


async def chat_turn(state: State, user_id: str, question: str) -> list[dict]:
    """The stored question and answer. Raises ModelError if there is no proposal."""
    view = await run_in_threadpool(portfolio_view, state.db_path, state.price_cache, user_id)
    watched = await run_in_threadpool(list_watchlist, state.db_path, user_id)
    history = await run_in_threadpool(recent_messages, state.db_path, user_id, HISTORY_SENT)
    # Static text first, changing data last, so the provider can cache the prefix.
    messages = [{"role": "system", "content": PROPOSER_PROMPT}]
    messages += [{"role": m["role"], "content": _history_text(m)} for m in history]
    payload = {"portfolio": _context(view, watched, state), "user_message": question}
    messages.append({"role": "user", "content": json.dumps(payload)})

    proposal = await state.llm.propose(messages)
    actions = _actions(proposal)
    check_actions(actions, view, watched, state)
    pending = [a for a in actions if "status" not in a]
    note = await _review(state, question, view, pending) if pending else ""
    for action in pending:
        if "status" not in action:
            await _execute(state, user_id, action)

    answer = f"{proposal.message}\n{note}".strip()
    return await run_in_threadpool(add_exchange, state.db_path, user_id, question, answer, actions)

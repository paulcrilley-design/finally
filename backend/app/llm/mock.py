"""Deterministic stand-ins for the proposer and reviewer (LLM_MOCK=true)."""

import os
import re

from .schemas import ProposerResponse, Review, ReviewerResponse, TradeProposal, WatchlistProposal

_TICKER = r"([a-z]+(?:[.\-][a-z]+)*)"
_TRADE_RE = re.compile(rf"\b(buy|sell)\s+(\d+(?:\.\d+)?|\.\d+)\s+{_TICKER}", re.IGNORECASE)
_WATCH_RE = re.compile(rf"\b(add|remove)\s+{_TICKER}", re.IGNORECASE)
_REJECT_RE = re.compile(r"\breject\b", re.IGNORECASE)


def is_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def propose(user_message: str) -> ProposerResponse:
    trades = [
        TradeProposal(ticker=ticker.upper(), side=side.lower(), quantity=float(quantity))
        for side, quantity, ticker in _TRADE_RE.findall(user_message)
    ]
    changes = [
        WatchlistProposal(ticker=ticker.upper(), action=action.lower())
        for action, ticker in _WATCH_RE.findall(user_message)
    ]
    message = (
        "Mock response: here is your request."
        if trades or changes
        else "Mock response: your portfolio looks balanced."
    )
    return ProposerResponse(message=message, trades=trades, watchlist_changes=changes)


def review(user_message: str, actions: list[dict]) -> ReviewerResponse:
    rejecting = bool(_REJECT_RE.search(user_message))
    return ReviewerResponse(
        reviews=[
            Review(
                action_index=a["action_index"],
                type=a["type"],
                verdict="reject" if rejecting else "approve",
                reason="Mock reviewer rejection." if rejecting else "Mock reviewer approval.",
            )
            for a in actions
        ]
    )

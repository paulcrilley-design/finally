"""Deterministic stand-in for both models (LLM_MOCK=true). No network."""

from __future__ import annotations

import json
import re

from .schema import Proposal, Review, ReviewResult

TICKER = r"([a-z][a-z0-9.\-]{0,9}?)(?=[\s,;!?]|\.(?:\s|$)|$)"
TRADE = re.compile(rf"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+{TICKER}", re.IGNORECASE)
CHANGE = re.compile(rf"\b(add|remove)\s+{TICKER}", re.IGNORECASE)


def _payload(messages: list[dict]) -> dict:
    return json.loads(messages[-1]["content"])


class MockClient:
    async def propose(self, messages: list[dict]) -> Proposal:
        payload = _payload(messages)
        text = payload["user_message"]
        trades = [
            {"side": side.lower(), "quantity": float(quantity), "ticker": ticker.upper()}
            for side, quantity, ticker in TRADE.findall(text)
        ]
        changes = [
            {"action": action.lower(), "ticker": ticker.upper()}
            for action, ticker in CHANGE.findall(text)
        ]
        if trades or changes:
            message = "Here is what you asked for."
        else:
            portfolio = payload["portfolio"]
            message = (
                f"You have ${portfolio['cash']:,.2f} in cash and "
                f"{len(portfolio['positions'])} open positions."
            )
        return Proposal(message=message, trades=trades, watchlist_changes=changes)

    async def review(self, messages: list[dict]) -> ReviewResult:
        payload = _payload(messages)
        rejected = "reject" in payload["user_message"].lower()
        return ReviewResult(
            reviews=[
                Review(
                    action_index=action["action_index"],
                    verdict="reject" if rejected else "approve",
                    reason="Rejected by the mock reviewer." if rejected else "Matches the request.",
                )
                for action in payload["actions"]
            ]
        )

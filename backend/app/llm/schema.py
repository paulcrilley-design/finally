"""What the models must return, as Pydantic models and as JSON Schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, StrictFloat, StrictInt


class ProposedTrade(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: StrictInt | StrictFloat


class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class Proposal(BaseModel):
    message: str
    trades: list[ProposedTrade] = []
    watchlist_changes: list[WatchlistChange] = []


class Review(BaseModel):
    action_index: StrictInt
    verdict: Literal["approve", "reject"]
    reason: str = ""


class ReviewResult(BaseModel):
    reviews: list[Review]
    summary: str = ""


def _object(properties: dict) -> dict:
    # Strict structured output: every property required, nothing else allowed.
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _list(item: dict) -> dict:
    return {"type": "array", "items": item}


TEXT = {"type": "string"}

PROPOSAL_SCHEMA = _object(
    {
        "message": TEXT,
        "trades": _list(
            _object(
                {
                    "ticker": TEXT,
                    "side": {"type": "string", "enum": ["buy", "sell"]},
                    "quantity": {"type": "number"},
                }
            )
        ),
        "watchlist_changes": _list(
            _object({"ticker": TEXT, "action": {"type": "string", "enum": ["add", "remove"]}})
        ),
    }
)

REVIEW_SCHEMA = _object(
    {
        "reviews": _list(
            _object(
                {
                    "action_index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["approve", "reject"]},
                    "reason": TEXT,
                }
            )
        ),
        "summary": TEXT,
    }
)

"""Request body and structured-output schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2000)


class TradeProposal(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float | None = Field(default=None, allow_inf_nan=False)  # shares
    amount: float | None = Field(default=None, allow_inf_nan=False)  # US dollars


class WatchlistProposal(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class ProposerResponse(BaseModel):
    message: str
    trades: list[TradeProposal] = []
    watchlist_changes: list[WatchlistProposal] = []


class Review(BaseModel):
    action_index: int
    type: Literal["trade", "watchlist_change"]
    verdict: Literal["approve", "reject"]
    reason: str


class ReviewerResponse(BaseModel):
    reviews: list[Review]
    summary: str | None = None

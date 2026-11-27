"""The user's watchlist, with the latest cached prices."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.errors import ApiError
from app.identity import get_current_user
from app.market import MarketDataError, normalize_ticker
from app.market.interface import is_valid_symbol
from app.tracking import sync_tracked_tickers
from db import add_to_watchlist, list_watchlist, remove_from_watchlist

router = APIRouter(prefix="/api", tags=["watchlist"])

# PriceUpdate.to_dict() without "ticker": all null while a price is unknown.
PRICE_FIELDS = (
    "price",
    "previous_price",
    "timestamp",
    "change",
    "change_percent",
    "direction",
    "prev_close",
    "day_change",
    "day_change_percent",
)


@router.get("/watchlist")
def get_watchlist(request: Request, user_id: Annotated[str, Depends(get_current_user)]) -> dict:
    items = []
    for ticker in list_watchlist(request.app.state.db_path, user_id):
        symbol = normalize_ticker(ticker)
        update = request.app.state.price_cache.get(symbol)
        if update is None:
            items.append({"ticker": symbol, **dict.fromkeys(PRICE_FIELDS)})
        else:
            items.append(update.to_dict())
    return {"watchlist": items}


class TickerRequest(BaseModel):
    ticker: str


@router.post("/watchlist")
async def add_ticker(
    body: TickerRequest,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    state = request.app.state
    symbol = normalize_ticker(body.ticker)
    try:
        valid = is_valid_symbol(symbol) and await state.source.validate_ticker(symbol)
    except MarketDataError as error:
        raise ApiError(
            "ticker_unavailable", "The ticker cannot be checked now. Try again."
        ) from error
    if not valid:
        raise ApiError("invalid_ticker", "That is not a valid ticker symbol.")
    if not await run_in_threadpool(add_to_watchlist, state.db_path, user_id, symbol):
        raise ApiError("already_watched", f"{symbol} is already on your watchlist.", 409)
    await sync_tracked_tickers(state)
    return await run_in_threadpool(get_watchlist, request, user_id)


@router.delete("/watchlist/{ticker}")
async def remove_ticker(
    ticker: str,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    state = request.app.state
    symbol = normalize_ticker(ticker)
    if not await run_in_threadpool(remove_from_watchlist, state.db_path, user_id, symbol):
        raise ApiError("not_watched", f"{symbol} is not on your watchlist.", 404)
    await sync_tracked_tickers(state)
    return await run_in_threadpool(get_watchlist, request, user_id)

"""Trades and watchlist changes, shared by the REST routes and the chat."""

from __future__ import annotations

from decimal import Decimal

from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import State

from app.errors import ApiError
from app.market import MarketDataError, normalize_ticker
from app.market.interface import is_valid_symbol
from app.tracking import sync_tracked_tickers
from db import TradeError, add_to_watchlist, execute_trade, remove_from_watchlist


async def place_trade(state: State, user_id: str, ticker: str, side: str, quantity: float) -> dict:
    """Fill a market order at the cached price, or raise ApiError."""
    symbol = normalize_ticker(ticker)
    update = state.price_cache.get(symbol)
    try:
        filled = await run_in_threadpool(
            execute_trade,
            state.db_path,
            user_id,
            symbol,
            side,
            Decimal(str(quantity)),
            update.price if update else None,
            update.prev_close if update else None,
            {t: u.price for t, u in state.price_cache.get_all().items()},
        )
    except TradeError as refusal:
        raise ApiError(refusal.code, refusal.message) from refusal
    await sync_tracked_tickers(state)
    return filled


async def watch(state: State, user_id: str, ticker: str) -> str:
    symbol = normalize_ticker(ticker)
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
    return symbol


async def unwatch(state: State, user_id: str, ticker: str) -> str:
    symbol = normalize_ticker(ticker)
    if not await run_in_threadpool(remove_from_watchlist, state.db_path, user_id, symbol):
        raise ApiError("not_watched", f"{symbol} is not on your watchlist.", 404)
    await sync_tracked_tickers(state)
    return symbol

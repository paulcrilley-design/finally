"""Watchlist reads and changes."""

import db
from app.market import MarketDataError, PriceCache, reconcile_tickers
from app.services.errors import ServiceError
from app.services.tickers import require_symbol

_PRICE_FIELDS = (
    "price",
    "previous_price",
    "timestamp",
    "direction",
    "prev_close",
    "day_change",
    "day_change_percent",
)


def get_watchlist(state, user_id: str) -> dict:
    return {"tickers": [_item(state.price_cache, t) for t in db.list_watchlist(user_id)]}


def check_change(state, user_id: str, ticker: str, action: str) -> str:
    """Validate an "add" or "remove" without writing. Returns the normalised ticker."""
    if action not in ("add", "remove"):
        raise ServiceError("invalid_request", "Action must be 'add' or 'remove'.")
    symbol = require_symbol(ticker)
    watching = symbol in db.list_watchlist(user_id)
    if action == "add" and watching:
        raise _already_watching(symbol)
    if action == "remove" and not watching:
        raise _not_watching(symbol)
    return symbol


async def add_ticker(state, user_id: str, ticker: str) -> dict:
    symbol = check_change(state, user_id, ticker, "add")
    try:
        known = await state.market_source.validate_ticker(symbol)
    except MarketDataError:
        raise ServiceError("no_price", f"Could not check {symbol} right now. Try again.") from None
    if not known:
        raise ServiceError("invalid_ticker", f"{symbol} is not a known ticker.")
    if not db.add_watchlist(user_id, symbol):
        raise _already_watching(symbol)
    await reconcile_tickers(state.market_source, db.all_tracked_tickers())
    return _item(state.price_cache, symbol)


async def remove_ticker(state, user_id: str, ticker: str) -> None:
    symbol = check_change(state, user_id, ticker, "remove")
    if not db.remove_watchlist(user_id, symbol):
        raise _not_watching(symbol)
    await reconcile_tickers(state.market_source, db.all_tracked_tickers())


def _item(cache: PriceCache, ticker: str) -> dict:
    update = cache.get(ticker)
    data = update.to_dict() if update else {}
    return {"ticker": ticker, **{field: data.get(field) for field in _PRICE_FIELDS}}


def _already_watching(ticker: str) -> ServiceError:
    return ServiceError("already_watching", f"{ticker} is already on the watchlist.", 409)


def _not_watching(ticker: str) -> ServiceError:
    return ServiceError("not_watching", f"{ticker} is not on the watchlist.", 404)

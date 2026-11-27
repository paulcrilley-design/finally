"""Ticker input checks."""

from app.market import normalize_ticker
from app.market.interface import is_valid_symbol
from app.services.errors import ServiceError


def require_symbol(ticker: str) -> str:
    """Return the normalised ticker, or raise `invalid_ticker`."""
    symbol = normalize_ticker(ticker)
    if not is_valid_symbol(symbol):
        raise ServiceError("invalid_ticker", "That is not a valid ticker symbol.")
    return symbol

"""Market data subsystem for FinAlly.

Public API:
    PriceUpdate, PriceCache         - price snapshot and the shared cache
    MarketDataSource                - abstract interface for data providers
    MarketDataError / Unavailable   - source failures
    create_market_data_source       - factory (simulator or Massive)
    start_market_data               - factory + start, with simulator fallback
    reconcile_tickers               - sync a source with the app's needed tickers
    create_stream_router            - FastAPI router for the SSE endpoint
"""

from .cache import PriceCache
from .factory import create_market_data_source, start_market_data
from .interface import (
    MarketDataError,
    MarketDataSource,
    MarketDataUnavailableError,
    normalize_ticker,
)
from .models import PriceUpdate
from .stream import create_stream_router
from .tracking import reconcile_tickers

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "MarketDataError",
    "MarketDataUnavailableError",
    "normalize_ticker",
    "create_market_data_source",
    "start_market_data",
    "reconcile_tickers",
    "create_stream_router",
]

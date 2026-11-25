"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource, MarketDataUnavailableError
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        logger.warning("Ignoring non-numeric %s=%r", name, raw)
        return default


def _env_seed() -> int | None:
    raw = os.environ.get("SIM_SEED", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("Ignoring non-integer SIM_SEED=%r", raw)
        return None


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Build (but do not start) the source selected by the environment.

    MASSIVE_API_KEY set and non-empty, and MARKET_FORCE_SIMULATOR not true
        -> MassiveDataSource    (MASSIVE_MODE=auto|snapshot|eod, MASSIVE_POLL_INTERVAL=15)
    otherwise
        -> SimulatorDataSource  (SIM_SEED=<int> for a reproducible series)
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    force_sim = os.environ.get("MARKET_FORCE_SIMULATOR", "").strip().lower() in ("1", "true", "yes")

    if api_key and not force_sim:
        logger.info("Market data source: Massive API")
        return MassiveDataSource(
            api_key=api_key,
            price_cache=price_cache,
            poll_interval=max(_env_float("MASSIVE_POLL_INTERVAL", 15.0), 1.0),
            requested_mode=os.environ.get("MASSIVE_MODE", "auto").strip().lower() or "auto",
        )
    logger.info("Market data source: GBM simulator")
    return SimulatorDataSource(price_cache=price_cache, seed=_env_seed())


async def start_market_data(price_cache: PriceCache, tickers: list[str]) -> MarketDataSource:
    """Create and start a source. If Massive cannot work (bad key), fall back to the
    simulator so the app stays usable; /api/health then reports degraded=true."""
    source = create_market_data_source(price_cache)
    try:
        await source.start(tickers)
        return source
    except MarketDataUnavailableError as err:
        logger.error("Massive unavailable (%s); falling back to the simulator", err)
        await source.stop()
        fallback = SimulatorDataSource(
            price_cache=price_cache, seed=_env_seed(), degraded_reason=str(err)
        )
        await fallback.start(tickers)
        return fallback

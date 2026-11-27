"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import math
import os

from .cache import PriceCache
from .interface import MarketDataSource, MarketDataUnavailableError
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value):
        logger.warning("Ignoring non-numeric %s=%r", name, raw)
        return default
    return value


def _env_seed() -> int | None:
    raw = os.environ.get("SIM_SEED", "").strip()
    if not raw:
        return None
    try:
        seed = int(raw)
    except ValueError:
        seed = -1
    if seed < 0:  # numpy rejects negative seeds
        logger.warning("Ignoring SIM_SEED=%r (must be a non-negative integer)", raw)
        return None
    return seed


def _env_mode() -> str:
    raw = os.environ.get("MASSIVE_MODE", "").strip().lower() or "auto"
    if raw not in ("auto", "snapshot", "eod"):
        logger.warning("Ignoring MASSIVE_MODE=%r (use auto, snapshot or eod)", raw)
        return "auto"
    return raw


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Build (but do not start) the source selected by the environment.

    MASSIVE_API_KEY set and non-empty, and MARKET_FORCE_SIMULATOR not true
        -> MassiveDataSource    (MASSIVE_MODE=auto|snapshot|eod, MASSIVE_POLL_INTERVAL=15)
    otherwise
        -> SimulatorDataSource  (SIM_SEED=<int >= 0> for a reproducible series)
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    force_sim = os.environ.get("MARKET_FORCE_SIMULATOR", "").strip().lower() in ("1", "true", "yes")

    if api_key and not force_sim:
        logger.info("Market data source: Massive API")
        return MassiveDataSource(
            api_key=api_key,
            price_cache=price_cache,
            poll_interval=max(_env_float("MASSIVE_POLL_INTERVAL", 15.0), 1.0),
            requested_mode=_env_mode(),
            fallback_seed=_env_seed(),
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

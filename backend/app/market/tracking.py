"""Keep the data source's ticker set equal to what the app needs."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .interface import MarketDataSource, normalize_ticker

logger = logging.getLogger(__name__)


async def reconcile_tickers(source: MarketDataSource, wanted: Iterable[str]) -> None:
    """Make `source` track exactly `wanted` (union of every user's watchlist and positions).

    Idempotent, so callers just invoke it after any watchlist or trade change instead of
    reasoning about add/remove ordering.
    """
    want = {normalize_ticker(t) for t in wanted}
    have = set(source.get_tickers())
    for ticker in sorted(want - have):
        await source.add_ticker(ticker)
    for ticker in sorted(have - want):
        await source.remove_ticker(ticker)
    if want != have:
        logger.info("Tracked tickers: +%s -%s", sorted(want - have), sorted(have - want))

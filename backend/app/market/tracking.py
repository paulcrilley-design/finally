"""Keep the data source's ticker set equal to what the app needs."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .interface import MarketDataSource, is_valid_symbol, normalize_ticker

logger = logging.getLogger(__name__)

_warned_invalid: set[str] = set()  # warn once per bad symbol, not on every reconcile


async def reconcile_tickers(source: MarketDataSource, wanted: Iterable[str]) -> None:
    """Make `source` track exactly `wanted` (union of every user's watchlist and positions).

    Idempotent, so callers just invoke it after any watchlist or trade change instead of
    reasoning about add/remove ordering.
    """
    want = {normalize_ticker(t) for t in wanted}
    invalid = {t for t in want if not is_valid_symbol(t)}  # sources would silently ignore these
    for ticker in sorted(invalid - _warned_invalid):
        logger.warning("Ignoring invalid ticker symbol %r", ticker)
    _warned_invalid.update(invalid)
    want -= invalid
    have = set(source.get_tickers())
    for ticker in sorted(want - have):
        await source.add_ticker(ticker)
    for ticker in sorted(have - want):
        await source.remove_ticker(ticker)
    if want != have:
        logger.info("Tracked tickers: +%s -%s", sorted(want - have), sorted(have - want))

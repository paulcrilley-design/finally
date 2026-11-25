"""Abstract interface for market data sources."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")  # AAPL, BRK.B, RDS-A


class MarketDataError(Exception):
    """A source could not do what was asked (network, rate limit, bad plan)."""


class MarketDataUnavailableError(MarketDataError):
    """Raised by start() when the source can never work with this config (bad key)."""


def normalize_ticker(ticker: str) -> str:
    """Canonical form used everywhere: stripped and upper-case."""
    return ticker.strip().upper()


def is_valid_symbol(ticker: str) -> bool:
    """Syntax check only. Says nothing about whether the symbol trades."""
    return bool(_TICKER_RE.match(ticker))


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source for prices; it reads
    from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates. Call exactly once."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop background work. Safe to call repeatedly."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Track a ticker. No-op if already tracked."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker and evict it from the cache. No-op if absent."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Currently tracked tickers."""

    # --- Optional capabilities, with safe defaults -------------------------

    @property
    def mode(self) -> str:
        """'simulator', 'massive-snapshot' or 'massive-eod'. Shown in /api/health."""
        return "unknown"

    async def validate_ticker(self, ticker: str) -> bool:
        """True if `ticker` is a real, priceable symbol for this source.

        Default: syntax check only. Raises MarketDataError if the source cannot
        decide right now (network down, rate limited).
        """
        return is_valid_symbol(normalize_ticker(ticker))

    def status(self) -> dict[str, Any]:
        """Small JSON-able dict for the health endpoint."""
        return {"mode": self.mode, "degraded": False, "tickers": len(self.get_tickers())}

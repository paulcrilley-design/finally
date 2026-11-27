"""Massive (formerly Polygon.io) market data source."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from datetime import time as dtime
from typing import Any
from zoneinfo import ZoneInfo

from massive import RESTClient
from massive.rest.models import SnapshotMarketType

from .cache import PriceCache
from .interface import (
    MarketDataError,
    MarketDataSource,
    MarketDataUnavailableError,
    clean_tickers,
    is_valid_symbol,
    normalize_ticker,
)
from .massive_parse import ErrorKind, classify_error, extract_quote
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)

NEW_YORK = ZoneInfo("America/New_York")
MAX_BACKOFF = 120.0  # seconds
FREE_TIER_CALL_GAP = 12.5  # 5 requests/minute => at most one call per 12 s
PROBE_TICKER = "AAPL"  # polled when nothing is tracked, so key and plan are still checked


class MassiveCallError(Exception):
    """A Massive call failed; `kind` says how, `__cause__` has the original."""

    def __init__(self, kind: ErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def make_client(api_key: str, timeout: float) -> RESTClient:
    """RESTClient tuned for polling.

    retries=0: the SDK's default of 3 retries includes HTTP 429, which hides the rate
    limit behind a MaxRetryError and stalls a worker thread. We do our own backoff.
    """
    client = RESTClient(api_key=api_key, retries=0, connect_timeout=timeout, read_timeout=timeout)
    # The SDK stores its timeout but never gives it to urllib3, so a hung call would keep
    # its thread (and the process) alive. SDK internal: covered by a test.
    client.client.connection_pool_kw["timeout"] = client.timeout
    return client


class MassiveDataSource(MarketDataSource):
    """Polls Massive REST endpoints and writes to the PriceCache.

    mode "snapshot": one /v2/snapshot call per poll for all tickers (paid plans).
    mode "eod":      grouped daily bars, refreshed hourly (free plan; prices are static).
    `requested_mode` "auto" starts in snapshot and drops to eod on a 403.
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
        requested_mode: str = "auto",  # auto | snapshot | eod
        request_timeout: float = 10.0,
        eod_refresh: float = 3600.0,
        call_gap: float | None = None,  # min seconds between eod calls; None = FREE_TIER_CALL_GAP
        fallback_seed: int | None = None,  # SIM_SEED for the simulator that may take over
        client: Any = None,  # injectable for tests
        validate_gap: float = 0.5,  # min seconds between snapshot-mode validate calls
    ) -> None:
        if requested_mode not in ("auto", "snapshot", "eod"):
            raise ValueError(f"bad MASSIVE_MODE: {requested_mode!r}")
        self._api_key = api_key
        self._cache = price_cache
        self._base_interval = poll_interval
        self._interval = poll_interval  # current, grows under rate limiting
        self._requested = requested_mode
        self._timeout = request_timeout
        self._eod_refresh = eod_refresh
        self._call_gap = FREE_TIER_CALL_GAP if call_gap is None else call_gap
        self._fallback_seed = fallback_seed
        self._client = client
        self._mode = "eod" if requested_mode == "eod" else "snapshot"
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._wakeup = asyncio.Event()
        self._last_call = 0.0
        self._eod_closes: dict[str, float] = {}  # whole market, latest session
        self._eod_prev: dict[str, float] = {}  # whole market, session before
        self._eod_ts: float = 0.0
        self._last_success: float | None = None
        self._last_error: str | None = None
        self._degraded: str | None = None
        self._eod_day: date | None = None  # session last logged, to warn once per session
        self._validate_gap = validate_gap
        self._validate_lock = asyncio.Lock()  # serialises validate calls
        self._last_validate = 0.0
        # Set when the key is rejected at runtime: a simulator takes over so prices keep moving.
        self._fallback: SimulatorDataSource | None = None

    # --- MarketDataSource ---

    @property
    def mode(self) -> str:
        if self._fallback:
            return self._fallback.mode
        return f"massive-{self._mode}"

    def status(self) -> dict[str, Any]:
        if self._fallback:
            return self._fallback.status()
        return {
            "mode": self.mode,
            "degraded": self._degraded is not None,
            "degraded_reason": self._degraded,
            "tickers": len(self._tickers),
            "poll_interval": self._interval,
            "last_success": self._last_success,
            "last_error": self._last_error,
        }

    async def start(self, tickers: list[str]) -> None:
        if self._task is not None and not self._task.done():
            raise RuntimeError("MassiveDataSource already started")
        self._tickers = clean_tickers(tickers)
        self._fallback = None
        self._degraded = None
        self._client = self._client or make_client(self._api_key, self._timeout)

        first_delay = 0.0
        if self._mode == "snapshot":
            try:  # probe: success also fills the cache before start() returns
                await self._poll_snapshot()
                self._on_success()
                first_delay = self._interval
            except MassiveCallError as err:
                if err.kind is ErrorKind.AUTH:
                    raise MarketDataUnavailableError(
                        f"Massive rejected the API key: {err}"
                    ) from err
                if err.kind is ErrorKind.FORBIDDEN and self._requested == "auto":
                    self._switch_to_eod(err)
                else:
                    self._on_error(err)  # network/rate limit: keep trying in the loop
                    first_delay = self._interval
        self._task = asyncio.create_task(self._run(first_delay), name="massive-poller")
        logger.info("Massive source started: mode=%s tickers=%d", self.mode, len(self._tickers))

    async def stop(self) -> None:
        await self._stop_poller()
        if self._fallback:
            await self._fallback.stop()
        logger.info("Massive source stopped")

    async def _stop_poller(self) -> None:
        task, self._task = self._task, None
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def add_ticker(self, ticker: str) -> None:
        if self._fallback:
            return await self._fallback.add_ticker(ticker)
        ticker = normalize_ticker(ticker)
        if not is_valid_symbol(ticker) or ticker in self._tickers:
            return
        self._tickers.append(ticker)
        if self._mode == "eod":
            self._apply_eod([ticker])  # whole-market data is already in memory
        elif self._interval <= self._base_interval:  # never cut a rate-limit backoff short
            self._wakeup.set()  # poll now instead of waiting up to a full interval

    async def remove_ticker(self, ticker: str) -> None:
        if self._fallback:
            return await self._fallback.remove_ticker(ticker)
        ticker = normalize_ticker(ticker)
        if ticker in self._tickers:
            self._tickers.remove(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        if self._fallback:
            return self._fallback.get_tickers()
        return list(self._tickers)

    async def validate_ticker(self, ticker: str) -> bool:
        if self._fallback:
            return await self._fallback.validate_ticker(ticker)
        ticker = normalize_ticker(ticker)
        if not is_valid_symbol(ticker):
            return False
        if self._mode == "eod":
            if not self._eod_closes:
                raise MarketDataError("End-of-day data is still loading; try again shortly")
            return ticker in self._eod_closes
        async with self._validate_lock:  # one call at a time, spaced out, so adds cannot burst
            wait = self._last_validate + self._validate_gap - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_validate = time.monotonic()
            try:
                snap = await self._call(
                    self._client.get_snapshot_ticker, SnapshotMarketType.STOCKS.value, ticker
                )
            except MassiveCallError as err:
                if err.kind is ErrorKind.NOT_FOUND:
                    return False
                if err.kind is ErrorKind.AUTH:
                    await self._fall_back(f"api key rejected: {err}")
                    return await self._fallback.validate_ticker(ticker)
                if err.kind is ErrorKind.FORBIDDEN and self._requested == "auto":
                    self._switch_to_eod(err)
                    self._wakeup.set()  # load the end-of-day data now
                raise MarketDataError(f"Could not validate {ticker}: {err}") from err
        return bool(snap) and getattr(snap, "ticker", None) == ticker

    # --- Background loop ---

    async def _run(self, first_delay: float) -> None:
        delay = first_delay
        while True:
            await self._sleep(delay)
            if self._fallback:  # validate_ticker handed over while we slept
                return
            try:
                if self._mode == "snapshot":
                    await self._poll_snapshot()
                    delay = self._interval
                else:
                    await self._refresh_eod()
                    delay = self._eod_refresh
                self._on_success()
            except MassiveCallError as err:
                if err.kind is ErrorKind.AUTH:
                    await self._fall_back(f"api key rejected: {err}")
                    return  # nothing will work until the key is fixed
                if (
                    err.kind is ErrorKind.FORBIDDEN
                    and self._mode == "snapshot"
                    and self._requested == "auto"
                ):
                    self._switch_to_eod(err)
                    delay = 0.0
                    continue
                self._on_error(err)
                delay = self._interval if self._mode == "snapshot" else min(self._eod_refresh, 300)
            except Exception:  # never let the loop die
                logger.exception("Massive loop error")
                delay = self._interval

    async def _sleep(self, seconds: float) -> None:
        """Sleep, but wake early when a ticker is added; then pause 1 s to coalesce adds."""
        if seconds <= 0:
            return
        try:
            await asyncio.wait_for(self._wakeup.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return
        self._wakeup.clear()
        await asyncio.sleep(1.0)

    # --- Snapshot mode ---

    async def _poll_snapshot(self) -> int:
        tickers = list(self._tickers) or [PROBE_TICKER]  # writes are filtered below
        snaps = await self._call(
            self._client.get_snapshot_all, SnapshotMarketType.STOCKS.value, tickers
        )
        written = 0
        for snap in snaps:
            ticker = (getattr(snap, "ticker", None) or "").upper()
            if ticker not in self._tickers:  # removed while the call was in flight
                continue
            quote = extract_quote(snap)
            if quote is None:
                logger.debug("Massive: no usable price for %s", ticker)
                continue
            self._cache.update(ticker, quote.price, quote.timestamp, prev_close=quote.prev_close)
            written += 1
        logger.debug("Massive poll: %d/%d tickers updated", written, len(tickers))
        return written

    # --- End-of-day mode ---

    async def _refresh_eod(self) -> None:
        """Load the last two trading sessions (whole market) and publish tracked tickers."""
        first_load = not self._eod_closes
        last_day: date | None = None
        latest: dict[str, float] = {}
        prev: dict[str, float] | None = None
        refused: MassiveCallError | None = None
        day = datetime.now(NEW_YORK).date()
        for _ in range(10):  # weekends are skipped for free; holidays cost one call each
            day -= timedelta(days=1)
            if day.weekday() >= 5:
                continue
            try:
                bars = await self._call(self._client.get_grouped_daily_aggs, day.isoformat(), True)
            except MassiveCallError as err:
                if last_day is not None:
                    logger.warning("Massive: could not load the prior session")
                    break
                if err.kind is not ErrorKind.FORBIDDEN:
                    raise
                refused = err  # often the newest session before its release: try older ones
                continue
            closes = {b.ticker: b.close for b in bars if b.ticker and b.close}
            if not closes:
                continue
            if last_day is None:
                last_day, latest = day, closes
                if first_load:
                    # Publish at once; the slow (rate-limited) second call below only
                    # adds the previous-close baseline.
                    self._publish_eod(day, closes, {})
            else:
                prev = closes
                break
        if last_day is None:
            raise refused or MassiveCallError(
                ErrorKind.OTHER, "no grouped daily bars in the last 10 days"
            )

        if prev is None:  # reuse what is known: same session, or the one just superseded
            if last_day == self._eod_day:
                prev = self._eod_prev
            else:
                prev = {} if first_load else self._eod_closes
        self._publish_eod(last_day, latest, prev)
        level = logging.WARNING if last_day != self._eod_day else logging.DEBUG  # once per session
        self._eod_day = last_day
        logger.log(
            level,
            "Massive end-of-day mode: prices are closes for %s and will not move intraday",
            last_day,
        )

    def _publish_eod(self, day: date, closes: dict[str, float], prev: dict[str, float]) -> None:
        self._eod_closes, self._eod_prev = closes, prev
        self._eod_ts = datetime.combine(day, dtime(16, 0), tzinfo=NEW_YORK).timestamp()
        self._apply_eod(self._tickers)

    def _apply_eod(self, tickers: list[str]) -> None:
        for ticker in tickers:
            close = self._eod_closes.get(ticker)
            if close:
                prev = self._eod_prev.get(ticker)
                self._cache.update(
                    ticker, close, self._eod_ts, prev_close=prev, clear_prev_close=prev is None
                )

    # --- Calling the SDK, backoff, mode switching ---

    async def _call(self, fn: Any, *args: Any) -> Any:
        """Run a blocking SDK call in a thread with a hard deadline; classify failures.

        The SDK stores timeouts but does not pass them to urllib3, so wait_for is the
        real deadline. (A stuck thread is abandoned, not killed; keep calls few.)
        """
        if self._mode == "eod" and self._call_gap:
            wait = self._last_call + self._call_gap - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        try:
            return await asyncio.wait_for(asyncio.to_thread(fn, *args), self._timeout + 5)
        except MassiveCallError:
            raise
        except Exception as exc:  # includes asyncio.TimeoutError
            raise MassiveCallError(classify_error(exc), _safe(exc)) from exc

    def _on_success(self) -> None:
        self._interval = self._base_interval
        self._last_success = time.time()
        self._last_error = None
        self._degraded = None

    def _on_error(self, err: MassiveCallError) -> None:
        self._last_error = f"{err.kind.value}: {err}"
        if err.kind is ErrorKind.RATE_LIMIT:
            self._interval = min(self._interval * 2, MAX_BACKOFF)
            self._wakeup.clear()  # a ticker added earlier must not cut the wait short
            logger.warning("Massive rate limited; polling every %.0fs", self._interval)
        else:
            logger.warning("Massive call failed (%s): %s", err.kind.value, err)

    async def _fall_back(self, reason: str) -> None:
        """The key stopped working: hand over to a simulator so prices keep moving."""
        if self._fallback:
            return
        self._degraded = reason
        self._last_error = reason
        logger.error("Massive source degraded (%s); falling back to the simulator", reason)
        tickers = list(self._tickers)
        fallback = SimulatorDataSource(
            self._cache,
            seed=self._fallback_seed,
            degraded_reason=reason,
            resume_from_cache=True,  # carry on from the last real prices
        )
        await fallback.start(tickers)
        self._fallback = fallback
        await self._stop_poller()

    def _switch_to_eod(self, err: MassiveCallError) -> None:
        logger.warning("Massive plan has no snapshot access (%s); using end-of-day data", err)
        self._mode = "eod"
        self._degraded = None


def _safe(exc: BaseException) -> str:
    """Error text that can be logged: first 200 chars, API key never included."""
    text = str(exc) or type(exc).__name__
    return text[:200]

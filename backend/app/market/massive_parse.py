"""Pure helpers for the Massive client: no I/O, no asyncio, easy to unit test."""

from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass
from typing import Any

from massive.exceptions import AuthError, BadResponse


def to_unix_seconds(ts: Any, now: float | None = None) -> float:
    """Normalise a Massive timestamp (ns, us, ms or s) to Unix seconds.

    Falls back to `now` (default: time.time()) when the value is missing, not a
    number, or lands outside [now - 10 years, now + 1 day].
    """
    now = time.time() if now is None else now
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts) or ts <= 0:
        return now
    if ts > 1e17:
        seconds = ts / 1e9  # nanoseconds
    elif ts > 1e14:
        seconds = ts / 1e6  # microseconds
    elif ts > 1e11:
        seconds = ts / 1e3  # milliseconds
    else:
        seconds = float(ts)
    return seconds if now - 10 * 365 * 86400 <= seconds <= now + 86400 else now


def _positive(x: Any) -> float | None:
    """x as a float if it is a finite number > 0, else None (0 means 'no data')."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x) if math.isfinite(x) and x > 0 else None


@dataclass(frozen=True, slots=True)
class Quote:
    price: float
    timestamp: float  # Unix seconds
    prev_close: float | None


def extract_quote(snap: Any, now: float | None = None) -> Quote | None:
    """Best available price from one TickerSnapshot, or None if it has no usable price.

    Preference: last_trade (Developer+) > latest minute bar > today's bar > prev day.
    Attribute names are those of massive.rest.models.TickerSnapshot (verified).
    """
    last_trade = getattr(snap, "last_trade", None)
    minute = getattr(snap, "min", None)
    day = getattr(snap, "day", None)
    prev_day = getattr(snap, "prev_day", None)
    prev_close = _positive(getattr(prev_day, "close", None))

    candidates = (
        (
            getattr(last_trade, "price", None),
            getattr(last_trade, "sip_timestamp", None)
            or getattr(last_trade, "participant_timestamp", None)
            or getattr(snap, "updated", None),
        ),
        (getattr(minute, "close", None), getattr(minute, "timestamp", None)),
        (getattr(day, "close", None), getattr(snap, "updated", None)),
    )
    for raw_price, raw_ts in candidates:
        price = _positive(raw_price)
        if price is not None:
            return Quote(price, to_unix_seconds(raw_ts, now), prev_close)
    if prev_close is not None:  # market not open yet: show the last close, flat
        return Quote(prev_close, to_unix_seconds(getattr(snap, "updated", None), now), prev_close)
    return None


class ErrorKind(enum.Enum):
    AUTH = "auth"  # missing / invalid key
    FORBIDDEN = "forbidden"  # plan does not include this endpoint or timeframe
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    NETWORK = "network"  # DNS, timeout, connection reset, 5xx
    OTHER = "other"


def classify_error(exc: BaseException) -> ErrorKind:
    """Map whatever the client raised to an ErrorKind.

    massive.rest raises BadResponse(<response body text>) for any non-200 and does
    not expose the HTTP status, so we classify on the documented JSON bodies.
    With retries=0 a 429 arrives as BadResponse; with retries>0 urllib3 would raise
    MaxRetryError('... too many 429 error responses'), handled below as well.
    """
    if isinstance(exc, AuthError):
        return ErrorKind.AUTH
    text = str(exc)
    low = text.lower()
    if isinstance(exc, BadResponse):
        if "not_authorized" in low or "doesn't include" in low or "not entitled" in low:
            return ErrorKind.FORBIDDEN
        if "maximum requests" in low or "rate limit" in low or "too many requests" in low:
            return ErrorKind.RATE_LIMIT
        if any(s in low for s in ("unknown api key", "invalid api key", "missing api key")):
            return ErrorKind.AUTH
        if "not_found" in low or "not found" in low:
            return ErrorKind.NOT_FOUND
        return ErrorKind.OTHER
    if "too many 429" in low or "429 error" in low:  # urllib3 MaxRetryError wording
        return ErrorKind.RATE_LIMIT
    return ErrorKind.NETWORK

"""Pure-function tests for massive_parse, using the real SDK models."""

import pytest
from massive.exceptions import AuthError, BadResponse
from massive.rest.models import TickerSnapshot

from app.market.massive_parse import ErrorKind, classify_error, extract_quote, to_unix_seconds

NOW = 1_764_081_000.0  # 2025-11-25


def snap(**overrides) -> TickerSnapshot:
    """A TickerSnapshot parsed from the documented JSON shape (camelCase keys)."""
    d = {
        "ticker": "AAPL",
        "updated": 1_764_080_900_000_000_000,
        "day": {"o": 1, "h": 2, "l": 1, "c": 190.4, "v": 10},
        "min": {"c": 190.3, "t": 1_764_080_880_000},
        "prevDay": {"c": 189.0},
        "lastTrade": {"p": 190.5, "t": 1_764_080_900_000_000_000},
    }
    d.update(overrides)
    return TickerSnapshot.from_dict({k: v for k, v in d.items() if v is not None})


class TestToUnixSeconds:
    @pytest.mark.parametrize(
        "raw",
        [1_764_080_900_000_000_000, 1_764_080_900_000_000, 1_764_080_900_000, 1_764_080_900],
    )
    def test_all_units(self, raw):
        assert to_unix_seconds(raw, NOW) == pytest.approx(1_764_080_900)

    @pytest.mark.parametrize("bad", [None, 0, -5, "x", float("nan"), True, 1.0])
    def test_bad_values_fall_back_to_now(self, bad):
        assert to_unix_seconds(bad, NOW) == NOW

    def test_far_future_is_rejected(self):
        assert to_unix_seconds(NOW + 10 * 86400, NOW) == NOW


class TestExtractQuote:
    def test_prefers_last_trade(self):
        q = extract_quote(snap(), NOW)
        assert (q.price, q.prev_close) == (190.5, 189.0)
        assert q.timestamp == pytest.approx(1_764_080_900)

    def test_falls_back_to_minute_bar(self):  # Starter plan: no lastTrade
        q = extract_quote(snap(lastTrade=None), NOW)
        assert q.price == 190.3 and q.timestamp == pytest.approx(1_764_080_880)

    def test_falls_back_to_day_then_prev_close(self):
        assert extract_quote(snap(lastTrade=None, min=None), NOW).price == 190.4
        q = extract_quote(snap(lastTrade=None, min=None, day={"c": 0}), NOW)  # pre-market
        assert q.price == 189.0

    def test_zero_prices_are_not_prices(self):
        s = snap(lastTrade={"p": 0, "t": 1}, min={"c": 0}, day={"c": 0}, prevDay=None)
        assert extract_quote(s, NOW) is None

    def test_empty_snapshot(self):
        assert extract_quote(TickerSnapshot(ticker="X"), NOW) is None


class TestClassifyError:
    def test_auth_error(self):
        assert classify_error(AuthError("no key")) is ErrorKind.AUTH

    @pytest.mark.parametrize(
        "body, kind",
        [
            (
                '{"status":"NOT_AUTHORIZED","message":"Your plan doesn\'t include this data"}',
                ErrorKind.FORBIDDEN,
            ),
            (
                '{"status":"ERROR","error":"You\'ve exceeded the maximum requests per minute"}',
                ErrorKind.RATE_LIMIT,
            ),
            ('{"status":"ERROR","message":"Unknown API Key"}', ErrorKind.AUTH),
            ('{"status":"NOT_FOUND","message":"Ticker not found."}', ErrorKind.NOT_FOUND),
            ("boom", ErrorKind.OTHER),
        ],
    )
    def test_bad_response_bodies(self, body, kind):
        assert classify_error(BadResponse(body)) is kind

    def test_network_and_429_retry_exhaustion(self):
        assert classify_error(TimeoutError("read timed out")) is ErrorKind.NETWORK
        assert classify_error(RuntimeError("too many 429 error responses")) is ErrorKind.RATE_LIMIT

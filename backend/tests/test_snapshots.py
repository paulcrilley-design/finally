"""Portfolio value snapshots: when they are taken, kept and returned."""

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main
from db import connect, execute_trade, init_db, record_snapshots, value_history

pytestmark = pytest.mark.usefixtures("app_env")


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "snap.db"
    init_db(path)
    return path


def values(path: Path) -> list[float]:
    return [row["total_value"] for row in value_history(path, "default")]


def insert(path: Path, recorded_at: str, value: float) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)"
            " VALUES (?, 'default', ?, ?)",
            (f"{recorded_at}-{value}", value, recorded_at),
        )


def test_a_trade_records_the_value_at_once(db_path: Path):
    execute_trade(db_path, "default", "AAPL", "buy", Decimal(10), 100.0)
    execute_trade(db_path, "default", "MSFT", "buy", Decimal(1), 400.0, prices={"AAPL": 110.0})
    assert values(db_path) == [10000.0, 10100.0]


def test_unknown_held_price_skips_the_snapshot(db_path: Path):
    execute_trade(db_path, "default", "AAPL", "buy", Decimal(1), 100.0)
    record_snapshots(db_path, {})
    assert values(db_path) == [10000.0]


def test_refused_trade_records_nothing(db_path: Path):
    with pytest.raises(Exception, match="Not enough"):
        execute_trade(db_path, "default", "AAPL", "buy", Decimal(1000), 100.0)
    assert values(db_path) == []


def test_old_snapshots_are_deleted(db_path: Path):
    now = datetime.now(UTC)
    for age, value in ((timedelta(days=8), 1.0), (timedelta(days=6), 2.0)):
        insert(db_path, (now - age).isoformat(timespec="microseconds"), value)
    record_snapshots(db_path, {})
    assert values(db_path) == [2.0, 10000.0]


def test_history_is_thinned_and_keeps_both_ends(db_path: Path):
    for index in range(1234):
        insert(db_path, f"2099-01-01T00:{index // 60:02d}:{index % 60:02d}", float(index))
    thinned = values(db_path)
    assert len(thinned) == 500
    assert (thinned[0], thinned[-1]) == (0.0, 1233.0)
    assert thinned == sorted(thinned)
    assert value_history(db_path, "nobody") == []


def test_app_snapshots_at_startup_repeatedly_and_after_trades(
    static_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(app.main, "SNAPSHOT_EVERY", 0.05)
    with TestClient(app.main.create_app(static_dir=static_dir)) as client:

        def count() -> int:
            return len(client.get("/api/portfolio/history").json()["history"])

        assert count() >= 1
        deadline = time.monotonic() + 5
        while count() < 3:
            assert time.monotonic() < deadline, "no periodic snapshots"
            time.sleep(0.02)

    monkeypatch.setattr(app.main, "SNAPSHOT_EVERY", 3600)
    with TestClient(app.main.create_app(static_dir=static_dir)) as client:
        before = len(client.get("/api/portfolio/history").json()["history"])
        assert before >= 4  # earlier points survive, plus the new startup one
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1})
        history = client.get("/api/portfolio/history").json()["history"]
        assert len(history) == before + 1
        assert set(history[-1]) == {"recorded_at", "total_value"}

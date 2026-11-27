"""Trading rules, money maths, the portfolio and watchlist APIs, and restarts."""

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.market.simulator import GBMSimulator
from app.routes.portfolio import value_position
from db import TradeError, connect, execute_trade, init_db, load_prices, read_portfolio

pytestmark = pytest.mark.usefixtures("app_env")

CASES = json.loads((Path(__file__).parent / "fixtures" / "valuation_cases.json").read_text())


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "trade.db"
    init_db(path)
    return path


def trade(path: Path, side: str, quantity: str, price: float | None, ticker: str = "AAPL"):
    return execute_trade(path, "default", ticker, side, Decimal(quantity), price)


def state(path: Path) -> tuple:
    with connect(path) as conn:
        history = [tuple(r) for r in conn.execute("SELECT * FROM trades ORDER BY rowid")]
    return read_portfolio(path, "default"), history


def position(path: Path) -> tuple[Decimal, Decimal]:
    [(_, quantity, avg_cost)] = read_portfolio(path, "default")[1]
    return quantity, avg_cost


def test_buys_average_the_cost_and_reduce_cash(db_path: Path):
    trade(db_path, "buy", "10", 190.0)
    trade(db_path, "buy", "5", 200.0)
    assert read_portfolio(db_path, "default")[0] == Decimal("7100.00")
    assert position(db_path) == (Decimal("15"), Decimal("193.3333"))
    assert len(state(db_path)[1]) == 2


def test_fractions_round_money_half_up(db_path: Path):
    trade(db_path, "buy", "0.5", 100.01)  # 50.005
    assert read_portfolio(db_path, "default")[0] == Decimal("9949.99")


def test_selling_keeps_the_average_and_selling_all_removes_the_position(db_path: Path):
    trade(db_path, "buy", "0.3", 100.0)
    trade(db_path, "sell", "0.1", 110.0)
    assert position(db_path) == (Decimal("0.2"), Decimal("100"))
    trade(db_path, "sell", "0.2", 110.0)
    cash, positions = read_portfolio(db_path, "default")
    assert (cash, positions) == (Decimal("10003.00"), [])
    assert len(state(db_path)[1]) == 3


def test_all_the_cash_can_be_spent(db_path: Path):
    trade(db_path, "buy", "100", 100.0)
    assert read_portfolio(db_path, "default")[0] == 0


def test_a_position_worth_under_a_cent_can_still_be_closed(db_path: Path):
    trade(db_path, "buy", "0.0002", 100.0)
    trade(db_path, "sell", "0.0002", 20.0)
    assert read_portfolio(db_path, "default")[1] == []


@pytest.mark.parametrize(
    ("side", "quantity", "price", "code"),
    [
        ("buy", "0", 100.0, "invalid_quantity"),
        ("buy", "-1", 100.0, "invalid_quantity"),
        ("buy", "0.00001", 100.0, "invalid_quantity"),
        ("buy", "NaN", 100.0, "invalid_quantity"),
        ("buy", "Infinity", 100.0, "invalid_quantity"),
        ("buy", "1e30", 100.0, "invalid_quantity"),
        ("buy", "1000", 100.0, "insufficient_cash"),
        ("buy", "1", None, "no_price"),
        ("buy", "0.0001", 1.0, "value_too_small"),
        ("sell", "3", 100.0, "insufficient_shares"),
        ("sell", "0.0001", 1.0, "value_too_small"),
    ],
)
def test_refused_trades_change_nothing(db_path: Path, side, quantity, price, code):
    trade(db_path, "buy", "2", 100.0)
    before = state(db_path)
    with pytest.raises(TradeError) as refusal:
        trade(db_path, side, quantity, price)
    assert refusal.value.code == code
    assert state(db_path) == before


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_concurrent_trades_cannot_overspend(db_path: Path, side: str):
    if side == "sell":
        trade(db_path, "buy", "60", 100.0)

    def attempt(_: int) -> bool:
        try:
            trade(db_path, side, "60", 100.0)
        except TradeError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(8))) == 1


@pytest.mark.parametrize("case", CASES)
def test_valuation(case: dict):
    valued = value_position(
        "AAPL", Decimal(str(case["quantity"])), Decimal(str(case["avg_cost"])), case["price"]
    )
    for key in ("market_value", "unrealized_pnl", "pnl_percent"):
        assert valued[key] == case[key], key


@pytest.fixture
def client(static_dir: Path) -> Iterator[TestClient]:
    with TestClient(create_app(static_dir=static_dir)) as test_client:
        yield test_client


def order(client: TestClient, **body):
    return client.post("/api/portfolio/trade", json=body)


def test_fresh_portfolio(client: TestClient):
    assert client.get("/api/portfolio").json() == {
        "cash": 10000.0,
        "total_value": 10000.0,
        "positions": [],
    }


def test_trade_api_fills_at_the_cached_price(client: TestClient):
    response = order(client, ticker=" aapl ", side="buy", quantity=1.5)
    assert response.status_code == 200
    body = response.json()
    assert body["trade"]["ticker"] == "AAPL"
    [held] = body["portfolio"]["positions"]
    assert held["quantity"] == 1.5
    assert held["avg_cost"] == body["trade"]["price"]
    total = body["portfolio"]["cash"] + held["market_value"]
    assert body["portfolio"]["total_value"] == pytest.approx(total)


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"ticker": "AAPL", "side": "buy", "quantity": "1"}, "invalid_quantity"),
        ({"ticker": "AAPL", "side": "buy", "quantity": True}, "invalid_quantity"),
        ({"ticker": "AAPL", "side": "buy", "quantity": None}, "invalid_quantity"),
        ({"ticker": "AAPL", "side": "hold", "quantity": 1}, "invalid_request"),
        ({"side": "buy", "quantity": 1}, "invalid_request"),
        ({"ticker": "ZZZZ", "side": "buy", "quantity": 1}, "no_price"),
    ],
)
def test_trade_api_errors_share_one_shape(client: TestClient, body: dict, code: str):
    response = client.post("/api/portfolio/trade", json=body)
    assert response.status_code == 400
    assert set(response.json()["error"]) == {"code", "message"}
    assert response.json()["error"]["code"] == code
    assert client.get("/api/portfolio").json()["cash"] == 10000.0


def tickers(response) -> list[str]:
    return [item["ticker"] for item in response.json()["watchlist"]]


def test_added_ticker_is_priced_at_once(client: TestClient):
    response = client.post("/api/watchlist", json={"ticker": " pypl "})
    assert tickers(response)[-1] == "PYPL"
    assert response.json()["watchlist"][-1]["price"] is not None


@pytest.mark.parametrize(
    ("ticker", "status", "code"),
    [("aapl", 409, "already_watched"), ("not a ticker", 400, "invalid_ticker")],
)
def test_add_refusals(client: TestClient, ticker: str, status: int, code: str):
    response = client.post("/api/watchlist", json={"ticker": ticker})
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)


def test_removed_ticker_stops_being_priced(client: TestClient):
    assert "AAPL" not in tickers(client.delete("/api/watchlist/aapl"))
    assert "AAPL" not in client.app.state.price_cache
    response = client.delete("/api/watchlist/AAPL")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_watched")


def test_removed_ticker_with_a_position_stays_priced_until_sold(client: TestClient):
    order(client, ticker="AAPL", side="buy", quantity=1)
    client.delete("/api/watchlist/AAPL")
    assert "AAPL" in client.app.state.price_cache
    assert client.get("/api/portfolio").json()["total_value"] is not None

    sold = order(client, ticker="AAPL", side="sell", quantity=1)
    assert sold.status_code == 200
    assert "AAPL" not in client.app.state.price_cache


def test_restart_continues_from_the_last_prices(app_env: Path, static_dir: Path):
    with TestClient(create_app(static_dir=static_dir)) as first:
        order(first, ticker="AAPL", side="buy", quantity=1)
    saved = load_prices(app_env)
    app = create_app(static_dir=static_dir)
    with TestClient(app):
        update = app.state.price_cache.get("AAPL")
        # One simulator step may already have run; it moves the price very little unless an
        # event fires, and prev_close never moves.
        assert update.prev_close == saved["AAPL"][1]
        assert update.price == pytest.approx(saved["AAPL"][0], rel=0.06)


def test_simulator_resumes_only_the_initial_tickers():
    sim = GBMSimulator(["AAPL"], resume={"AAPL": (123.45, 120.0), "MSFT": (1.0, 1.0)})
    assert (sim.get_price("AAPL"), sim.get_open_price("AAPL")) == (123.45, 120.0)
    sim.add_ticker("MSFT")
    assert sim.get_price("MSFT") != 1.0

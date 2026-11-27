import pytest

import db


def trade(client, ticker, side, quantity):
    return client.post(
        "/api/portfolio/trade", json={"ticker": ticker, "side": side, "quantity": quantity}
    )


def test_initial_portfolio(client):
    assert client.get("/api/portfolio").json() == {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "positions_value": 0.0,
        "unrealized_pnl": 0.0,
        "positions": [],
    }


def test_startup_snapshot(client):
    history = client.get("/api/portfolio/history").json()["history"]
    assert [row["total_value"] for row in history] == [10000.0]


def test_buy_then_value_at_new_price(client, fixed_price):
    fixed_price("AAPL", 190.0)
    response = trade(client, " aapl ", "buy", 10)
    assert response.status_code == 200
    body = response.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["trade"]["price"] == 190.0
    assert body["portfolio"]["cash_balance"] == 8100.0
    assert len(client.get("/api/portfolio/history").json()["history"]) == 2

    fixed_price("AAPL", 191.25)
    portfolio = client.get("/api/portfolio").json()
    assert portfolio["total_value"] == 10012.5
    assert portfolio["positions"] == [
        {
            "ticker": "AAPL",
            "quantity": 10.0,
            "avg_cost": 190.0,
            "current_price": 191.25,
            "market_value": 1912.5,
            "unrealized_pnl": 12.5,
            "unrealized_pnl_percent": 0.6579,
            "weight": 1.0,
        }
    ]


def test_sell_all_removes_position(client, fixed_price):
    fixed_price("AAPL", 100.0)
    trade(client, "AAPL", "buy", 2.5)
    portfolio = trade(client, "AAPL", "sell", 2.5).json()["portfolio"]
    assert portfolio["positions"] == []
    assert portfolio["cash_balance"] == 10000.0


def test_unpriced_position(client, fixed_price):
    fixed_price("AAPL", 100.0)
    fixed_price("MSFT", 100.0)
    trade(client, "AAPL", "buy", 1)
    trade(client, "MSFT", "buy", 1)
    client.app.state.price_cache.remove("MSFT")
    portfolio = client.get("/api/portfolio").json()
    positions = {p["ticker"]: p for p in portfolio["positions"]}
    for field in ("current_price", "market_value", "unrealized_pnl", "weight"):
        assert positions["MSFT"][field] is None
    assert positions["AAPL"]["weight"] == 1.0
    assert portfolio["total_value"] == 9900.0


def test_no_snapshot_when_unpriced(client, fixed_price):
    fixed_price("AAPL", 100.0)
    trade(client, "AAPL", "buy", 1)
    before = len(db.list_snapshots("default"))
    client.app.state.price_cache.remove("AAPL")
    from app.services.snapshots import snapshot_all

    snapshot_all(client.app.state)
    assert len(db.list_snapshots("default")) == before


def test_held_ticker_stays_tracked_until_sold(client):
    trade(client, "AAPL", "buy", 1)
    assert client.delete("/api/watchlist/AAPL").status_code == 204
    assert "AAPL" in client.app.state.market_source.get_tickers()
    assert trade(client, "AAPL", "sell", 1).status_code == 200
    assert "AAPL" not in client.app.state.market_source.get_tickers()


@pytest.mark.parametrize(
    ("ticker", "side", "quantity", "code"),
    [
        ("!!", "buy", 1, "invalid_ticker"),
        ("AAPL", "hold", 1, "invalid_side"),
        ("AAPL", "buy", 0, "invalid_quantity"),
        ("AAPL", "buy", -1, "invalid_quantity"),
        ("AAPL", "buy", 0.00001, "invalid_quantity"),
        ("AAPL", "buy", "nan", "invalid_quantity"),
        ("AAPL", "buy", "inf", "invalid_quantity"),
        ("ZZZZ", "buy", 1, "no_price"),
        ("AAPL", "buy", 1e308, "insufficient_cash"),
        ("AAPL", "sell", 1, "insufficient_shares"),
    ],
)
def test_rejected_trades(client, ticker, side, quantity, code):
    response = trade(client, ticker, side, quantity)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code
    assert db.list_trades("default") == []
    assert db.get_cash("default") == 10000.0


def test_buy_worth_nothing_is_rejected(client, fixed_price):
    fixed_price("AAPL", 10.0)
    response = trade(client, "AAPL", "buy", 0.0001)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_quantity"
    assert db.list_trades("default") == []
    assert db.get_cash("default") == 10000.0


def test_tiny_position_can_be_closed(client, fixed_price):
    fixed_price("AAPL", 10.0)
    db.apply_trade("default", "AAPL", "buy", 0.0001, 10.0)
    response = trade(client, "AAPL", "sell", 0.0001)
    assert response.status_code == 200
    assert response.json()["portfolio"]["positions"] == []


def test_invalid_request_body(client):
    response = client.post("/api/portfolio/trade", json={"ticker": "AAPL"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"

"""Orders given as a US dollar amount."""

import pytest

import db

URL = "/api/portfolio/trade"


@pytest.fixture
def priced(client):
    """The app with the simulator frozen, so prices are exactly what the test sets."""
    source = client.app.state.market_source
    source._task.cancel()

    def set_price(price, ticker="AAPL"):
        client.app.state.price_cache.update(ticker, price)

    set_price(190.0)
    return client, set_price


def order(client, side="buy", **size):
    return client.post(URL, json={"ticker": "AAPL", "side": side, **size})


@pytest.mark.parametrize("price", [190.0, 3.17, 842.37, 9999.99])
def test_buy_spends_exactly_the_amount(priced, price):
    client, set_price = priced
    set_price(price)
    body = order(client, amount=500).json()
    assert body["trade"]["value"] == 500.0
    assert body["portfolio"]["cash_balance"] == 9500.0


def test_all_the_cash_can_be_spent(priced):
    client, _ = priced
    assert order(client, amount=10_000).json()["portfolio"]["cash_balance"] == 0.0


def test_very_high_prices_never_cost_more_than_asked(priced):
    client, set_price = priced
    set_price(612_345.67)
    assert order(client, amount=500).json()["trade"]["value"] <= 500.0


def test_sell_by_amount(priced):
    client, _ = priced
    order(client, amount=500)
    body = order(client, "sell", amount=200).json()
    assert body["trade"]["value"] == 200.0
    assert body["portfolio"]["cash_balance"] == 9700.0


def test_selling_the_shown_value_closes_the_position(priced):
    client, set_price = priced
    order(client, quantity=0.526315)
    set_price(189.99)  # worth $99.994585..., shown as $99.99
    body = order(client, "sell", amount=99.99).json()
    assert body["trade"]["quantity"] == 0.526315
    assert db.get_position("default", "AAPL") is None


@pytest.mark.parametrize(
    ("side", "size", "code"),
    [
        ("buy", {"amount": 10_000.01}, "insufficient_cash"),
        ("buy", {"amount": 1e308}, "insufficient_cash"),
        ("sell", {"amount": 5}, "insufficient_shares"),
        ("buy", {"amount": 0}, "invalid_amount"),
        ("buy", {"amount": -5}, "invalid_amount"),
        ("buy", {"amount": 0.004}, "invalid_amount"),
        ("buy", {"amount": 5, "quantity": 1}, "invalid_request"),
        ("buy", {}, "invalid_request"),
    ],
)
def test_rejections_change_nothing(priced, side, size, code):
    client, _ = priced
    response = order(client, side, **size)
    assert response.json()["error"]["code"] == code
    assert db.get_cash("default") == 10_000.0


def test_selling_more_than_held_by_amount(priced):
    client, _ = priced
    order(client, amount=100)
    assert order(client, "sell", amount=101).json()["error"]["code"] == "insufficient_shares"

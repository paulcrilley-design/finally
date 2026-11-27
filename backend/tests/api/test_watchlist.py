FIELDS = {
    "ticker",
    "price",
    "previous_price",
    "timestamp",
    "direction",
    "prev_close",
    "day_change",
    "day_change_percent",
}


def tickers(client):
    return [item["ticker"] for item in client.get("/api/watchlist").json()["tickers"]]


def test_default_watchlist_is_priced(client):
    items = client.get("/api/watchlist").json()["tickers"]
    assert len(items) == 10
    assert set(items[0]) == FIELDS
    assert all(item["price"] is not None for item in items)


def test_unpriced_item_has_nulls(client):
    client.app.state.price_cache.remove("AAPL")
    # The simulator may re-price it on its next tick, so call the service shape directly.
    from app.services.watchlist import _item

    item = _item(client.app.state.price_cache, "NOPE")
    assert set(item) == FIELDS
    assert all(item[field] is None for field in FIELDS - {"ticker"})


def test_add_and_remove(client):
    response = client.post("/api/watchlist", json={"ticker": " pypl "})
    assert response.status_code == 201
    assert response.json()["ticker"] == "PYPL"
    assert response.json()["price"] is not None
    assert tickers(client)[-1] == "PYPL"
    assert "PYPL" in client.app.state.market_source.get_tickers()

    assert client.delete("/api/watchlist/pypl").status_code == 204
    assert "PYPL" not in tickers(client)
    assert "PYPL" not in client.app.state.market_source.get_tickers()


def test_errors(client):
    cases = [
        (client.post("/api/watchlist", json={"ticker": "AAPL"}), 409, "already_watching"),
        (client.post("/api/watchlist", json={"ticker": "$$"}), 400, "invalid_ticker"),
        (client.post("/api/watchlist", json={}), 422, "invalid_request"),
        (client.delete("/api/watchlist/PYPL"), 404, "not_watching"),
    ]
    for response, status, code in cases:
        assert response.status_code == status
        assert response.json()["error"]["code"] == code

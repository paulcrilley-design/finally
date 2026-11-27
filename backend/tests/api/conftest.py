import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "static"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.setenv("SIM_SEED", "1")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def fixed_price(client):
    """Stop the simulator's ticks and return a function that sets a price."""
    source = client.app.state.market_source
    client.portal.call(source._task.cancel)

    def set_price(ticker: str, price: float) -> None:
        client.app.state.price_cache.update(ticker, price)

    return set_price

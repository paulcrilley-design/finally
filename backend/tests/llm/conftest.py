"""Chat endpoint over a temporary database, fixed prices and a faked LLM."""

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db
from app.errors import register_error_handlers
from app.llm import client as llm_client
from app.llm import create_chat_router
from app.market import PriceCache

PRICES = {"AAPL": 100.0, "MSFT": 200.0, "PYPL": 50.0}


class FakeSource:
    def __init__(self):
        self.tickers: set[str] = set()

    def get_tickers(self):
        return list(self.tickers)

    async def add_ticker(self, ticker):
        self.tickers.add(ticker)

    async def remove_ticker(self, ticker):
        self.tickers.discard(ticker)

    async def validate_ticker(self, ticker):
        return True


class FakeLLM:
    """Stands in for litellm.acompletion: replies are served in order."""

    def __init__(self):
        self.replies: list = []
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        content = reply if isinstance(reply, str) else json.dumps(reply)
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture(autouse=True)
def environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MOCK", raising=False)
    db.init_db()


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm_client, "acompletion", fake)
    return fake


@pytest.fixture
def api(llm):
    app = FastAPI()
    register_error_handlers(app)
    cache = PriceCache()
    for ticker, price in PRICES.items():
        cache.update(ticker, price)
    app.state.price_cache = cache
    app.state.market_source = FakeSource()
    app.include_router(create_chat_router())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def chat(api):
    def send(message: str) -> dict:
        response = api.post("/api/chat", json={"message": message})
        assert response.status_code == 200, response.text
        return response.json()

    return send

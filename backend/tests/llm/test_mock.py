"""LLM_MOCK=true: deterministic and offline."""

import pytest

import db
from app.llm import mock

USER = "default"


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "TRUE")
    monkeypatch.delenv("OPENROUTER_API_KEY")


def test_no_actions(chat, llm):
    body = chat("how is my portfolio?")
    assert body["message"] == "Mock response: your portfolio looks balanced."
    assert body["trades"] == body["watchlist_changes"] == []
    assert llm.calls == []


def test_repeatable_actions(chat, llm):
    body = chat("BUY 5 aapl, buy 1.5 MSFT, Sell 2 AAPL. Add PYPL and remove NFLX.")
    assert body["message"].startswith("Mock response: here is your request.\nRejected: sell")
    assert [(t["side"], t["quantity"], t["ticker"], t["status"]) for t in body["trades"]] == [
        ("buy", 5.0, "AAPL", "executed"),
        ("buy", 1.5, "MSFT", "executed"),
        # Validated before the buys execute, so there is nothing to sell yet.
        ("sell", 2.0, "AAPL", "rejected"),
    ]
    assert [(c["action"], c["ticker"], c["status"]) for c in body["watchlist_changes"]] == [
        ("add", "PYPL", "executed"),
        ("remove", "NFLX", "executed"),
    ]
    assert db.get_position(USER, "AAPL")["quantity"] == 5.0
    assert llm.calls == []


def test_reject_trigger(chat):
    body = chat("buy 5 AAPL and add PYPL, then REJECT")
    actions = body["trades"] + body["watchlist_changes"]
    assert [a["status"] for a in actions] == ["rejected", "rejected"]
    assert actions[0]["review"] == {"verdict": "reject", "reason": "Mock reviewer rejection."}
    assert body["error"] is None
    assert db.list_trades(USER) == []


def test_dollar_orders():
    trades = mock.propose("buy $500 of AAPL and sell $20.50 TSLA, buy 2 MSFT").trades
    assert [(t.ticker, t.amount, t.quantity) for t in trades] == [
        ("AAPL", 500.0, None),
        ("TSLA", 20.5, None),
        ("MSFT", None, 2.0),
    ]

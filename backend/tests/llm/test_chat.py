"""Chat flow with faked proposer and reviewer calls."""

import asyncio

import pytest

import db
from app.llm import client as llm_client

USER = "default"


def proposal(trades=(), changes=(), message="Sure."):
    return {"message": message, "trades": list(trades), "watchlist_changes": list(changes)}


def trade(ticker="AAPL", side="buy", quantity=5):
    return {"ticker": ticker, "side": side, "quantity": quantity}


def change(ticker="PYPL", action="add"):
    return {"ticker": ticker, "action": action}


def verdict(index, kind="trade", result="approve", reason="Fine."):
    return {"action_index": index, "type": kind, "verdict": result, "reason": reason}


def reviews(*items, summary=None):
    return {"reviews": list(items), "summary": summary}


def test_conversation_skips_reviewer_and_persists(chat, llm):
    llm.replies = [proposal(message="All good.")]
    body = chat("  how am I doing?  ")
    assert body == {"message": "All good.", "trades": [], "watchlist_changes": [], "error": None}
    assert len(llm.calls) == 1
    user, assistant = db.list_chat_messages(USER)
    assert (user["content"], user["actions"]) == ("how am I doing?", None)
    assert assistant["actions"] == {"trades": [], "watchlist_changes": [], "error": None}


def test_proposer_request(chat, llm):
    for i in range(12):
        db.add_chat_message(USER, "user", f"old {i}")
    llm.replies = [proposal()]
    chat("hello")
    call = llm.calls[0]
    assert call["model"] == llm_client.MODEL
    assert call["extra_body"] == {"provider": {"order": ["cerebras"]}}
    assert call["reasoning_effort"] == "low"
    messages = call["messages"]
    assert len(messages) == 13  # system, 10 history, portfolio, user
    assert messages[1]["content"] == "old 2"
    assert "AAPL:100.0" in messages[-2]["content"]
    assert messages[-1] == {"role": "user", "content": "hello"}


def test_approved_actions_execute(chat, llm):
    llm.replies = [
        proposal([trade(ticker=" aapl ")], [change()]),
        reviews(verdict(0, "watchlist_change"), verdict(1), summary="Looks sensible."),
    ]
    body = chat("buy 5 AAPL and watch PYPL")
    assert body["trades"] == [
        {
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 5.0,
            "status": "executed",
            "price": 100.0,
            "reason": None,
            "review": {"verdict": "approve", "reason": "Fine."},
        }
    ]
    assert body["watchlist_changes"][0]["status"] == "executed"
    assert body["message"] == "Sure.\nLooks sensible."
    assert db.get_cash(USER) == 9500.0
    assert "PYPL" in db.list_watchlist(USER)
    assert "watchlist" not in llm.calls[1]["messages"][1]["content"].split('"proposed_actions"')[0]
    assert db.list_chat_messages(USER)[-1]["actions"]["trades"] == body["trades"]


def test_invalid_actions_never_reach_reviewer(chat, llm):
    llm.replies = [proposal([trade(quantity=1000)], [change("AAPL", "add")])]
    body = chat("buy 1000 AAPL")
    assert len(llm.calls) == 1
    assert body["trades"][0]["status"] == "rejected"
    assert body["trades"][0]["review"] is None
    assert body["watchlist_changes"][0]["review"] is None
    assert "Rejected: buy 1000 AAPL - Not enough cash" in body["message"]
    assert "Rejected: add AAPL" in body["message"]
    assert body["error"] is None


def test_rejected_and_missing_verdicts_block(chat, llm):
    llm.replies = [
        proposal([trade(), trade("MSFT"), trade("PYPL")]),
        reviews(
            verdict(0, result="reject", reason="Not asked for."),
            verdict(2, "watchlist_change"),  # wrong type: not a verdict for this trade
        ),
    ]
    body = chat("buy something")
    assert [t["status"] for t in body["trades"]] == ["rejected"] * 3
    assert body["trades"][0]["reason"] == "Not asked for."
    assert body["trades"][1]["review"]["verdict"] == "reject"
    assert db.list_trades(USER) == []


def test_conflicting_verdicts_reject(chat, llm):
    llm.replies = [proposal([trade()]), reviews(verdict(0), verdict(0, result="reject"))]
    assert chat("buy 5 AAPL")["trades"][0]["status"] == "rejected"


@pytest.mark.parametrize(
    "failure", [TimeoutError(), RuntimeError("boom"), "not json", '{"reviews": "no"}']
)
def test_review_failure_blocks_everything(chat, llm, failure):
    llm.replies = [proposal([trade()], [change()]), failure]
    body = chat("buy 5 AAPL and add PYPL")
    assert body["error"] == "review_failed"
    actions = body["trades"] + body["watchlist_changes"]
    assert [a["status"] for a in actions] == ["rejected", "rejected"]
    assert "safety review failed" in body["message"]
    assert db.list_trades(USER) == []
    assert "PYPL" not in db.list_watchlist(USER)


@pytest.mark.parametrize(
    "failure",
    [RuntimeError("boom"), "not json", '{"trades": []}', proposal([trade(quantity="NaN")])],
)
def test_proposer_failure(chat, llm, failure):
    llm.replies = [failure]
    body = chat("buy 5 AAPL")
    assert body["error"] == "llm_unavailable"
    assert body["trades"] == body["watchlist_changes"] == []
    assert db.list_chat_messages(USER)[-1]["actions"]["error"] == "llm_unavailable"


def test_missing_key(chat, llm, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY")
    body = chat("hello")
    assert body["error"] == "llm_unavailable"
    assert "OPENROUTER_API_KEY" in body["message"]
    assert llm.calls == []


def test_timeout(chat, monkeypatch):
    async def hang(**kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr(llm_client, "acompletion", hang)
    monkeypatch.setattr(llm_client, "TIMEOUT_SECONDS", 0.01)
    assert chat("hello")["error"] == "llm_unavailable"


def test_jointly_unaffordable_trades_execute_independently(chat, llm):
    llm.replies = [
        proposal([trade(quantity=60), trade(quantity=60)]),
        reviews(verdict(0), verdict(1)),
    ]
    body = chat("buy 60 AAPL twice")
    assert [t["status"] for t in body["trades"]] == ["executed", "rejected"]
    assert "Not enough cash" in body["trades"][1]["reason"]
    assert body["trades"][1]["review"]["verdict"] == "approve"


@pytest.mark.parametrize("message", ["", "   ", "x" * 2001])
def test_invalid_request(api, message):
    response = api.post("/api/chat", json={"message": message})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_reviewer_sees_only_the_previous_assistant_reply(chat, llm):
    llm.replies = [
        proposal(message="Older reply."),
        proposal(message="Shall I buy 5 AAPL?"),
        proposal(trades=[trade()]),
        reviews(verdict(0)),
    ]
    chat("hello")
    chat("any ideas?")
    chat("yes")
    sent = llm.calls[-1]["messages"][-1]["content"]
    assert "Shall I buy 5 AAPL?" in sent
    assert "Older reply." not in sent and "any ideas?" not in sent


def test_history_returns_stored_messages(api, chat, llm):
    assert api.get("/api/chat/history").json() == {"messages": []}
    llm.replies = [proposal(message="Hi.")]
    chat("hello")
    messages = api.get("/api/chat/history").json()["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "hello"),
        ("assistant", "Hi."),
    ]
    assert messages[1]["actions"] == {"trades": [], "watchlist_changes": [], "error": None}

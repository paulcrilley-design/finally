"""The chat: review, execution, failures, limits and the model client. No network."""

import json
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.chat import PROPOSER_PROMPT
from app.llm import MockClient, ModelError, OpenRouterClient, Proposal, ReviewResult
from app.main import create_app
from db import add_exchange

pytestmark = pytest.mark.usefixtures("app_env")


class FakeModel(MockClient):
    """The mock, recording what it is sent and optionally misbehaving."""

    def __init__(self) -> None:
        self.proposal: Proposal | None = None
        self.review_result: ReviewResult | Exception | None = None
        self.proposals: list[list[dict]] = []
        self.reviews: list[dict] = []

    async def propose(self, messages):
        self.proposals.append(messages)
        return self.proposal or await super().propose(messages)

    async def review(self, messages):
        self.reviews.append(json.loads(messages[-1]["content"]))
        if isinstance(self.review_result, Exception):
            raise self.review_result
        return self.review_result or await super().review(messages)


@pytest.fixture
def model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def client(static_dir: Path, model: FakeModel) -> Iterator[TestClient]:
    app = create_app(static_dir=static_dir)
    app.state.llm = model
    with TestClient(app) as test_client:
        yield test_client


def say(client: TestClient, message: str) -> dict:
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200, response.text
    return response.json()["messages"][1]


def portfolio(client: TestClient) -> dict:
    return client.get("/api/portfolio").json()


def watched(client: TestClient) -> list[str]:
    return [i["ticker"] for i in client.get("/api/watchlist").json()["watchlist"]]


def statuses(reply: dict) -> list[str]:
    return [action["status"] for action in reply["actions"]]


def test_question_is_answered_without_a_review(client: TestClient, model: FakeModel):
    reply = say(client, "How am I doing?")
    assert reply["content"] == "You have $10,000.00 in cash and 0 open positions."
    assert reply["actions"] == [] and model.reviews == []


def test_approved_trade_and_watchlist_changes_execute(client: TestClient):
    reply = say(client, "add PYPL, buy 2 PYPL and remove NFLX.")
    assert statuses(reply) == ["executed", "executed", "executed"]
    assert portfolio(client)["positions"][0]["ticker"] == "PYPL"
    assert "PYPL" in watched(client) and "NFLX" not in watched(client)
    assert reply["actions"][1]["price"] > 0
    assert reply["actions"][1]["review"]["verdict"] == "approve"


def test_rejected_by_the_reviewer(client: TestClient):
    reply = say(client, "buy 1 AAPL and add PYPL, then reject")
    assert statuses(reply) == ["rejected", "rejected"]
    assert reply["actions"][0]["reason"] == "Rejected by the mock reviewer."
    assert portfolio(client)["cash"] == 10000.0 and "PYPL" not in watched(client)


@pytest.mark.parametrize(
    "failure",
    [ModelError("model_unavailable", "down"), RuntimeError("boom"), ReviewResult(reviews=[])],
)
def test_review_failure_executes_nothing(client: TestClient, model: FakeModel, failure):
    model.review_result = failure
    reply = say(client, "buy 1 AAPL and remove NFLX")
    assert statuses(reply) == ["rejected", "rejected"]
    assert portfolio(client)["cash"] == 10000.0 and "NFLX" in watched(client)


def test_conflicting_verdicts_reject(client: TestClient, model: FakeModel):
    model.review_result = ReviewResult(
        reviews=[
            {"action_index": 0, "verdict": "approve"},
            {"action_index": 0, "verdict": "reject", "reason": "No."},
        ]
    )
    assert statuses(say(client, "buy 1 AAPL")) == ["rejected"]


def test_code_checks_come_before_the_reviewer(client: TestClient, model: FakeModel):
    reply = say(client, "buy 1000 AAPL, sell 1 MSFT, buy 1 ZZZZ and buy 1 V")
    assert statuses(reply) == ["rejected", "rejected", "rejected", "executed"]
    assert [a["ticker"] for a in model.reviews[0]["actions"]] == ["V"]
    assert "Not enough cash" in reply["actions"][0]["reason"]


def test_trades_cannot_overspend_together(client: TestClient):
    reply = say(client, "buy 30 AAPL and buy 30 AAPL")
    assert statuses(reply) == ["executed", "rejected"]


def test_only_five_actions_of_a_kind(client: TestClient):
    reply = say(client, " ".join("buy 1 V," for _ in range(7)))
    assert statuses(reply).count("executed") == 5
    assert statuses(reply).count("rejected") == 2


def test_history_survives_and_only_ten_messages_are_sent(client: TestClient, model: FakeModel):
    for index in range(7):
        say(client, f"question {index}")
    messages = client.get("/api/chat").json()["messages"]
    assert len(messages) == 14 and messages[0]["content"] == "question 0"
    sent = model.proposals[-1]
    assert sent[0] == {"role": "system", "content": PROPOSER_PROMPT}
    assert len(sent) == 12  # system, ten past messages, the new one
    assert sent[1]["content"] == "question 1"


def test_past_results_are_sent_with_past_answers(client: TestClient, model: FakeModel):
    say(client, "buy 1000 AAPL")
    say(client, "what happened?")
    assert "buy 1000 AAPL: rejected" in model.proposals[-1][-2]["content"]


@pytest.mark.parametrize("message", ["", "   ", "x" * 1001])
def test_message_length_is_limited(client: TestClient, message: str):
    response = client.post("/api/chat", json={"message": message})
    assert response.json()["error"]["code"] == "invalid_message"


def test_missing_key_is_explained_and_nothing_else_breaks(client: TestClient):
    client.app.state.llm = OpenRouterClient("")
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "no_api_key"
    assert client.get("/api/chat").json() == {"messages": []}
    assert client.get("/api/portfolio").status_code == 200


def test_second_message_waits_for_the_first(client: TestClient):
    client.app.state.chatting.add("default")
    response = client.post("/api/chat", json={"message": "hi"})
    assert (response.status_code, response.json()["error"]["code"]) == (409, "chat_busy")


def model_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def live(*responses, **options) -> tuple[OpenRouterClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        response = responses[min(len(seen), len(responses)) - 1]
        if isinstance(response, Exception):
            raise response
        return response

    return OpenRouterClient("test-key", httpx.MockTransport(handle), **options), seen


MESSAGES = [{"role": "user", "content": "{}"}]


async def test_client_asks_cerebras_for_structured_output():
    client, seen = live(model_reply('{"message": "ok", "trades": [], "watchlist_changes": []}'))
    assert (await client.propose(MESSAGES)).message == "ok"
    body = json.loads(seen[0].content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["provider"] == {"order": ["cerebras"]}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert (body["max_tokens"], body["reasoning"]) == (800, {"effort": "low"})
    assert seen[0].headers["authorization"] == "Bearer test-key"


@pytest.mark.parametrize(
    ("failure", "code", "attempts"),
    [
        (httpx.ConnectError("no"), "model_unavailable", 2),
        (httpx.Response(500), "model_unavailable", 2),
        (httpx.Response(429), "model_unavailable", 1),
        (httpx.Response(401), "bad_api_key", 1),
        (httpx.Response(200, text="not json"), "model_bad_output", 2),
        (model_reply('{"trades": []}'), "model_bad_output", 2),
        (httpx.Response(200, json={"choices": []}), "model_bad_output", 2),
    ],
)
async def test_proposer_failures(failure, code: str, attempts: int):
    client, seen = live(failure)
    with pytest.raises(ModelError) as error:
        await client.propose(MESSAGES)
    assert (error.value.code, len(seen)) == (code, attempts)


async def test_proposer_retry_can_succeed():
    client, seen = live(httpx.Response(502), model_reply('{"message": "ok"}'))
    assert (await client.propose(MESSAGES)).message == "ok" and len(seen) == 2


async def test_reviewer_is_not_retried():
    client, seen = live(httpx.Response(500))
    with pytest.raises(ModelError):
        await client.review(MESSAGES)
    assert len(seen) == 1


def test_context_carries_the_weights(client: TestClient, model: FakeModel):
    say(client, "buy 10 AAPL")
    say(client, "how concentrated am I?")
    context = json.loads(model.proposals[-1][-1]["content"])["portfolio"]
    [held] = context["positions"]
    assert held["percent_of_total"] == pytest.approx(19, abs=1)
    assert held["percent_of_total"] + context["cash_percent_of_total"] == pytest.approx(
        100, abs=0.02
    )


def test_watchlist_changes_that_cannot_work_are_not_reviewed(
    client: TestClient, model: FakeModel
):
    reply = say(client, "add AAPL, remove PYPL, add 123 and sell 0.00001 V")
    assert set(statuses(reply)) == {"rejected"}
    assert model.reviews == []
    assert all(action["reason"] for action in reply["actions"])


def test_one_failed_action_does_not_stop_the_others(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    async def broken(*args):
        raise RuntimeError("disk full")

    monkeypatch.setattr("app.chat.watch", broken)
    reply = say(client, "add PYPL and buy 1 V")
    assert statuses(reply) == ["rejected", "executed"]
    assert reply["actions"][0]["reason"] == "It could not be executed."
    assert portfolio(client)["positions"][0]["ticker"] == "V"


def test_history_saved_by_an_earlier_version_does_not_break_chat(
    client: TestClient, model: FakeModel
):
    old = {"trades": [], "watchlist_changes": [], "error": None}
    add_exchange(client.app.state.db_path, "default", "hello", "Hi.", old)
    assert say(client, "buy 1 V")["actions"][0]["status"] == "executed"
    assert model.proposals[0][2] == {"role": "assistant", "content": "Hi."}
    assert client.get("/api/chat").json()["messages"][1]["actions"] is None

import asyncio

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.snapshots import run_snapshot_loop


def test_health(client):
    assert client.get("/api/health").json() == {
        "status": "ok",
        "market": {"mode": "simulator", "degraded": False, "tickers": 10},
        "llm_mock": True,
    }


def test_routes_registered(client):
    paths = {route.path for route in client.app.routes}
    assert {"/api/stream/prices", "/api/chat"} <= paths


def test_unknown_api_path_is_json_404(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<p>home</p>")
    (static / "404.html").write_text("<p>missing</p>")
    with TestClient(create_app()) as client:
        assert client.get("/").text == "<p>home</p>"
        assert client.get("/nope").status_code == 404
        for response in (client.get("/api/nope"), client.post("/api/nope"), client.get("/api")):
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "not_found"


def test_runs_without_static_dir(client):
    assert client.get("/").status_code == 404


def test_unexpected_error_is_json(monkeypatch):
    def boom(*args):
        raise RuntimeError("boom")

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        monkeypatch.setattr("db.list_snapshots", boom)
        response = client.get("/api/portfolio/history")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


async def test_snapshot_loop_repeats_and_survives_errors(monkeypatch):
    calls = []

    def fake(state):
        calls.append(state)
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.snapshots.snapshot_all", fake)
    task = asyncio.create_task(run_snapshot_loop(None, interval=0.001))
    while len(calls) < 2:
        await asyncio.sleep(0.001)
    task.cancel()

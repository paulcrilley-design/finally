"""The uvicorn entry point. Recorders stand in, so no real env file is opened."""

import importlib
import sys

import dotenv
import pytest

import app.main


def test_server_loads_env_without_override(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple] = []
    created = object()

    def fake_load_dotenv(path, *, override):
        calls.append(("load_dotenv", path, override))

    def fake_create_app():
        calls.append(("create_app",))
        return created

    monkeypatch.setattr(dotenv, "load_dotenv", fake_load_dotenv)
    monkeypatch.setattr(app.main, "create_app", fake_create_app)
    monkeypatch.delitem(sys.modules, "app.server", raising=False)
    try:
        server = importlib.import_module("app.server")
        assert server.app is created
        assert calls == [
            ("load_dotenv", app.main.PROJECT_ROOT / ".env", False),
            ("create_app",),
        ]
    finally:
        sys.modules.pop("app.server", None)

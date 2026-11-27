"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


# Not autouse: tests/market/test_factory.py selects sources through the same variables.
@pytest.fixture
def app_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "finally.db"
    monkeypatch.setenv("MARKET_FORCE_SIMULATOR", "true")
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_path))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("FINALLY_STATIC_DIR", raising=False)
    monkeypatch.setenv("LLM_MOCK", "true")  # tests never call a model
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return db_path


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    (out / "index.html").write_text("<h1>FinAlly stub</h1>")
    return out

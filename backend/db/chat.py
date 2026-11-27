"""Stored conversations."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .database import connect


def add_exchange(
    path: Path, user_id: str, question: str, answer: str, actions: list[dict]
) -> list[dict]:
    """Store a question and its answer together, and return both messages."""
    messages = [
        _message("user", question, None),
        _message("assistant", answer, actions),
    ]
    with connect(path) as conn:
        conn.executemany(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    m["id"],
                    user_id,
                    m["role"],
                    m["content"],
                    None if m["actions"] is None else json.dumps(m["actions"]),
                    m["created_at"],
                )
                for m in messages
            ],
        )
    return messages


def _message(role: str, content: str, actions: list[dict] | None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": datetime.now(UTC).isoformat(timespec="microseconds"),
    }


def recent_messages(path: Path, user_id: str, limit: int) -> list[dict]:
    """The newest `limit` messages, oldest first."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages"
            " WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        {**dict(row), "actions": None if row["actions"] is None else json.loads(row["actions"])}
        for row in reversed(rows)
    ]

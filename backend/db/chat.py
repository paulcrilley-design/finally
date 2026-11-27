"""Chat history."""

import json
import uuid

from .connection import connect, utc_now


def add_chat_message(user_id: str, role: str, content: str, actions: dict | None = None) -> dict:
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": utc_now(),
    }
    encoded = None if actions is None else json.dumps(actions)
    with connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (:id, :user_id, :role, :content, :actions, :created_at)",
            {**message, "user_id": user_id, "actions": encoded},
        )
    return message


def list_chat_messages(user_id: str, limit: int = 10) -> list[dict]:
    """The newest `limit` messages, returned oldest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (user_id, max(limit, 0)),
        ).fetchall()
    return [
        {**dict(row), "actions": None if row["actions"] is None else json.loads(row["actions"])}
        for row in reversed(rows)
    ]

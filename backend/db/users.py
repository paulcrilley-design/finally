"""User profiles."""

from .connection import connect


def list_user_ids() -> list[str]:
    with connect() as conn:
        rows = conn.execute("SELECT id FROM users_profile ORDER BY created_at, id").fetchall()
    return [row["id"] for row in rows]


def get_cash(user_id: str) -> float:
    """Cash balance. Raises KeyError for an unknown user."""
    with connect() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise KeyError(user_id)
    return row["cash_balance"]

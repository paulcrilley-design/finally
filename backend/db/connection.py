"""SQLite connection handling."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "db" / "finally.db"


def db_path() -> Path:
    """Location of the SQLite file, read from DB_PATH on every call."""
    return Path(os.environ.get("DB_PATH") or DEFAULT_DB_PATH)


def utc_now() -> str:
    """Current time as a fixed-width ISO 8601 UTC string, so text order is time order."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """A short-lived autocommit connection, closed on exit."""
    conn = sqlite3.connect(db_path(), isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """A connection inside BEGIN IMMEDIATE: commits on success, rolls back on any error."""
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            conn.rollback()
            raise

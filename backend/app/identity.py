"""Who is making the request. Adding login later changes only this module."""

from __future__ import annotations

from db import DEFAULT_USER_ID


def get_current_user() -> str:
    """The single default user: identity never comes from the request."""
    return DEFAULT_USER_ID

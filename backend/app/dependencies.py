"""Shared FastAPI dependencies."""


def get_current_user() -> str:
    """The single place user identity is resolved. Auth would replace this."""
    return "default"

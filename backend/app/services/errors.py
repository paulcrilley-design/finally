"""Errors raised by the service layer."""


class ServiceError(Exception):
    """A request the app refuses. Turned into a JSON error response."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

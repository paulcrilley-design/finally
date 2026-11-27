"""One error body for every refusal: {"error": {"code", "message"}}."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _body(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    return _body(error.code, error.message, error.status)


async def invalid_request_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    """Name the first bad field, without echoing what was sent."""
    location = error.errors()[0]["loc"]
    field = str(location[1]) if len(location) > 1 else "body"
    if field == "quantity":
        return _body("invalid_quantity", "Quantity must be a number.", 400)
    return _body("invalid_request", f"Missing or invalid {field}.", 400)

"""Turn every API error into {"error": {"code", "message"}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.services.errors import ServiceError

logger = logging.getLogger(__name__)


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


async def _service_error(request: Request, exc: ServiceError) -> JSONResponse:
    return _error(exc.code, exc.message, exc.status)


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"][1:]) or "body"
    return _error("invalid_request", f"Invalid request: {field}: {first['msg']}.", 422)


async def _http_error(request: Request, exc: HTTPException):
    path = request.url.path
    if path != "/api" and not path.startswith("/api/"):
        return await http_exception_handler(request, exc)
    if exc.status_code == 404:
        return _error("not_found", "Not found.", 404)
    code = "invalid_request" if exc.status_code < 500 else "internal_error"
    return _error(code, str(exc.detail), exc.status_code)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s", request.url.path, exc_info=exc)
    return _error("internal_error", "Something went wrong on the server.", 500)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _service_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)

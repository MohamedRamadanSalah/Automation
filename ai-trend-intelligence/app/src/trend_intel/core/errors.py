"""Domain exceptions and FastAPI exception handlers."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class TrendIntelError(Exception):
    """Base domain error."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(TrendIntelError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ConflictError(TrendIntelError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class ValidationError(TrendIntelError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class AgentError(TrendIntelError):
    """Agent call failed after retries."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "agent_error"


class SourceError(TrendIntelError):
    """An external discovery source failed."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "source_error"


class RunStateError(TrendIntelError):
    """Invalid run state transition."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "invalid_run_state"


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(TrendIntelError)
    async def _domain_handler(request: Request, exc: TrendIntelError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def _generic_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "An unexpected error occurred."},
        )

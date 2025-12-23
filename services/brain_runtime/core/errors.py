"""Application error types and handling."""

from enum import Enum
from typing import Optional
from dataclasses import dataclass
from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode(Enum):
    """Standard error codes for the application."""

    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    INVALID_MODEL = "INVALID_MODEL"
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors (5xx)
    PROVIDER_ERROR = "PROVIDER_ERROR"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class AppError(Exception):
    """Application error with code and details."""

    code: ErrorCode
    message: str
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert error to dictionary format."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }

    @property
    def status_code(self) -> int:
        """Map error code to HTTP status."""
        mapping = {
            ErrorCode.VALIDATION_ERROR: 400,
            ErrorCode.SESSION_NOT_FOUND: 404,
            ErrorCode.TOOL_NOT_FOUND: 404,
            ErrorCode.INVALID_MODEL: 400,
            ErrorCode.RATE_LIMITED: 429,
            ErrorCode.PROVIDER_ERROR: 502,
            ErrorCode.TOOL_EXECUTION_ERROR: 500,
            ErrorCode.DATABASE_ERROR: 500,
            ErrorCode.INTERNAL_ERROR: 500,
        }
        return mapping.get(self.code, 500)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """FastAPI exception handler for AppError."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


class ToolError(Exception):
    """Error during tool execution.

    This is a more specific error type for tool-related failures,
    providing better context than generic ValueError.
    """

    pass

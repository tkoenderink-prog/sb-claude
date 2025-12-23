"""Unit tests for error handling system.

Run with: cd services/brain_runtime && uv run pytest ../../tests/unit/test_error_handling.py -v
"""

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

import sys
from pathlib import Path

# Add services/brain_runtime to path
brain_runtime_path = Path(__file__).parent.parent.parent / "services" / "brain_runtime"
sys.path.insert(0, str(brain_runtime_path))

from core.errors import AppError, ErrorCode, ToolError, app_error_handler


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_codes_exist(self):
        """Verify all error codes are defined."""
        assert ErrorCode.VALIDATION_ERROR
        assert ErrorCode.SESSION_NOT_FOUND
        assert ErrorCode.TOOL_NOT_FOUND
        assert ErrorCode.INVALID_MODEL
        assert ErrorCode.RATE_LIMITED
        assert ErrorCode.PROVIDER_ERROR
        assert ErrorCode.TOOL_EXECUTION_ERROR
        assert ErrorCode.DATABASE_ERROR
        assert ErrorCode.INTERNAL_ERROR


class TestAppError:
    """Test AppError exception class."""

    def test_app_error_creation(self):
        """Test creating an AppError."""
        error = AppError(
            code=ErrorCode.TOOL_NOT_FOUND,
            message="Tool 'test_tool' not found",
            details={"tool_name": "test_tool"},
        )
        assert error.code == ErrorCode.TOOL_NOT_FOUND
        assert error.message == "Tool 'test_tool' not found"
        assert error.details == {"tool_name": "test_tool"}

    def test_app_error_to_dict(self):
        """Test converting AppError to dict."""
        error = AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
            details={"field": "user_id"},
        )
        error_dict = error.to_dict()
        assert error_dict == {
            "code": "VALIDATION_ERROR",
            "message": "Invalid input",
            "details": {"field": "user_id"},
        }

    def test_status_code_mapping_4xx(self):
        """Test HTTP status code mapping for client errors."""
        assert AppError(ErrorCode.VALIDATION_ERROR, "test").status_code == 400
        assert AppError(ErrorCode.SESSION_NOT_FOUND, "test").status_code == 404
        assert AppError(ErrorCode.TOOL_NOT_FOUND, "test").status_code == 404
        assert AppError(ErrorCode.INVALID_MODEL, "test").status_code == 400
        assert AppError(ErrorCode.RATE_LIMITED, "test").status_code == 429

    def test_status_code_mapping_5xx(self):
        """Test HTTP status code mapping for server errors."""
        assert AppError(ErrorCode.PROVIDER_ERROR, "test").status_code == 502
        assert AppError(ErrorCode.TOOL_EXECUTION_ERROR, "test").status_code == 500
        assert AppError(ErrorCode.DATABASE_ERROR, "test").status_code == 500
        assert AppError(ErrorCode.INTERNAL_ERROR, "test").status_code == 500


class TestAppErrorHandler:
    """Test FastAPI error handler."""

    @pytest.mark.asyncio
    async def test_error_handler_response(self):
        """Test that error handler returns proper JSON response."""
        # Create a mock request
        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "query_string": b"",
                "headers": [],
            }
        )

        error = AppError(
            code=ErrorCode.TOOL_NOT_FOUND,
            message="Tool not found",
            details={"tool_name": "missing_tool"},
        )

        response = await app_error_handler(request, error)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

        # Parse response body
        import json

        body = json.loads(response.body.decode())
        assert body["code"] == "TOOL_NOT_FOUND"
        assert body["message"] == "Tool not found"
        assert body["details"]["tool_name"] == "missing_tool"


class TestToolError:
    """Test ToolError exception."""

    def test_tool_error_creation(self):
        """Test creating a ToolError."""
        error = ToolError("Tool execution failed")
        assert str(error) == "Tool execution failed"

    def test_tool_error_is_exception(self):
        """Test that ToolError is an Exception."""
        error = ToolError("test")
        assert isinstance(error, Exception)

    def test_tool_error_can_be_raised(self):
        """Test that ToolError can be raised and caught."""
        with pytest.raises(ToolError) as exc_info:
            raise ToolError("Test error")
        assert str(exc_info.value) == "Test error"


class TestErrorIntegration:
    """Integration tests for error handling."""

    def test_tool_error_import(self):
        """Test that ToolError can be imported from core.tools."""
        from core.tools import ToolError as ImportedToolError

        assert ImportedToolError is ToolError

#!/usr/bin/env python
"""Verification script for error handling implementation.

Run with: uv run python verify_errors.py
"""

from core.errors import AppError, ErrorCode, ToolError, app_error_handler
from core.tools import ToolError as ToolErrorFromTools, ToolRegistry
from fastapi import Request


def test_error_codes():
    """Test that all error codes exist."""
    print("Testing ErrorCode enum...")
    codes = [
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.SESSION_NOT_FOUND,
        ErrorCode.TOOL_NOT_FOUND,
        ErrorCode.INVALID_MODEL,
        ErrorCode.RATE_LIMITED,
        ErrorCode.PROVIDER_ERROR,
        ErrorCode.TOOL_EXECUTION_ERROR,
        ErrorCode.DATABASE_ERROR,
        ErrorCode.INTERNAL_ERROR,
    ]
    print(f"  ✓ All {len(codes)} error codes defined")


def test_app_error():
    """Test AppError functionality."""
    print("Testing AppError...")

    # Test creation
    error = AppError(
        code=ErrorCode.TOOL_NOT_FOUND,
        message="Tool 'test_tool' not found",
        details={"tool_name": "test_tool"},
    )
    assert error.code == ErrorCode.TOOL_NOT_FOUND
    print("  ✓ AppError creation works")

    # Test to_dict
    error_dict = error.to_dict()
    assert error_dict["code"] == "TOOL_NOT_FOUND"
    assert error_dict["message"] == "Tool 'test_tool' not found"
    print("  ✓ to_dict() works")

    # Test status code mapping
    assert AppError(ErrorCode.VALIDATION_ERROR, "test").status_code == 400
    assert AppError(ErrorCode.TOOL_NOT_FOUND, "test").status_code == 404
    assert AppError(ErrorCode.RATE_LIMITED, "test").status_code == 429
    assert AppError(ErrorCode.PROVIDER_ERROR, "test").status_code == 502
    assert AppError(ErrorCode.INTERNAL_ERROR, "test").status_code == 500
    print("  ✓ Status code mapping works")


def test_tool_error():
    """Test ToolError functionality."""
    print("Testing ToolError...")

    # Test creation
    error = ToolError("Test error")
    assert str(error) == "Test error"
    print("  ✓ ToolError creation works")

    # Test that it's an Exception
    assert isinstance(error, Exception)
    print("  ✓ ToolError is an Exception")

    # Test it can be raised
    try:
        raise ToolError("Test exception")
    except ToolError as e:
        assert str(e) == "Test exception"
    print("  ✓ ToolError can be raised and caught")


def test_tool_error_import():
    """Test that ToolError can be imported from core.tools."""
    print("Testing ToolError import from core.tools...")

    assert ToolErrorFromTools is ToolError
    print("  ✓ ToolError exported from core.tools")


async def test_error_handler():
    """Test the FastAPI error handler."""
    print("Testing error handler...")

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
    assert response.status_code == 404
    print("  ✓ Error handler returns correct status code")

    # Parse response body
    import json

    body = json.loads(response.body.decode())
    assert body["code"] == "TOOL_NOT_FOUND"
    assert body["message"] == "Tool not found"
    print("  ✓ Error handler returns correct JSON body")


def test_tool_registry_errors():
    """Test that ToolRegistry properly raises ToolError."""
    print("Testing ToolRegistry error handling...")

    registry = ToolRegistry.get_instance()

    # Test unknown provider
    try:
        registry.get_tools_for_provider("unknown_provider")
        assert False, "Should have raised ToolError"
    except ToolError as e:
        assert "Unknown provider" in str(e)
    print("  ✓ ToolRegistry raises ToolError for unknown provider")

    # Test tool not found
    try:
        import asyncio

        asyncio.run(registry.execute("nonexistent_tool", {}))
        assert False, "Should have raised ToolError"
    except ToolError as e:
        assert "Tool not found" in str(e)
    print("  ✓ ToolRegistry raises ToolError for missing tool")


def test_app_integration():
    """Test that error handler is registered in the app."""
    print("Testing FastAPI app integration...")

    from main import app

    assert AppError in app.exception_handlers
    print("  ✓ AppError handler registered in FastAPI app")

    handler = app.exception_handlers[AppError]
    assert handler == app_error_handler
    print("  ✓ Correct handler function registered")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Error Handling Verification")
    print("=" * 60)
    print()

    test_error_codes()
    test_app_error()
    test_tool_error()
    test_tool_error_import()

    import asyncio

    asyncio.run(test_error_handler())

    test_tool_registry_errors()
    test_app_integration()

    print()
    print("=" * 60)
    print("✅ All verification tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

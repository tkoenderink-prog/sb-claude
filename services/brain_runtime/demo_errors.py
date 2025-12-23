#!/usr/bin/env python
"""Demo script showing error handling in action.

Run with: uv run python demo_errors.py
"""

from core.errors import AppError, ErrorCode, ToolError
from core.tools import ToolRegistry
import asyncio


async def demo_app_error():
    """Demonstrate AppError usage."""
    print("\n" + "=" * 60)
    print("DEMO 1: AppError with automatic status code mapping")
    print("=" * 60)

    error = AppError(
        code=ErrorCode.SESSION_NOT_FOUND,
        message="Chat session 'abc123' not found",
        details={"session_id": "abc123", "user_id": "user_456"},
    )

    print(f"\nError: {error}")
    print(f"Status Code: {error.status_code}")
    print(f"JSON Response:\n{error.to_dict()}")


async def demo_tool_error():
    """Demonstrate ToolError in tool registry."""
    print("\n" + "=" * 60)
    print("DEMO 2: ToolError when tool not found")
    print("=" * 60)

    registry = ToolRegistry.get_instance()

    try:
        # Try to execute a non-existent tool
        await registry.execute("nonexistent_tool", {"arg": "value"})
    except ToolError as e:
        print(f"\n✓ Caught ToolError: {e}")
        print(f"  Type: {type(e).__name__}")


async def demo_provider_error():
    """Demonstrate provider error handling."""
    print("\n" + "=" * 60)
    print("DEMO 3: Provider error (e.g., API timeout)")
    print("=" * 60)

    error = AppError(
        code=ErrorCode.PROVIDER_ERROR,
        message="Claude API request timed out",
        details={
            "provider": "anthropic",
            "model": "claude-opus-4-5",
            "timeout": 30,
            "retry_count": 3,
        },
    )

    print(f"\nError: {error}")
    print(f"Status Code: {error.status_code} (Bad Gateway)")
    print(f"Details: {error.details}")


async def demo_validation_error():
    """Demonstrate validation error."""
    print("\n" + "=" * 60)
    print("DEMO 4: Validation error with field details")
    print("=" * 60)

    error = AppError(
        code=ErrorCode.VALIDATION_ERROR,
        message="Invalid model ID specified",
        details={
            "field": "model_id",
            "provided": "gpt-5",
            "allowed": [
                "claude-opus-4-5",
                "claude-sonnet-4-5",
                "gpt-4o",
                "gpt-4-turbo",
            ],
        },
    )

    print(f"\nError: {error}")
    print(f"Status Code: {error.status_code}")
    print("Would return to client:")
    import json

    print(json.dumps(error.to_dict(), indent=2))


async def demo_tool_execution_error():
    """Demonstrate tool execution error with chaining."""
    print("\n" + "=" * 60)
    print("DEMO 5: Tool execution error with exception chaining")
    print("=" * 60)

    try:
        # Simulate a tool that fails
        raise ValueError("Database connection lost")
    except ValueError as e:
        # Wrap in ToolError with proper chaining
        tool_error = ToolError(f"Tool 'get_calendar_events' failed: {e}")
        tool_error.__cause__ = e

        print(f"\n✓ Original error: {e}")
        print(f"✓ Wrapped in ToolError: {tool_error}")
        print(f"✓ Cause preserved: {tool_error.__cause__}")


async def demo_error_comparison():
    """Compare different error types and status codes."""
    print("\n" + "=" * 60)
    print("DEMO 6: Error code to HTTP status mapping")
    print("=" * 60)

    errors = [
        (ErrorCode.VALIDATION_ERROR, "Invalid input"),
        (ErrorCode.SESSION_NOT_FOUND, "Session not found"),
        (ErrorCode.TOOL_NOT_FOUND, "Tool not found"),
        (ErrorCode.RATE_LIMITED, "Too many requests"),
        (ErrorCode.PROVIDER_ERROR, "Provider API failed"),
        (ErrorCode.TOOL_EXECUTION_ERROR, "Tool crashed"),
        (ErrorCode.DATABASE_ERROR, "DB connection failed"),
        (ErrorCode.INTERNAL_ERROR, "Unexpected error"),
    ]

    print("\n{:<25} | {:<15} | {}".format("Error Code", "HTTP Status", "Message"))
    print("-" * 70)
    for code, message in errors:
        error = AppError(code=code, message=message)
        print(
            "{:<25} | {:<15} | {}".format(code.value, error.status_code, message)
        )


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("ERROR HANDLING SYSTEM DEMONSTRATION")
    print("=" * 60)

    await demo_app_error()
    await demo_tool_error()
    await demo_provider_error()
    await demo_validation_error()
    await demo_tool_execution_error()
    await demo_error_comparison()

    print("\n" + "=" * 60)
    print("✅ All demos completed successfully!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("  1. AppError automatically maps error codes to HTTP status")
    print("  2. ToolError provides specific context for tool failures")
    print("  3. Errors serialize cleanly to JSON for API responses")
    print("  4. Exception chaining preserves original error context")
    print("  5. All errors are caught and handled by FastAPI")
    print()


if __name__ == "__main__":
    asyncio.run(main())

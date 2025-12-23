# Error Handling System

This module provides a standardized error handling system for the Brain Runtime service.

## Overview

The error handling system consists of three main components:

1. **ErrorCode** - Enum defining all application error codes
2. **AppError** - Exception class with automatic HTTP status code mapping
3. **ToolError** - Specialized exception for tool execution failures

## Error Codes

### Client Errors (4xx)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `INVALID_MODEL` | 400 | Invalid model ID specified |
| `SESSION_NOT_FOUND` | 404 | Chat session not found |
| `TOOL_NOT_FOUND` | 404 | Tool not found in registry |
| `RATE_LIMITED` | 429 | Too many requests |

### Server Errors (5xx)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PROVIDER_ERROR` | 502 | LLM provider API error |
| `TOOL_EXECUTION_ERROR` | 500 | Tool execution failed |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `INTERNAL_ERROR` | 500 | Internal server error |

## Usage

### Raising AppError

```python
from core.errors import AppError, ErrorCode

# Simple error
raise AppError(
    code=ErrorCode.SESSION_NOT_FOUND,
    message="Session 'abc123' not found"
)

# Error with details
raise AppError(
    code=ErrorCode.VALIDATION_ERROR,
    message="Invalid input parameters",
    details={
        "field": "model_id",
        "value": "invalid-model",
        "allowed": ["claude-opus-4-5", "claude-sonnet-4-5"]
    }
)
```

### Using ToolError

For tool-specific errors, use `ToolError`:

```python
from core.errors import ToolError

# Raise during tool execution
async def execute_tool(name: str, args: dict):
    if name not in registry:
        raise ToolError(f"Tool '{name}' not found")

    try:
        result = await tool.execute(**args)
        return result
    except Exception as e:
        raise ToolError(f"Tool execution failed: {e}") from e
```

### FastAPI Integration

The error handler is automatically registered in `main.py`:

```python
from core.errors import AppError, app_error_handler

app.add_exception_handler(AppError, app_error_handler)
```

When an `AppError` is raised, it's automatically converted to a JSON response:

```json
{
  "code": "SESSION_NOT_FOUND",
  "message": "Session 'abc123' not found",
  "details": null
}
```

### Tool Registry Integration

The `ToolRegistry` uses `ToolError` for all tool-related failures:

```python
from core.tools import ToolRegistry, ToolError

registry = ToolRegistry.get_instance()

try:
    result = await registry.execute("get_events", {})
except ToolError as e:
    # Handle tool-specific error
    logger.error(f"Tool failed: {e}")
```

## Error Response Format

All `AppError` exceptions are converted to JSON responses with this structure:

```typescript
{
  code: string;        // Error code (e.g., "TOOL_NOT_FOUND")
  message: string;     // Human-readable error message
  details?: object;    // Optional additional context
}
```

## Adding New Error Codes

1. Add the error code to `ErrorCode` enum:

```python
class ErrorCode(Enum):
    # ... existing codes ...
    NEW_ERROR_CODE = "NEW_ERROR_CODE"
```

2. Add HTTP status mapping in `AppError.status_code`:

```python
@property
def status_code(self) -> int:
    mapping = {
        # ... existing mappings ...
        ErrorCode.NEW_ERROR_CODE: 403,  # or appropriate status
    }
    return mapping.get(self.code, 500)
```

## Best Practices

1. **Use specific error codes**: Choose the most specific error code for the situation
2. **Provide details**: Include helpful context in the `details` field
3. **Don't expose internals**: Sanitize error messages for production
4. **Chain exceptions**: Use `from e` to preserve the original exception chain
5. **Log before raising**: Log errors with full stack traces before raising

## Example: API Route with Error Handling

```python
from fastapi import APIRouter
from core.errors import AppError, ErrorCode

router = APIRouter()

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = await db.get_session(session_id)

    if not session:
        raise AppError(
            code=ErrorCode.SESSION_NOT_FOUND,
            message=f"Session '{session_id}' not found",
            details={"session_id": session_id}
        )

    return session
```

The error handler will automatically convert this to:

```
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "code": "SESSION_NOT_FOUND",
  "message": "Session 'abc123' not found",
  "details": {
    "session_id": "abc123"
  }
}
```

## Testing

Run the verification script to test all error handling:

```bash
cd services/brain_runtime
uv run python verify_errors.py
```

## See Also

- `core/errors.py` - Error definitions and handlers
- `core/tools/registry.py` - Tool registry with ToolError usage
- `main.py` - FastAPI app with error handler registration

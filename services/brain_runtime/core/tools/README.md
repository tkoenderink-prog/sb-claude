# Tool Registry System

Central registry for all chat and agent mode tools. This system wraps existing API endpoints to make them available to LLMs via function calling.

## Architecture

```
core/tools/
├── __init__.py           # Exports and register_all_tools()
├── registry.py           # ToolRegistry singleton + @tool decorator
├── calendar_tools.py     # Calendar tools (4 tools)
├── tasks_tools.py        # Tasks tools (5 tools)
├── vault_tools.py        # Vault/RAG tools (5 tools)
└── skills_tools.py       # Skills tools (4 tools)
```

## Usage

### 1. Register All Tools (on startup)

```python
from core.tools import register_all_tools, ToolRegistry

# Register all tools
register_all_tools()

# Get registry instance
registry = ToolRegistry.get_instance()
```

### 2. Get Tools for a Provider

```python
# For Anthropic Claude
anthropic_tools = registry.get_tools_for_provider("anthropic")
# Returns list of dicts in Anthropic format

# For OpenAI GPT
openai_tools = registry.get_tools_for_provider("openai")
# Returns list of dicts in OpenAI function format
```

### 3. Execute a Tool

```python
# Execute by name
result = await registry.execute("get_today_events", {})

# With arguments
result = await registry.execute("semantic_search", {
    "query": "mental models",
    "limit": 10
})
```

## Available Tools (18 total)

### Calendar Tools (4)
- `get_today_events()` - Today's events from both calendars
- `get_week_events()` - Next 7 days events
- `get_events_in_range(start, end)` - Custom date range
- `search_events(query, limit)` - Search by title/description

### Tasks Tools (5)
- `get_overdue_tasks()` - Overdue tasks (oldest first)
- `get_today_tasks()` - Tasks due today
- `get_week_tasks()` - Tasks due in next 7 days
- `query_tasks(status, priority, tag, project, due_before, due_after, limit)` - Flexible filtering
- `get_tasks_by_project()` - Grouped by project folder

### Vault/RAG Tools (5)
- `semantic_search(query, limit, min_score, para_category, tags, path_contains)` - E5-multilingual embeddings
- `text_search(query, limit, path_contains)` - Ripgrep exact matching
- `hybrid_search(query, limit, min_score, path_contains)` - Semantic + text fallback
- `read_vault_file(path)` - Read full file content
- `list_vault_directory(path)` - List directory contents

### Skills Tools (4)
- `list_skills(source)` - List all skills (filter by source)
- `get_skill(skill_id)` - Get full skill details
- `search_skills(query)` - Search by name/description
- `get_skills_stats()` - Statistics about skills

## Adding New Tools

### Method 1: Using @tool Decorator

```python
from core.tools import tool

@tool(
    name="my_tool",
    description="What this tool does (for LLM)",
    parameters={
        "type": "object",
        "properties": {
            "arg1": {
                "type": "string",
                "description": "First argument"
            }
        },
        "required": ["arg1"]
    }
)
async def my_tool(arg1: str):
    """Implementation."""
    # Call existing API or implement logic
    return {"result": "success"}
```

### Method 2: Manual Registration

```python
from core.tools import Tool, ToolRegistry

async def my_function(arg1: str):
    return {"result": arg1}

tool = Tool(
    name="my_tool",
    description="What it does",
    parameters={...},
    execute_fn=my_function
)

registry = ToolRegistry.get_instance()
registry.register(tool)
```

## Provider Format Examples

### Anthropic Format
```json
{
  "name": "get_today_events",
  "description": "Get calendar events for today...",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

### OpenAI Format
```json
{
  "type": "function",
  "function": {
    "name": "get_today_events",
    "description": "Get calendar events for today...",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  }
}
```

## Internal Implementation Notes

### Tool Functions Call APIs Directly
Tools don't make HTTP requests - they import and call API functions directly:

```python
# calendar_tools.py
async def get_today_events():
    from api.calendar import get_today_events as api_get_today_events
    result = await api_get_today_events()
    return {"events": [e.model_dump() for e in result.events], ...}
```

This ensures:
1. No HTTP overhead
2. Type safety via Pydantic models
3. Direct access to all API functionality
4. Consistent error handling

### Why Wrap APIs as Tools?

1. **Provider Compatibility**: Different LLM providers (Anthropic, OpenAI) have different tool/function formats
2. **Abstraction**: Tools can combine multiple API calls or add LLM-specific formatting
3. **Registry Pattern**: Single source of truth for available capabilities
4. **Type Safety**: Pydantic models ensure correct arguments
5. **Logging**: Centralized execution logging for debugging

## Testing

```bash
# Run test script
cd services/brain_runtime
python test_tools.py
```

Expected output:
```
Testing tool registry...

Registered 18 tools:
  get_today_events
  get_week_events
  ...

All tests passed!
```

## Integration with Chat/Agent Modes

### Quick Chat (No Tools)
- Registry not used
- Direct LLM calls without function calling

### Tool-Enabled Chat
```python
registry = ToolRegistry.get_instance()
tools = registry.get_tools_for_provider("anthropic")

# Pass tools to Claude
response = anthropic.messages.create(
    model="claude-opus-4",
    tools=tools,
    messages=[...]
)

# If tool_use in response
if response.stop_reason == "tool_use":
    for block in response.content:
        if block.type == "tool_use":
            result = await registry.execute(block.name, block.input)
```

### Agent Mode (Claude SDK)
```python
# Claude Agent SDK will use tools automatically
from anthropic import Agent

agent = Agent(
    model="claude-opus-4",
    tools=registry.get_tools_for_provider("anthropic")
)

# SDK handles tool calls internally
result = await agent.run(task="Analyze my week")
```

## Error Handling

Tools return structured errors on failure:

```python
try:
    result = await registry.execute("get_today_events", {})
except ValueError as e:
    # Tool not found or execution failed
    print(f"Error: {e}")
```

Individual tools may raise HTTPException (from FastAPI), which should be caught and converted to tool error responses.

## Future Enhancements

1. **Tool Groups**: Tag tools by domain (calendar, tasks, etc.) for selective loading
2. **Permissions**: Role-based access control for sensitive tools
3. **Rate Limiting**: Per-tool rate limits for expensive operations
4. **Caching**: Cache tool results for repeated queries
5. **Processor Tools**: Add tools for running processors (calendar refresh, task parsing, etc.)
6. **Write Tools**: Propose/diff/apply tools for safe vault modifications

# LLM Provider Adapters

This module provides unified interfaces to different LLM providers (Anthropic Claude and OpenAI GPT) with support for streaming, tool calling, and consistent event formats.

## Architecture

All providers implement the `BaseProvider` abstract class, which defines:
- **Streaming chat completion** with SSE-compatible events
- **Tool/function calling** support
- **Model metadata** (context windows, capabilities)
- **Unified event format** for consistent handling

## Supported Providers

### Anthropic Claude
- **Models:** Claude Opus 4, Claude Sonnet 4, Claude 3.5 Haiku
- **Capabilities:** Tools, vision, streaming
- **Context:** Up to 200K tokens
- **Default:** claude-sonnet-4-20250514

### OpenAI GPT
- **Models:** GPT-4 Turbo, GPT-4o, GPT-4o Mini
- **Capabilities:** Tools, vision (Turbo/4o), streaming
- **Context:** Up to 128K tokens
- **Default:** gpt-4o

## Usage

### Basic Chat (No Tools)

```python
from core.providers import get_provider, ProviderType
from core.config import get_settings

settings = get_settings()

# Initialize provider
provider = get_provider(
    ProviderType.ANTHROPIC,
    api_key=settings.anthropic_api_key
)

# Send message and stream response
messages = [
    {"role": "user", "content": "What is the capital of France?"}
]

async for event in provider.chat(messages=messages, stream=True):
    if event["type"] == "content":
        print(event["data"]["text"], end="", flush=True)
    elif event["type"] == "done":
        print("\n[Complete]")
```

### Chat with Tools

```python
# Define tools
tools = [{
    "name": "get_weather",
    "description": "Get current weather for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name"
            }
        },
        "required": ["location"]
    }
}]

# Send message with tools
messages = [
    {"role": "user", "content": "What's the weather in Paris?"}
]

async for event in provider.chat(messages=messages, tools=tools, stream=True):
    if event["type"] == "content":
        print(f"Assistant: {event['data']['text']}")

    elif event["type"] == "tool_call_start":
        print(f"Tool call started: {event['data']['name']}")

    elif event["type"] == "tool_call":
        tool_name = event["data"]["name"]
        tool_input = event["data"]["input"]
        print(f"Calling {tool_name} with {tool_input}")

        # Execute tool and send result back
        # (See tool execution pattern below)
```

### Multi-turn Conversation with Tools

```python
messages = []

# Turn 1: User asks question
messages.append({
    "role": "user",
    "content": "What events do I have today?"
})

# Turn 2: Assistant calls tool
tool_call_id = None
async for event in provider.chat(messages=messages, tools=tools):
    if event["type"] == "tool_call":
        tool_call_id = event["data"]["id"]
        tool_name = event["data"]["name"]
        tool_input = event["data"]["input"]

        # Execute tool (e.g., call calendar API)
        result = await execute_tool(tool_name, tool_input)

        # Add assistant message with tool call
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_input)
                }
            }]
        })

        # Add tool result
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(result)
        })

# Turn 3: Assistant synthesizes response
async for event in provider.chat(messages=messages, tools=tools):
    if event["type"] == "content":
        print(event["data"]["text"], end="")
```

## Event Types

All providers emit consistent event types:

### message_start
Emitted when message generation begins.
```python
{
    "type": "message_start",
    "data": {
        "model": "claude-sonnet-4-20250514",
        "role": "assistant"
    }
}
```

### content
Text content delta (streaming) or full text (non-streaming).
```python
{
    "type": "content",
    "data": {
        "text": "The capital of France",
        "index": 0
    }
}
```

### tool_call_start
Tool call begins (streaming only).
```python
{
    "type": "tool_call_start",
    "data": {
        "id": "toolu_123",
        "name": "get_weather",
        "index": 0
    }
}
```

### tool_call_delta
Partial JSON for tool arguments (streaming only).
```python
{
    "type": "tool_call_delta",
    "data": {
        "partial_json": '{"location":',
        "index": 0
    }
}
```

### tool_call
Complete tool call with parsed arguments.
```python
{
    "type": "tool_call",
    "data": {
        "id": "toolu_123",
        "name": "get_weather",
        "input": {"location": "Paris"},
        "index": 0
    }
}
```

### stop
Message generation stopped.
```python
{
    "type": "stop",
    "data": {
        "stop_reason": "end_turn" | "tool_use" | "max_tokens"
    }
}
```

### usage
Token usage statistics.
```python
{
    "type": "usage",
    "data": {
        "input_tokens": 150,
        "output_tokens": 42
    }
}
```

### done
Message complete.
```python
{
    "type": "done",
    "data": {
        "provider": "anthropic"
    }
}
```

### error
Error occurred.
```python
{
    "type": "error",
    "data": {
        "error": "API rate limit exceeded",
        "provider": "anthropic"
    }
}
```

## Provider-Specific Notes

### Anthropic

- Requires separating system messages from conversation
- Tool calls use `tool_use` blocks in content
- Stop reason is `end_turn` or `tool_use`
- Streaming provides token-by-token deltas

### OpenAI

- System messages are part of the messages array
- Tool calls use `function` with JSON arguments
- Stop reason is `stop`, `tool_calls`, or `length`
- Streaming provides word-by-word deltas
- No usage stats in streaming mode

## Configuration

API keys are loaded from environment via `core.config.Settings`:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
```

```python
from core.config import get_settings

settings = get_settings()
provider = get_provider(
    ProviderType.ANTHROPIC,
    api_key=settings.anthropic_api_key
)
```

## Error Handling

All providers catch exceptions and emit error events:

```python
async for event in provider.chat(messages):
    if event["type"] == "error":
        error_msg = event["data"]["error"]
        provider_name = event["data"]["provider"]
        logger.error(f"{provider_name} error: {error_msg}")
        # Handle gracefully
```

Common errors:
- Invalid API key
- Rate limit exceeded
- Context length exceeded
- Invalid tool format
- Network timeout

## Testing

Run the test script to verify provider functionality:

```bash
cd services/brain_runtime
uv run python test_providers.py
```

This validates:
- Provider imports
- Model metadata
- Tool formatting
- Initialization

For integration testing with real API calls, ensure API keys are set in environment.

## Adding New Providers

To add a new provider:

1. Create `core/providers/newprovider.py` extending `BaseProvider`
2. Implement all abstract methods:
   - `chat()` - streaming and non-streaming
   - `supports_tools()` - capability flag
   - `get_models()` - model list
   - `format_tools()` - tool schema conversion
   - `get_default_model()` - default model ID
   - `name` property - provider identifier
3. Add to `__init__.py` PROVIDER_CLASSES dict
4. Update tests and documentation

See `anthropic.py` and `openai.py` for reference implementations.

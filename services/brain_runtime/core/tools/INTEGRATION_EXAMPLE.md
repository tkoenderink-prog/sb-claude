# Tool Registry Integration Example

This document shows how the tool registry will be used in Phase 7 (Chat + Agent Mode).

## 1. Startup: Register All Tools

```python
# In main.py (FastAPI startup)
from fastapi import FastAPI
from core.tools import register_all_tools

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Register all tools on application startup."""
    register_all_tools()
    print("✅ Registered all tools")
```

## 2. Chat Endpoint: Tool-Enabled Mode

```python
# In api/chat.py
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from anthropic import Anthropic
from core.tools import ToolRegistry

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
async def chat(request: ChatRequest):
    """
    Chat endpoint with tool support.

    Modes:
    - quick: No tools, direct LLM response
    - tools: Tools available, LLM can call them
    - agent: Autonomous agent with tools
    """

    if request.mode == "quick":
        # No tools, just stream response
        return await quick_chat(request)

    elif request.mode == "tools":
        # Tools available
        return await tool_enabled_chat(request)

    elif request.mode == "agent":
        # Agent mode (Phase 7 Step 7)
        return await agent_mode(request)


async def tool_enabled_chat(request: ChatRequest):
    """Chat with tools available."""

    # Get tools from registry
    registry = ToolRegistry.get_instance()
    tools = registry.get_tools_for_provider("anthropic")

    # Create Anthropic client
    client = Anthropic(api_key=settings.anthropic_api_key)

    # Build messages
    messages = [{"role": "user", "content": request.message}]

    # Stream response with tool handling
    async def event_generator():
        # Initial LLM call
        response = client.messages.create(
            model=request.model or "claude-opus-4",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # Stream assistant response
        for block in response.content:
            if block.type == "text":
                yield {
                    "event": "assistant",
                    "data": json.dumps({"text": block.text})
                }

            elif block.type == "tool_use":
                # Stream tool call
                yield {
                    "event": "tool_call",
                    "data": json.dumps({
                        "name": block.name,
                        "input": block.input
                    })
                }

                # Execute tool
                try:
                    result = await registry.execute(block.name, block.input)

                    # Stream tool result
                    yield {
                        "event": "tool_result",
                        "data": json.dumps({
                            "tool_use_id": block.id,
                            "result": result
                        })
                    }

                    # Continue conversation with tool result
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        }]
                    })

                    # Get next response
                    follow_up = client.messages.create(
                        model=request.model or "claude-opus-4",
                        max_tokens=4096,
                        tools=tools,
                        messages=messages
                    )

                    # Stream follow-up text
                    for follow_block in follow_up.content:
                        if follow_block.type == "text":
                            yield {
                                "event": "assistant",
                                "data": json.dumps({"text": follow_block.text})
                            }

                except Exception as e:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }

        # Stream complete
        yield {
            "event": "done",
            "data": json.dumps({"status": "completed"})
        }

    return EventSourceResponse(event_generator())
```

## 3. Example User Flows

### Flow 1: Simple Calendar Query

**User:** "What's on my calendar today?"

**System:**
1. LLM receives message + tools list
2. LLM chooses `get_today_events` tool
3. Registry executes tool → calls `api.calendar.get_today_events()`
4. Tool returns events
5. LLM synthesizes natural language response

**SSE Stream:**
```json
{"event": "tool_call", "data": {"name": "get_today_events", "input": {}}}
{"event": "tool_result", "data": {"result": {"events": [...], "count": 3}}}
{"event": "assistant", "data": {"text": "You have 3 events today:\n\n1. Team standup at 9:00 AM..."}}
{"event": "done", "data": {"status": "completed"}}
```

### Flow 2: Multi-Tool Query

**User:** "What's on my schedule today and what tasks are overdue?"

**System:**
1. LLM receives message
2. LLM calls TWO tools in parallel:
   - `get_today_events`
   - `get_overdue_tasks`
3. Registry executes both tools
4. LLM synthesizes combined response

**SSE Stream:**
```json
{"event": "tool_call", "data": {"name": "get_today_events", "input": {}}}
{"event": "tool_call", "data": {"name": "get_overdue_tasks", "input": {}}}
{"event": "tool_result", "data": {"tool_use_id": "1", "result": {"events": [...]}}}
{"event": "tool_result", "data": {"tool_use_id": "2", "result": {"tasks": [...]}}}
{"event": "assistant", "data": {"text": "Here's your day overview:\n\n**Calendar (3 events)**\n..."}}
{"event": "done", "data": {"status": "completed"}}
```

### Flow 3: Search + Read Flow

**User:** "Find my notes about mental models and summarize the key concepts"

**System:**
1. LLM calls `semantic_search` with query "mental models"
2. Tool returns top 10 chunks with file paths
3. LLM analyzes results, decides to read full files
4. LLM calls `read_vault_file` for 2-3 most relevant files
5. LLM synthesizes summary from full content

**SSE Stream:**
```json
{"event": "tool_call", "data": {"name": "semantic_search", "input": {"query": "mental models", "limit": 10}}}
{"event": "tool_result", "data": {"result": {"count": 10, "results": [...]}}}
{"event": "tool_call", "data": {"name": "read_vault_file", "input": {"path": "Resources/Mental-Models/Framework.md"}}}
{"event": "tool_result", "data": {"result": {"content": "# Mental Models\n\n..."}}}
{"event": "assistant", "data": {"text": "Based on your notes, here are the key mental model concepts:\n\n1. **First Principles Thinking**..."}}
{"event": "done", "data": {"status": "completed"}}
```

## 4. OpenAI Integration (GPT-4)

```python
# For OpenAI (same registry, different format)
from openai import OpenAI

async def openai_tool_chat(request: ChatRequest):
    """Chat using OpenAI GPT with tools."""

    # Get tools in OpenAI format
    registry = ToolRegistry.get_instance()
    tools = registry.get_tools_for_provider("openai")

    # Create OpenAI client
    client = OpenAI(api_key=settings.openai_api_key)

    # Call with tools
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": request.message}],
        tools=tools,
        tool_choice="auto"
    )

    # Handle tool calls
    if response.choices[0].finish_reason == "tool_calls":
        for tool_call in response.choices[0].message.tool_calls:
            # Execute via registry
            result = await registry.execute(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            # ... continue conversation
```

## 5. Agent Mode (Autonomous)

```python
# Using Claude Agent SDK (Phase 7 Step 7)
from anthropic import Agent
from core.tools import ToolRegistry

async def agent_mode(request: ChatRequest):
    """Autonomous agent with tools."""

    # Get tools
    registry = ToolRegistry.get_instance()
    tools = registry.get_tools_for_provider("anthropic")

    # Create agent
    agent = Agent(
        model="claude-opus-4",
        tools=tools,
        max_iterations=10
    )

    # Run task
    async def event_generator():
        async for event in agent.run_stream(task=request.message):
            if event.type == "thinking":
                yield {"event": "thinking", "data": json.dumps({"text": event.text})}

            elif event.type == "tool_call":
                yield {"event": "tool_call", "data": json.dumps({
                    "name": event.tool_name,
                    "input": event.tool_input
                })}

            elif event.type == "tool_result":
                yield {"event": "tool_result", "data": json.dumps({
                    "result": event.result
                })}

            elif event.type == "response":
                yield {"event": "assistant", "data": json.dumps({"text": event.text})}

            elif event.type == "artifact":
                yield {"event": "artifact", "data": json.dumps({
                    "type": event.artifact_type,
                    "content": event.content
                })}

        yield {"event": "done", "data": json.dumps({"status": "completed"})}

    return EventSourceResponse(event_generator())
```

## 6. Frontend Integration

```typescript
// apps/web/src/lib/chat.ts
export async function sendChatMessage(
  message: string,
  mode: 'quick' | 'tools' | 'agent',
  onEvent: (event: SSEEvent) => void
) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, mode })
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        onEvent(data);
      }
    }
  }
}

// Usage in React component
const [messages, setMessages] = useState([]);

sendChatMessage(userInput, 'tools', (event) => {
  if (event.event === 'tool_call') {
    // Show tool call in UI
    setMessages(prev => [...prev, {
      type: 'tool_call',
      name: event.data.name,
      input: event.data.input
    }]);
  }
  else if (event.event === 'tool_result') {
    // Show tool result
    setMessages(prev => [...prev, {
      type: 'tool_result',
      result: event.data.result
    }]);
  }
  else if (event.event === 'assistant') {
    // Show assistant response
    setMessages(prev => [...prev, {
      type: 'assistant',
      text: event.data.text
    }]);
  }
});
```

## 7. Testing Tool Calls

```python
# Test individual tool
import asyncio
from core.tools import ToolRegistry

async def test_tool():
    registry = ToolRegistry.get_instance()

    # Test calendar tool
    result = await registry.execute("get_today_events", {})
    print(f"Today's events: {result['count']}")

    # Test semantic search
    result = await registry.execute("semantic_search", {
        "query": "mental models",
        "limit": 5
    })
    print(f"Found {result['count']} results")

asyncio.run(test_tool())
```

## Benefits of This Architecture

1. **Single Source of Truth**: All tools in one registry
2. **Provider Agnostic**: Works with Anthropic and OpenAI
3. **Type Safe**: Pydantic models ensure correctness
4. **Testable**: Easy to test tools independently
5. **Extensible**: Add new tools with @tool decorator
6. **Performance**: Direct API calls, no HTTP overhead
7. **Debuggable**: Centralized logging and error handling

## Next Steps

1. ✅ Tool registry (COMPLETE - this document)
2. 🔲 Provider adapters (`core/providers/anthropic_adapter.py`, `openai_adapter.py`)
3. 🔲 Chat endpoint (`api/chat.py`)
4. 🔲 Agent runtime (`core/agent_runtime.py`)
5. 🔲 Frontend chat UI (`apps/web/src/app/chat/`)
6. 🔲 E2E tests for chat flows

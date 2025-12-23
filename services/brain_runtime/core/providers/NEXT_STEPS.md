# Next Steps: Integrating Providers into Phase 7

The provider adapters are complete. Here's how to integrate them into the Phase 7 chat system.

## Step 1: Create Tool Registry

**Location:** `core/tools/`

Create tools that wrap existing Phase 1-6 APIs:

```python
# core/tools/__init__.py
from typing import Dict, Any, List, Callable

TOOL_REGISTRY: Dict[str, Callable] = {}

def register_tool(name: str, description: str, parameters: Dict):
    """Decorator to register a tool."""
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = {
            "function": func,
            "name": name,
            "description": description,
            "parameters": parameters
        }
        return func
    return decorator

def get_tool_definitions() -> List[Dict]:
    """Get all tool definitions for LLM."""
    return [{
        "name": tool["name"],
        "description": tool["description"],
        "parameters": tool["parameters"]
    } for tool in TOOL_REGISTRY.values()]

async def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a tool by name."""
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}")

    tool = TOOL_REGISTRY[name]
    return await tool["function"](**arguments)
```

### Example Tools to Implement

```python
# core/tools/calendar.py
from . import register_tool
from ..processors.calendar import get_combined_events

@register_tool(
    name="get_today_events",
    description="Get all calendar events for today",
    parameters={"type": "object", "properties": {}, "required": []}
)
async def get_today_events():
    """Get today's calendar events."""
    return await get_combined_events(date_range="today")

@register_tool(
    name="search_events",
    description="Search calendar events by keyword",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
)
async def search_events(query: str):
    """Search calendar events."""
    # Implementation...
    pass
```

Similar for:
- `core/tools/tasks.py` - Task queries
- `core/tools/vault.py` - Vault search and read
- `core/tools/skills.py` - Skills listing and retrieval

## Step 2: Create Chat Endpoint

**Location:** `api/chat.py`

```python
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from core.config import get_settings
from core.providers import get_provider, ProviderType
from core.tools import get_tool_definitions, execute_tool

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    provider: str = "anthropic"  # "anthropic" or "openai"
    model: Optional[str] = None
    mode: str = "quick"  # "quick", "tools", or "agent"
    session_id: Optional[str] = None
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 1.0

@router.post("")
async def chat(request: ChatRequest):
    """Send chat message and stream response."""
    settings = get_settings()

    # Get API key for provider
    if request.provider == "anthropic":
        api_key = settings.anthropic_api_key
    elif request.provider == "openai":
        api_key = settings.openai_api_key
    else:
        raise HTTPException(400, f"Invalid provider: {request.provider}")

    if not api_key:
        raise HTTPException(400, f"No API key for provider: {request.provider}")

    # Initialize provider
    provider = get_provider(request.provider, api_key)

    # Build messages (load from session if exists, else start new)
    messages = _load_session_messages(request.session_id) if request.session_id else []
    messages.append({"role": "user", "content": request.message})

    # Get tools if mode requires them
    tools = None
    if request.mode in ["tools", "agent"]:
        tools = get_tool_definitions()

    # Stream response
    async def event_generator():
        async for event in provider.chat(
            messages=messages,
            tools=tools,
            stream=True,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        ):
            # Handle tool calls
            if event["type"] == "tool_call":
                tool_name = event["data"]["name"]
                tool_input = event["data"]["input"]

                # Execute tool
                try:
                    result = await execute_tool(tool_name, tool_input)

                    # Send tool result event
                    yield f"data: {json.dumps({
                        'type': 'tool_result',
                        'data': {
                            'name': tool_name,
                            'result': result
                        }
                    })}\n\n"

                    # Add to message history for next turn
                    # (Implementation depends on provider format)

                except Exception as e:
                    yield f"data: {json.dumps({
                        'type': 'tool_error',
                        'data': {'error': str(e)}
                    })}\n\n"
            else:
                # Forward other events to client
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

def _load_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Load message history from session."""
    # TODO: Load from database
    return []
```

## Step 3: Add Session Management

**Location:** `core/chat_sessions.py`

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class ChatSession(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    provider: str
    model: str
    mode: str
    messages: List[Dict[str, Any]]

class SessionManager:
    """Manage chat sessions with message history."""

    def __init__(self):
        # TODO: Use database instead of in-memory
        self.sessions: Dict[str, ChatSession] = {}

    async def create_session(
        self,
        provider: str,
        model: str,
        mode: str
    ) -> ChatSession:
        """Create new chat session."""
        session = ChatSession(
            id=...,  # Generate UUID
            created_at=datetime.now(),
            updated_at=datetime.now(),
            provider=provider,
            model=model,
            mode=mode,
            messages=[]
        )
        self.sessions[session.id] = session
        return session

    async def add_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Add message to session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self.sessions[session_id]
        session.messages.append(message)
        session.updated_at = datetime.now()

    async def get_messages(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get all messages in session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")

        return self.sessions[session_id].messages
```

## Step 4: Frontend Integration

**Location:** `apps/web/src/app/chat/`

### Chat Page Component

```typescript
// apps/web/src/app/chat/page.tsx
'use client';

import { useState } from 'react';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { ChatInput } from '@/components/chat/ChatInput';
import { ModeSelector } from '@/components/chat/ModeSelector';
import { ProviderSelector } from '@/components/chat/ProviderSelector';

export default function ChatPage() {
  const [mode, setMode] = useState<'quick' | 'tools' | 'agent'>('tools');
  const [provider, setProvider] = useState<'anthropic' | 'openai'>('anthropic');
  const [model, setModel] = useState<string>('claude-sonnet-4-20250514');
  const [messages, setMessages] = useState<any[]>([]);

  const handleSend = async (text: string) => {
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: text }]);

    // Call API with SSE
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        provider,
        model,
        mode
      })
    });

    // Parse SSE stream
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    let assistantMessage = { role: 'assistant', content: '', toolCalls: [] };

    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const event = JSON.parse(line.slice(6));

          if (event.type === 'content') {
            assistantMessage.content += event.data.text;
            setMessages(prev => [...prev.slice(0, -1), { ...assistantMessage }]);
          }
          // Handle other event types...
        }
      }
    }
  };

  return (
    <div className="flex h-screen">
      <div className="flex-1 flex flex-col">
        {/* Header with mode/provider selectors */}
        <div className="border-b p-4 flex gap-4">
          <ModeSelector value={mode} onChange={setMode} />
          <ProviderSelector
            value={{ provider, model }}
            onChange={(p, m) => { setProvider(p); setModel(m); }}
          />
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} message={msg} />
          ))}
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} />
      </div>
    </div>
  );
}
```

## Step 5: Testing

### Backend Tests

```python
# tests/test_providers.py
import pytest
from core.providers import get_provider, ProviderType

@pytest.mark.asyncio
async def test_anthropic_chat_stream():
    provider = get_provider(ProviderType.ANTHROPIC, api_key="test")
    messages = [{"role": "user", "content": "Hi"}]

    events = []
    async for event in provider.chat(messages, stream=True):
        events.append(event)

    assert any(e["type"] == "content" for e in events)
    assert any(e["type"] == "done" for e in events)

@pytest.mark.asyncio
async def test_tool_execution():
    from core.tools import execute_tool

    result = await execute_tool("get_today_events", {})
    assert isinstance(result, list)
```

### E2E Tests

```typescript
// tests/e2e/chat.spec.ts
import { test, expect } from '@playwright/test';

test('send chat message and receive response', async ({ page }) => {
  await page.goto('http://localhost:3000/chat');

  // Type message
  await page.fill('[data-testid="chat-input"]', 'Hello');
  await page.click('[data-testid="send-button"]');

  // Wait for response
  await expect(page.locator('[data-testid="assistant-message"]')).toBeVisible();
});

test('tool call shows in UI', async ({ page }) => {
  await page.goto('http://localhost:3000/chat');

  // Select tools mode
  await page.selectOption('[data-testid="mode-selector"]', 'tools');

  // Ask question that triggers tool
  await page.fill('[data-testid="chat-input"]', "What's on my calendar today?");
  await page.click('[data-testid="send-button"]');

  // Verify tool call card appears
  await expect(page.locator('[data-testid="tool-call-card"]')).toBeVisible();
});
```

## Summary

**Completed:**
- Provider adapters (Anthropic, OpenAI)
- Streaming support with unified events
- Tool calling infrastructure
- Model metadata and capabilities

**Next to implement:**
1. Tool registry wrapping existing APIs
2. Chat endpoint with SSE streaming
3. Session management (database-backed)
4. Frontend chat UI components
5. Agent mode with Claude SDK
6. E2E tests for chat flows

**Files to create:**
- `core/tools/{__init__,calendar,tasks,vault,skills}.py`
- `api/chat.py`
- `core/chat_sessions.py`
- `apps/web/src/app/chat/page.tsx`
- `apps/web/src/components/chat/{ChatMessage,ChatInput,ModeSelector,ProviderSelector}.tsx`
- `tests/e2e/chat.spec.ts`

Providers are ready to use. Start with Step 1 (Tool Registry) next.

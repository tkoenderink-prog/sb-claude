# Tool Execution Loop Implementation

## Overview

This document describes the tool execution loop implementation for Phase 7A, which fixes the critical gap where tool calls were executed but their results were never sent back to the LLM for continuation.

## Problem Statement

**Before (Phase 7):**
- LLM would call tools
- Tools would execute successfully
- Results were emitted to the frontend via SSE
- **But conversation ended there** - results were never sent back to LLM
- Line 165-167 in old `chat.py` said: "In a full implementation, we'd continue the conversation here"

**Impact:**
- No multi-turn tool conversations
- LLM couldn't ask follow-up questions based on tool results
- Agent mode was essentially broken

## Solution Architecture

### 1. Tool Executor (`core/tools/executor.py`)

New abstraction layer for tool execution with proper error handling and result formatting.

**Key Classes:**

```python
@dataclass
class ToolCallRequest:
    """Request to execute a tool."""
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ToolCallResult:
    """Result from a tool execution."""
    tool_call_id: str
    success: bool
    content: Any
    error: Optional[str] = None

class ToolExecutor:
    """Executes tools and formats results for LLM providers."""

    async def execute(self, tool_call: ToolCallRequest) -> ToolCallResult
    async def execute_all(self, tool_calls: List[ToolCallRequest]) -> List[ToolCallResult]
    def format_for_anthropic(self, results: List[ToolCallResult]) -> List[Dict]
    def format_for_openai(self, results: List[ToolCallResult]) -> List[Dict]
```

**Provider-Specific Formatting:**

- **Anthropic:** Tool results go in a `user` message with `tool_result` content blocks
  ```python
  {
      "role": "user",
      "content": [
          {
              "type": "tool_result",
              "tool_use_id": "...",
              "content": "...",
              "is_error": False  # only if error
          }
      ]
  }
  ```

- **OpenAI:** Tool results are separate messages with `role: "tool"`
  ```python
  {
      "role": "tool",
      "tool_call_id": "...",
      "content": "..."
  }
  ```

### 2. Tool Execution Loop (`api/chat.py`)

Complete rewrite of `chat_event_generator` to implement a multi-turn conversation loop.

**Flow:**

```
1. Initialize conversation with user messages
2. LOOP (max 5 turns):
   a. Send messages to LLM
   b. Stream response, collecting:
      - Text content
      - Tool calls
   c. IF no tool calls:
      - Save assistant message
      - Send "done" event
      - BREAK
   d. IF tool calls present:
      - Execute all tools via ToolExecutor
      - Emit tool result events (for frontend)
      - Add assistant message with tool_use blocks to conversation
      - Add tool results as user message to conversation
      - CONTINUE to next turn
3. IF max turns reached:
   - Save assistant message
   - Send "done" with max_turns_reached flag
```

**Key Implementation Details:**

1. **Turn Tracking:**
   - `current_turn` counter (1 to max_turns)
   - `turn_tool_calls` - collects all tool calls in current turn
   - `turn_text` - collects text in current turn
   - `all_accumulated_*` - tracks data across all turns for database

2. **Tool Call Collection:**
   - Handles both streaming (`tool_call_start`, `tool_call_delta`) and non-streaming (`tool_call`) formats
   - Parses JSON from deltas on `content_block_stop`
   - Stores as `ToolCallRequest` objects for execution

3. **Tool Execution:**
   - After streaming completes for a turn, execute all collected tool calls
   - Use `ToolExecutor.execute_all()` for batch execution
   - Emit `tool_result` events for each result (frontend sees them)

4. **Conversation Continuation:**
   - Build assistant message with:
     - Text content (if any)
     - Tool use blocks (Anthropic format)
   - Append to `provider_messages`
   - Format tool results for provider (Anthropic vs OpenAI)
   - Append tool results to `provider_messages`
   - Loop back to step 2

5. **Exit Conditions:**
   - No tool calls in response → conversation complete
   - Max turns (5) reached → prevent infinite loops
   - Error from provider → abort

## Database Persistence

**Tracked Across All Turns:**
- `all_accumulated_text` - all text from all turns
- `all_accumulated_tool_calls` - all tool calls made
- `all_accumulated_tool_results` - all tool results received

**Saved When:**
- Conversation completes (no more tool calls)
- Max turns reached
- Via `session_service.save_message()` with all accumulated data

## Benefits

1. **Multi-Turn Tool Conversations:**
   - LLM can call a tool, see the result, and decide what to do next
   - Can call multiple tools in sequence
   - Can ask clarifying questions based on results

2. **Error Handling:**
   - Tool execution errors don't crash the conversation
   - Errors are sent back to LLM with `is_error: True`
   - LLM can handle errors gracefully (retry, ask for help, etc.)

3. **Provider Abstraction:**
   - Works with both Anthropic and OpenAI
   - Executor handles format differences
   - Easy to add new providers

4. **Safety:**
   - Max turns limit prevents infinite loops
   - Each turn is logged
   - All data persisted to database

## Testing

**Manual Test Flow:**

1. Start chat with mode="tools"
2. Ask: "What's on my calendar today?"
3. Expect:
   - Turn 1: LLM calls `get_today_events`
   - Tool executes, results returned
   - Turn 2: LLM responds with calendar summary
   - Done (no more tool calls)

4. Ask: "What tasks are overdue and what's on my calendar tomorrow?"
5. Expect:
   - Turn 1: LLM calls `get_overdue_tasks` and `get_tomorrow_events`
   - Both tools execute
   - Turn 2: LLM responds with combined answer
   - Done

**Edge Cases:**

- Tool execution error: LLM should receive error and can retry or explain
- Max turns reached: Conversation ends gracefully with warning
- Empty tool results: LLM should handle gracefully
- Mixed text + tool calls: Both should be preserved

## Files Modified

1. **`core/tools/executor.py`** (NEW)
   - ToolExecutor class
   - ToolCallRequest/Result dataclasses
   - Provider-specific formatters

2. **`core/tools/__init__.py`** (UPDATED)
   - Export ToolExecutor, ToolCallRequest, ToolCallResult

3. **`api/chat.py`** (COMPLETE REWRITE)
   - `chat_event_generator` function
   - Tool execution loop implementation
   - Multi-turn conversation handling

## Future Enhancements

1. **Configurable Max Turns:**
   - Currently hardcoded to 5
   - Could be per-request parameter

2. **Token Budget Tracking:**
   - Track cumulative tokens across turns
   - Stop if approaching context limit

3. **Tool Call Parallelization:**
   - Currently executes tools sequentially
   - Could run independent tools in parallel

4. **Retry Logic:**
   - Auto-retry failed tools with exponential backoff
   - Configurable retry policy

5. **Streaming Tool Results:**
   - For long-running tools, stream partial results
   - Would require tool protocol changes

## Migration Notes

**Breaking Changes:**
- None - API surface unchanged
- Existing frontend code works as-is
- SSE event types unchanged

**Deployment:**
- No database migrations needed
- No config changes needed
- Safe to deploy directly

**Rollback:**
- Git revert to previous commit
- No data corruption risk (append-only database operations)

"""Chat API endpoints with SSE streaming."""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.providers import get_provider, get_provider_models
from core.tools.registry import ToolRegistry
from core.tools.executor import ToolExecutor, ToolCallRequest
from core.config import get_settings
from core.session_service import SessionService
from core.skills import SkillInjector
from models.chat import ChatRequest, ChatEvent, ToolCall, ToolResult, ProviderInfo
from models.db_models import ChatSessionDB, ChatMessageDB
from sqlalchemy import select, delete

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Get settings for API keys
settings = get_settings()

# Global skill injector instance
_skill_injector: SkillInjector | None = None


def get_skill_injector() -> SkillInjector:
    """Get or create the skill injector singleton."""
    global _skill_injector
    if _skill_injector is None:
        _skill_injector = SkillInjector()
    return _skill_injector


# Base system prompt for tool-enabled modes
def get_base_system_prompt(session_id: str = "default") -> str:
    """Build base system prompt with current date and session ID.

    Args:
        session_id: Current chat session ID for proposal tools

    Returns the system prompt dynamically so today's date and session_id are accurate at request time,
    not at module load time.
    """
    today = datetime.now().strftime("%Y-%m-%d (%A)")
    return f"""You are an AI assistant with access to the user's Second Brain system. You have powerful tools to query their calendar, tasks, and knowledge vault.

Today's date: {today}
Current Session ID: {session_id}

# Available Tools

## Calendar Tools
- **get_today_events**: Get all events for today
- **get_week_events**: Get events for the next 7 days from today
- **get_events_in_range(start, end)**: Get events for ANY custom date range. Use ISO format dates like "2026-01-05T00:00:00" and "2026-01-12T23:59:59". ALWAYS use this for specific future weeks or date ranges.
- **search_events(query)**: Search events by title or description

## Task Tools
- **get_overdue_tasks**: Get tasks past their due date
- **get_today_tasks**: Get tasks due today
- **get_week_tasks**: Get tasks due in the next 7 days
- **query_tasks(status, priority, project, has_due_date, limit)**: Flexible task query with filters
- **get_tasks_by_project**: Get tasks grouped by project folder

## Vault/Knowledge Tools
- **semantic_search(query, limit)**: Find related content by meaning/concept
- **text_search(query, limit)**: Find exact text matches
- **hybrid_search(query, limit)**: Combines semantic + text search (best for general queries)
- **read_vault_file(path)**: Read full content of a specific file
- **list_vault_directory(path)**: List files in a vault folder

## Skills Tools
- **list_skills(source, category)**: List all available thinking frameworks and skills. Filter by source (user, vault, database) or category.
- **get_skill(skill_id)**: Get full content of a specific skill
- **search_skills(query)**: Search skills by name or description
- **create_skill(name, description, when_to_use, category, content, tags)**: Create a new skill in the database. Categories: knowledge, workflow, analysis, creation, integration, training, productivity.
- **update_skill(skill_id, ...)**: Update an existing database skill (id starts with 'db_')
- **delete_skill(skill_id)**: Delete a database skill (soft delete)

IMPORTANT for Skills Tools:
- Use create_skill to make new reusable thinking frameworks, workflows, or procedures
- Database skills (created via create_skill) have IDs starting with 'db_'
- Only database skills can be updated or deleted via these tools
- Filesystem skills (in ~/.claude/skills) are read-only via these tools

## Proposal Tools (Write Mode)
When the user asks you to create, modify, or delete files in their vault:
- **propose_file_change(file_path, new_content, description, session_id)**: Modify an existing file
- **propose_new_file(file_path, content, description, session_id)**: Create a new file
- **propose_delete_file(file_path, description, session_id)**: Delete a file

IMPORTANT for Proposal Tools:
1. Use proposals instead of describing changes. The user can review diffs and approve.
2. For modifications, provide the COMPLETE new file content, not just the changes.
3. Always include a clear description explaining what you're changing and why.
4. File paths are relative to the vault root (e.g., "Notes/Daily/2025-12-21.md").
5. Delete proposals always require manual approval, even in YOLO mode.
6. You MUST pass the session_id parameter - use the current chat session ID.

# Guidelines

1. **Use the right tool for the request**: If the user asks about a specific date range (e.g., "week of January 5"), use get_events_in_range with the appropriate start and end dates.

2. **Be proactive with tools**: Don't say you can't do something if a tool exists for it. Check the tool list above.

3. **Combine tools when needed**: For complex questions, use multiple tools to gather complete information.

4. **Format responses clearly**: Use markdown headers, bullet points, and bold text to organize information.

5. **Cite sources**: When referencing vault content, mention the file path.

6. **Be concise**: Focus on answering the user's question directly.
"""


def build_system_prompt_with_skills(
    mode: str,
    messages: List[dict],
    session_id: str = "default",
    attached_skills: Optional[List[str]] = None,
    already_injected: Optional[List[str]] = None,
    mode_prompt_addition: Optional[str] = None,
) -> tuple[str, List[str]]:
    """Build system prompt with automatic and manual skill injection.

    Args:
        mode: Chat mode (quick, tools, agent)
        messages: Conversation history for context matching
        session_id: Current chat session ID for proposal tools
        attached_skills: Manually attached skill IDs
        already_injected: Skills already injected in this session
        mode_prompt_addition: Additional system prompt from selected database mode

    Returns:
        Tuple of (system_prompt, all_injected_skill_ids)
    """
    if mode == "quick":
        return "", []

    injector = get_skill_injector()
    all_injected = list(already_injected or [])

    # Start with base prompt (dynamically generated with current date and session_id)
    prompt = get_base_system_prompt(session_id=session_id)

    # Add mode-specific prompt addition if provided
    if mode_prompt_addition:
        prompt += f"\n\n# Mode-Specific Instructions\n{mode_prompt_addition}"

    # 1. Add manually attached skills first (user explicitly requested)
    if attached_skills:
        prompt = injector.inject_manual_skills(prompt, attached_skills)
        for skill_id in attached_skills:
            if skill_id not in all_injected:
                all_injected.append(skill_id)

    # 2. Add automatically matched skills
    enhanced_prompt, auto_injected = injector.build_skill_aware_prompt(
        base_prompt=prompt,
        messages=messages,
        already_injected=all_injected,
        mode=mode,
    )

    all_injected.extend(auto_injected)

    return enhanced_prompt, all_injected


async def chat_event_generator(
    request: ChatRequest,
    session_id: str,
    session_service: SessionService,
    already_injected: Optional[List[str]] = None,
    mode_prompt_addition: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming chat events via SSE with tool execution loop.

    Implements a tool execution loop that:
    1. Sends messages to LLM
    2. Collects tool calls from response
    3. Executes all tools
    4. Adds results to conversation
    5. Continues until LLM responds with text only (or max 5 turns)

    Args:
        request: Chat request with messages and configuration
        session_id: ID of the chat session
        session_service: Session service for persistence
        already_injected: Skills already injected in this session
        mode_prompt_addition: Additional system prompt from selected database mode

    Yields:
        SSE-formatted chat events
    """
    # Track accumulated data for saving assistant response
    all_accumulated_text = []
    all_accumulated_tool_calls = []
    all_accumulated_tool_results = []
    newly_injected_skills: List[str] = []

    try:
        # Get provider
        provider = get_provider(
            provider_type=request.provider,
            api_key=getattr(settings, f"{request.provider}_api_key", None),
        )

        if not provider:
            error_event = ChatEvent(
                type="error",
                data={"error": f"Provider {request.provider} not available"},
                timestamp=datetime.now(timezone.utc),
            )
            yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"
            return

        # Get tool registry (needed for both tools and skills)
        tool_registry = ToolRegistry.get_instance()

        # Build provider messages first for skill matching
        provider_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Build system prompt with automatic + manual skill injection (including session_id)
        system_prompt, all_injected = build_system_prompt_with_skills(
            mode=request.mode,
            messages=provider_messages,
            session_id=session_id,
            attached_skills=request.attached_skills,
            already_injected=already_injected,
            mode_prompt_addition=mode_prompt_addition,
        )

        # Track newly injected skills
        newly_injected_skills = [s for s in all_injected if s not in (already_injected or [])]
        if newly_injected_skills:
            logger.info(f"Auto-injected skills for session {session_id}: {newly_injected_skills}")

        # Convert ChatMessage objects to provider format
        provider_messages = []

        # Add system message first if we have one
        if system_prompt:
            provider_messages.append({"role": "system", "content": system_prompt})
            logger.info(
                f"Added system prompt with {len(request.attached_skills or [])} skills"
            )

        for msg in request.messages:
            provider_messages.append({"role": msg.role, "content": msg.content})

        # Get tools if mode is 'tools' or 'agent'
        tools = None
        tool_executor = None
        if request.mode in ["tools", "agent"]:
            tools = tool_registry.get_tools_for_provider(request.provider)
            tool_executor = ToolExecutor(tool_registry)
            logger.info(f"Loaded {len(tools)} tools for {request.mode} mode")

        # Send initial status
        yield f"event: status\ndata: {json.dumps({'status': 'started', 'session_id': session_id})}\n\n"

        # Tool execution loop - max 5 turns to prevent infinite loops
        max_turns = 5
        current_turn = 0

        while current_turn < max_turns:
            current_turn += 1
            logger.info(f"Starting turn {current_turn}/{max_turns}")

            # Track tool calls and text for this turn
            turn_tool_calls = []
            turn_text = []
            pending_tool_calls = {}  # Keyed by index, not ID

            # Stream response from provider
            async for event in provider.chat(
                messages=provider_messages,
                tools=tools,
                stream=True,
                model=request.model,
                max_tokens=8192,
            ):
                event_type = event.get("type")

                if event_type == "content":
                    # Text content from LLM
                    text = event.get("data", {}).get("text", "")
                    if text:
                        turn_text.append(text)
                        all_accumulated_text.append(text)
                        text_event = ChatEvent(
                            type="text",
                            data={"text": text},
                            timestamp=datetime.now(timezone.utc),
                        )
                        yield f"event: text\ndata: {text_event.model_dump_json()}\n\n"

                elif event_type == "tool_call_start":
                    # Tool call is starting (streaming)
                    tool_data = event.get("data", {})
                    tool_call_id = tool_data.get("id")
                    tool_name = tool_data.get("name")
                    tool_index = tool_data.get("index", 0)

                    # Key by index since deltas only have index
                    pending_tool_calls[tool_index] = {
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": "",
                    }

                    logger.info(f"Tool call starting: {tool_name} ({tool_call_id}) at index {tool_index}")

                elif event_type == "tool_call_delta":
                    # Streaming tool input JSON
                    tool_index = event.get("data", {}).get("index", 0)
                    partial_json = event.get("data", {}).get("partial_json", "")

                    if tool_index in pending_tool_calls:
                        pending_tool_calls[tool_index]["input"] += partial_json

                elif event_type == "tool_call":
                    # Complete tool call (non-streaming)
                    tool_data = event.get("data", {})
                    tool_call_id = tool_data.get("id")
                    tool_name = tool_data.get("name")
                    tool_input = tool_data.get("input", {})

                    # Store for execution after streaming completes
                    turn_tool_calls.append(
                        ToolCallRequest(
                            id=tool_call_id, name=tool_name, arguments=tool_input
                        )
                    )

                    # Track for database
                    tool_call_obj = ToolCall(
                        id=tool_call_id,
                        tool=tool_name,
                        arguments=tool_input,
                        status="pending",
                    )
                    all_accumulated_tool_calls.append(tool_call_obj.model_dump())

                    # Emit tool call event
                    tool_call_event = ChatEvent(
                        type="tool_call",
                        data=tool_call_obj.model_dump(),
                        timestamp=datetime.now(timezone.utc),
                    )
                    yield f"event: tool_call\ndata: {tool_call_event.model_dump_json()}\n\n"

                elif event_type == "content_block_stop":
                    # Content block finished - parse any pending tool calls for this index
                    stop_index = event.get("data", {}).get("index", 0)

                    if stop_index in pending_tool_calls:
                        tool_data = pending_tool_calls[stop_index]
                        # Check if we have a tool name (not just input)
                        # Tools with no parameters may have empty input string
                        if tool_data.get("name"):
                            try:
                                # Default to empty object for tools with no parameters
                                tool_input_str = tool_data.get("input", "") or "{}"
                                tool_input = json.loads(tool_input_str)
                                tool_name = tool_data["name"]
                                tool_call_id = tool_data["id"]

                                # Store for execution
                                turn_tool_calls.append(
                                    ToolCallRequest(
                                        id=tool_call_id,
                                        name=tool_name,
                                        arguments=tool_input,
                                    )
                                )

                                # Track for database
                                tool_call_obj = ToolCall(
                                    id=tool_call_id,
                                    tool=tool_name,
                                    arguments=tool_input,
                                    status="pending",
                                )
                                all_accumulated_tool_calls.append(tool_call_obj.model_dump())

                                # Emit tool call event
                                tool_call_event = ChatEvent(
                                    type="tool_call",
                                    data=tool_call_obj.model_dump(),
                                    timestamp=datetime.now(timezone.utc),
                                )
                                yield f"event: tool_call\ndata: {tool_call_event.model_dump_json()}\n\n"

                                logger.info(f"Tool call parsed: {tool_name} ({tool_call_id})")

                                # Clean up
                                del pending_tool_calls[stop_index]

                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse tool input for index {stop_index}: {e}")

                elif event_type == "usage":
                    # Token usage information
                    usage_data = event.get("data", {})
                    usage_event = ChatEvent(
                        type="usage",
                        data=usage_data,
                        timestamp=datetime.now(timezone.utc),
                    )
                    yield f"event: usage\ndata: {usage_event.model_dump_json()}\n\n"

                elif event_type == "error":
                    # Error from provider
                    error_data = event.get("data", {})
                    error_event = ChatEvent(
                        type="error", data=error_data, timestamp=datetime.now(timezone.utc)
                    )
                    yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"
                    return

                elif event_type == "stop":
                    # Stop event from provider with stop_reason
                    stop_reason = event.get("data", {}).get("stop_reason")
                    logger.info(f"LLM stop reason: {stop_reason}")

                    # If stop_reason is "max_tokens", log a warning about potential truncation
                    if stop_reason == "max_tokens":
                        logger.warning("Response may have been truncated due to max_tokens limit")
                        # Emit a warning event to the frontend
                        warning_event = ChatEvent(
                            type="log",
                            data={"message": "Warning: Response may have been truncated due to max_tokens limit"},
                            timestamp=datetime.now(timezone.utc),
                        )
                        yield f"event: log\ndata: {warning_event.model_dump_json()}\n\n"

                elif event_type == "done":
                    # Streaming complete for this turn
                    logger.info(f"Turn {current_turn} streaming complete")

            # Check if we have tool calls to execute
            if not turn_tool_calls:
                # No tool calls - conversation is complete
                logger.info("No tool calls - conversation complete")

                # Save assistant message to database
                assistant_content = "".join(all_accumulated_text)
                if assistant_content or all_accumulated_tool_calls:
                    await session_service.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=assistant_content,
                        tool_calls=all_accumulated_tool_calls if all_accumulated_tool_calls else None,
                        tool_results=all_accumulated_tool_results if all_accumulated_tool_results else None,
                        file_refs=None,
                    )
                    await session_service.db.commit()
                    logger.info(f"Saved assistant message to session {session_id}")

                done_event = ChatEvent(
                    type="done",
                    data={"provider": request.provider, "turns": current_turn, "session_id": session_id},
                    timestamp=datetime.now(timezone.utc),
                )
                yield f"event: done\ndata: {done_event.model_dump_json()}\n\n"
                break

            # Execute all tool calls for this turn
            if tool_executor:
                logger.info(f"Executing {len(turn_tool_calls)} tool calls")
                tool_results = await tool_executor.execute_all(turn_tool_calls)

                # Emit tool result events
                for i, result in enumerate(tool_results):
                    tool_result = ToolResult(
                        tool_call_id=result.tool_call_id,
                        result=result.content,
                        error=result.error,
                    )
                    all_accumulated_tool_results.append(tool_result.model_dump())

                    tool_result_event = ChatEvent(
                        type="tool_result",
                        data=tool_result.model_dump(),
                        timestamp=datetime.now(timezone.utc),
                    )
                    yield f"event: tool_result\ndata: {tool_result_event.model_dump_json()}\n\n"

                    # Check if this is a proposal tool result
                    tool_call = turn_tool_calls[i]
                    if tool_call.name in ["propose_file_change", "propose_new_file", "propose_delete_file"]:
                        # Emit proposal event for the UI
                        if isinstance(result.content, dict) and "proposal_id" in result.content:
                            proposal_data = {
                                "id": result.content.get("proposal_id"),
                                "description": result.content.get("message", ""),
                                "files": [{
                                    "path": result.content.get("file_path", tool_call.arguments.get("file_path", "")),
                                    "operation": "delete" if tool_call.name == "propose_delete_file" else
                                                 "create" if tool_call.name == "propose_new_file" else "modify",
                                    "diff_preview": result.content.get("diff_preview", ""),
                                    "lines_added": result.content.get("lines_added", 0),
                                    "lines_removed": result.content.get("lines_removed", 0),
                                }],
                                "status": result.content.get("status", "pending"),
                                "auto_applied": result.content.get("auto_applied", False),
                                "requires_approval": result.content.get("requires_approval", True),
                            }
                            proposal_event = ChatEvent(
                                type="proposal",
                                data=proposal_data,
                                timestamp=datetime.now(timezone.utc),
                            )
                            yield f"event: proposal\ndata: {proposal_event.model_dump_json()}\n\n"
                            logger.info(f"Emitted proposal event: {proposal_data['id']}")

                # Add assistant message with tool calls to conversation
                # For Anthropic, we need to include the tool use blocks
                assistant_content = []
                if turn_text:
                    assistant_content.append(
                        {"type": "text", "text": "".join(turn_text)}
                    )
                for tool_call in turn_tool_calls:
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.arguments,
                        }
                    )

                provider_messages.append(
                    {"role": "assistant", "content": assistant_content}
                )

                # Add tool results as user message
                if request.provider == "anthropic":
                    tool_result_content = tool_executor.format_for_anthropic(
                        tool_results
                    )
                    provider_messages.append(
                        {"role": "user", "content": tool_result_content}
                    )
                elif request.provider == "openai":
                    # OpenAI uses separate tool messages
                    tool_result_messages = tool_executor.format_for_openai(tool_results)
                    provider_messages.extend(tool_result_messages)

                logger.info(f"Added tool results to conversation, continuing to turn {current_turn + 1}")
            else:
                # No executor - shouldn't happen, but handle gracefully
                logger.warning("Tool calls present but no executor available")
                break

        # If we hit max turns, save and send done event
        if current_turn >= max_turns:
            logger.warning(f"Reached max turns ({max_turns})")

            # Save assistant message
            assistant_content = "".join(all_accumulated_text)
            if assistant_content or all_accumulated_tool_calls:
                await session_service.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_content,
                    tool_calls=all_accumulated_tool_calls if all_accumulated_tool_calls else None,
                    tool_results=all_accumulated_tool_results if all_accumulated_tool_results else None,
                    file_refs=None,
                )
                await session_service.db.commit()
                logger.info(f"Saved assistant message to session {session_id}")

            done_event = ChatEvent(
                type="done",
                data={
                    "provider": request.provider,
                    "turns": current_turn,
                    "max_turns_reached": True,
                    "session_id": session_id,
                },
                timestamp=datetime.now(timezone.utc),
            )
            yield f"event: done\ndata: {done_event.model_dump_json()}\n\n"

    except Exception as e:
        logger.error(f"Chat stream error: {e}", exc_info=True)
        error_event = ChatEvent(
            type="error", data={"error": str(e)}, timestamp=datetime.now(timezone.utc)
        )
        yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"


@router.post("")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Main chat endpoint with SSE streaming.

    Supports three modes:
    - quick: Direct LLM call without tools
    - tools: LLM with access to calendar, tasks, vault, skills (with tool execution loop)
    - agent: Autonomous agent mode (with tool execution loop)

    Args:
        request: Chat request with messages and configuration
        db: Database session

    Returns:
        SSE stream of chat events
    """
    from models.db_models import ModeDB

    # Generate or use existing session ID
    session_id = request.session_id or str(uuid.uuid4())

    # Create session service
    session_service = SessionService(db)

    # Track already injected skills from existing session
    already_injected: List[str] = []

    # Fetch database mode if mode_id is provided
    mode_prompt_addition: Optional[str] = None
    mode_id_uuid = None
    if request.mode_id:
        try:
            mode_id_uuid = uuid.UUID(request.mode_id)
            result = await db.execute(
                select(ModeDB).where(
                    ModeDB.id == mode_id_uuid,
                    ModeDB.deleted_at.is_(None),
                )
            )
            db_mode = result.scalar_one_or_none()
            if db_mode and db_mode.system_prompt_addition:
                mode_prompt_addition = db_mode.system_prompt_addition
                logger.info(f"Using mode '{db_mode.name}' with prompt addition")
        except Exception as e:
            logger.warning(f"Failed to fetch mode {request.mode_id}: {e}")

    # Create or update session in database
    if request.session_id:
        # Update existing session
        result = await db.execute(
            select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
        )
        session = result.scalar_one_or_none()
        if session:
            session.updated_at = datetime.now(timezone.utc)
            session.attached_skills = request.attached_skills
            # Get previously injected skills
            already_injected = session.injected_skills or []
        else:
            # Session ID provided but doesn't exist - create new one
            session = ChatSessionDB(
                id=uuid.UUID(session_id),
                mode=request.mode,
                provider=request.provider,
                model=request.model,
                attached_skills=request.attached_skills,
                injected_skills=[],
                mode_id=mode_id_uuid,
            )
            db.add(session)
    else:
        # Create new session
        session = ChatSessionDB(
            id=uuid.UUID(session_id),
            mode=request.mode,
            provider=request.provider,
            model=request.model,
            attached_skills=request.attached_skills,
            injected_skills=[],
            mode_id=mode_id_uuid,
        )
        db.add(session)

    # Flush to ensure session exists before adding messages (foreign key constraint)
    await db.flush()

    # Save user messages to database
    for msg in request.messages:
        if msg.role == "user":
            db_message = ChatMessageDB(
                session_id=uuid.UUID(session_id),
                role=msg.role,
                content=msg.content,
                tool_calls=None,
                tool_results=None,
                file_refs=None,
            )
            db.add(db_message)

    await db.commit()
    await db.refresh(session)

    return StreamingResponse(
        chat_event_generator(
            request,
            session_id,
            session_service,
            already_injected,
            mode_prompt_addition,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session_id,
        },
    )


@router.get("/sessions")
async def list_sessions(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    List chat sessions.

    Args:
        limit: Maximum number of sessions to return
        db: Database session

    Returns:
        List of chat sessions
    """
    # Fetch sessions from database, ordered by most recent first
    result = await db.execute(
        select(ChatSessionDB).order_by(ChatSessionDB.created_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()

    # Convert to dict format
    sessions_list = [session.to_dict() for session in sessions]

    return {"sessions": sessions_list, "count": len(sessions_list)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific chat session with message history.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Chat session details

    Raises:
        HTTPException: If session not found
    """
    # Fetch session from database
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch messages for this session
    messages_result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == uuid.UUID(session_id))
        .order_by(ChatMessageDB.created_at.asc())
    )
    messages = messages_result.scalars().all()

    # Convert to dict format
    session_dict = session.to_dict()
    session_dict["messages"] = [msg.to_dict() for msg in messages]

    return session_dict


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a chat session.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If session not found
    """
    # Check if session exists
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete all messages for this session
    await db.execute(
        delete(ChatMessageDB).where(ChatMessageDB.session_id == uuid.UUID(session_id))
    )

    # Delete the session
    await db.execute(
        delete(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
    )

    await db.commit()

    return {"message": "Session deleted successfully", "session_id": session_id}


@router.get("/providers", response_model=list[ProviderInfo])
async def get_providers():
    """
    Get list of available LLM providers and their models.

    Returns:
        List of provider information including available models
    """
    providers = []

    # Anthropic
    try:
        anthropic_models = get_provider_models("anthropic")
        providers.append(
            ProviderInfo(
                id="anthropic", name="Anthropic Claude", models=anthropic_models
            )
        )
    except Exception as e:
        logger.warning(f"Failed to get Anthropic models: {e}")

    # OpenAI (when implemented)
    try:
        openai_models = get_provider_models("openai")
        providers.append(
            ProviderInfo(id="openai", name="OpenAI GPT", models=openai_models)
        )
    except Exception as e:
        logger.warning(f"Failed to get OpenAI models: {e}")

    return providers


@router.post("/sessions/{session_id}/title")
async def generate_session_title(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Generate a 3-4 word title for a chat session using Haiku 4.5.

    Uses the first user message and first assistant response to generate
    a concise title summarizing the conversation topic.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Generated title

    Raises:
        HTTPException: If session not found or title generation fails
    """
    # Fetch session
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if title already exists
    if session.title:
        return {"title": session.title, "session_id": session_id}

    # Fetch messages for this session
    messages_result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == uuid.UUID(session_id))
        .order_by(ChatMessageDB.created_at.asc())
        .limit(2)
    )
    messages = messages_result.scalars().all()

    # Need at least one user message
    first_user_msg = next((m for m in messages if m.role == "user"), None)
    first_assistant_msg = next((m for m in messages if m.role == "assistant"), None)

    if not first_user_msg:
        raise HTTPException(status_code=400, detail="No user messages found")

    # Build prompt for title generation
    title_prompt = f"""Generate a 3-4 word title summarizing this conversation.
User: {first_user_msg.content[:500]}
{f"Assistant: {first_assistant_msg.content[:500]}" if first_assistant_msg else ""}
Respond with ONLY the title, no quotes or punctuation."""

    try:
        # Get Anthropic provider for Haiku
        provider = get_provider(
            provider_type="anthropic",
            api_key=settings.anthropic_api_key,
        )

        if not provider:
            raise HTTPException(status_code=500, detail="Anthropic provider not available")

        # Call Haiku 4.5 for title generation
        title_text = ""
        async for event in provider.chat(
            messages=[{"role": "user", "content": title_prompt}],
            tools=None,
            stream=True,
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
        ):
            if event.get("type") == "content":
                title_text += event.get("data", {}).get("text", "")

        # Clean up title
        title = title_text.strip().replace('"', '').replace("'", "")[:100]

        # Save title to session
        session.title = title
        await db.commit()

        logger.info(f"Generated title for session {session_id}: {title}")
        return {"title": title, "session_id": session_id}

    except Exception as e:
        logger.error(f"Failed to generate title for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Title generation failed: {str(e)}")

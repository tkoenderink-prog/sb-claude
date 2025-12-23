"""Agent API endpoints for autonomous tasks."""

import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from core.database import get_db
from core.config import get_settings
from core.providers.anthropic import AnthropicProvider
from core.tools.registry import ToolRegistry
from core.agent.sdk_runtime import SDKAgentRuntime
from models.chat import (
    AgentRunRequest,
    AgentRun,
    ArtifactRef,
    TokenUsage,
    ChatEvent,
    ToolCall,
)
from models.db_models import AgentRunDB, AgentArtifactDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


# ============================================================================
# Agent Runtime Helpers
# ============================================================================


class AgentRuntime:
    """Runtime for executing autonomous agent tasks.

    NOTE: This is the legacy implementation. New code should use
    SDKAgentRuntime from core.agent.sdk_runtime for better subagent support.
    """

    def __init__(self, provider: AnthropicProvider):
        """Initialize agent runtime.

        Args:
            provider: LLM provider (currently only Anthropic)
        """
        self.provider = provider
        self.tool_registry = ToolRegistry.get_instance()

    async def execute(
        self,
        run_id: str,
        task: str,
        context: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        max_turns: int = 10,
        attached_skills: list[str] = None,
    ) -> AsyncGenerator[ChatEvent, None]:
        """Execute autonomous agent task.

        Args:
            run_id: Unique run identifier
            task: Task description
            context: Optional additional context
            tools: Available tools (None = all tools)
            max_turns: Maximum conversation turns
            attached_skills: Skills to include in system prompt

        Yields:
            ChatEvent objects for streaming to client
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(task, context, attached_skills)

        # Initialize conversation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]

        # Track metrics
        turns = 0
        tool_calls_count = 0
        input_tokens = 0
        output_tokens = 0

        # Emit start status
        yield ChatEvent(
            type="status",
            data={"run_id": run_id, "status": "running", "turns": turns},
        )

        try:
            # Agent loop
            while turns < max_turns:
                turns += 1

                # Emit turn status
                yield ChatEvent(
                    type="status",
                    data={"run_id": run_id, "status": "running", "turns": turns},
                )

                # Call LLM
                response_text = ""
                response_tool_calls = []

                # Get tools for Anthropic provider if not specified
                provider_tools = tools if tools is not None else self.tool_registry.get_tools_for_provider("anthropic")

                async for event in self.provider.chat(
                    messages=messages,
                    tools=provider_tools,
                    stream=True,
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                ):
                    event_type = event.get("type")
                    event_data = event.get("data", {})

                    if event_type == "content":
                        # Stream text content
                        text = event_data.get("text", "")
                        response_text += text
                        yield ChatEvent(type="text", data=text)

                    elif event_type == "tool_call":
                        # Tool call detected
                        tool_call = ToolCall(
                            id=event_data.get("id"),
                            tool=event_data.get("name"),
                            arguments=event_data.get("input", {}),
                            status="pending",
                        )
                        response_tool_calls.append(tool_call)
                        tool_calls_count += 1

                        yield ChatEvent(
                            type="tool_call",
                            data=tool_call.model_dump(),
                        )

                    elif event_type == "usage":
                        # Track token usage
                        input_tokens += event_data.get("input_tokens", 0)
                        output_tokens += event_data.get("output_tokens", 0)

                    elif event_type == "error":
                        # Propagate errors
                        yield ChatEvent(type="error", data=event_data)
                        return

                # If no tool calls, agent is done
                if not response_tool_calls:
                    # Emit final usage
                    usage = TokenUsage(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        estimated_cost_usd=self._estimate_cost(
                            input_tokens, output_tokens
                        ),
                    )
                    yield ChatEvent(type="usage", data=usage.model_dump())

                    # Emit done status
                    yield ChatEvent(
                        type="done",
                        data={
                            "run_id": run_id,
                            "turns": turns,
                            "tool_calls": tool_calls_count,
                        },
                    )
                    return

                # Add assistant message to conversation
                messages.append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.tool,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in response_tool_calls
                        ],
                    }
                )

                # Execute tool calls
                for tool_call in response_tool_calls:
                    try:
                        result = await self._execute_tool_call(tool_call)

                        yield ChatEvent(
                            type="tool_result",
                            data={
                                "tool_call_id": tool_call.id,
                                "result": result,
                                "error": None,
                            },
                        )

                        # Add tool result to conversation
                        messages.append(
                            {
                                "role": "tool",
                                "content": json.dumps(result),
                                "tool_call_id": tool_call.id,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Tool call {tool_call.tool} failed: {e}", exc_info=True)
                        error_result = {
                            "error": str(e),
                            "tool": tool_call.tool,
                        }

                        yield ChatEvent(
                            type="tool_result",
                            data={
                                "tool_call_id": tool_call.id,
                                "result": None,
                                "error": str(e),
                            },
                        )

                        # Add error to conversation
                        messages.append(
                            {
                                "role": "tool",
                                "content": json.dumps(error_result),
                                "tool_call_id": tool_call.id,
                            }
                        )

            # Max turns reached
            yield ChatEvent(
                type="error",
                data={"error": f"Max turns ({max_turns}) reached without completion"},
            )

        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            yield ChatEvent(type="error", data={"error": str(e)})

    def _build_system_prompt(
        self, task: str, context: Optional[str], attached_skills: list[str]
    ) -> str:
        """Build system prompt for agent.

        Args:
            task: Task description
            context: Optional context
            attached_skills: Skills to include

        Returns:
            System prompt string
        """
        today = datetime.now().strftime("%Y-%m-%d (%A)")
        prompt = f"""You are an autonomous AI agent with access to tools for querying calendar, tasks, vault, and other data sources.

Today's date: {today}

Your goal is to complete the user's task by:
1. Breaking down the task into steps
2. Using available tools to gather information
3. Synthesizing findings into a coherent response
4. Optionally creating artifacts (reports, analyses, etc.)

Be thorough, cite sources, and explain your reasoning.
"""

        if context:
            prompt += f"\n\nAdditional Context:\n{context}\n"

        if attached_skills:
            prompt += f"\n\nAttached Skills: {', '.join(attached_skills)}\n"

        return prompt

    async def _execute_tool_call(self, tool_call: ToolCall) -> dict:
        """Execute a tool call via the ToolRegistry.

        Args:
            tool_call: Tool call to execute

        Returns:
            Tool result

        Raises:
            ValueError: If tool execution fails
        """
        return await self.tool_registry.execute(tool_call.tool, tool_call.arguments)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Claude Sonnet 4 pricing (approximate)
        # $3 per million input tokens, $15 per million output tokens
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        return input_cost + output_cost


class ArtifactManager:
    """Manager for agent artifacts."""

    def __init__(self, artifacts_dir: Path):
        """Initialize artifact manager.

        Args:
            artifacts_dir: Directory to store artifacts
        """
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def save_artifact(
        self,
        run_id: str,
        name: str,
        content: bytes,
        artifact_type: str,
        mime_type: str,
    ) -> ArtifactRef:
        """Save an artifact to disk.

        Args:
            run_id: Agent run ID
            name: Artifact name
            content: Artifact content
            artifact_type: Type of artifact
            mime_type: MIME type

        Returns:
            ArtifactRef with metadata
        """
        # Create run-specific directory
        run_dir = self.artifacts_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = run_dir / name
        file_path.write_bytes(content)

        # Create artifact reference
        artifact = ArtifactRef(
            name=name,
            type=artifact_type,
            mime_type=mime_type,
            size_bytes=len(content),
            download_url=f"/api/agent/runs/{run_id}/artifacts/{name}",
        )

        return artifact

    def get_artifact_path(self, run_id: str, artifact_name: str) -> Path:
        """Get path to artifact file.

        Args:
            run_id: Agent run ID
            artifact_name: Artifact name

        Returns:
            Path to artifact file
        """
        return self.artifacts_dir / run_id / artifact_name


# ============================================================================
# Dependency Injection
# ============================================================================


def get_agent_runtime() -> AgentRuntime:
    """Get agent runtime instance (legacy).

    Returns:
        AgentRuntime instance
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    provider = AnthropicProvider(api_key=settings.anthropic_api_key)
    return AgentRuntime(provider=provider)


def get_sdk_agent_runtime() -> SDKAgentRuntime:
    """Get SDK agent runtime instance (new).

    Returns:
        SDKAgentRuntime instance using Claude Agent SDK
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    return SDKAgentRuntime(api_key=settings.anthropic_api_key)


def get_artifact_manager() -> ArtifactManager:
    """Get artifact manager instance.

    Returns:
        ArtifactManager instance
    """
    # Store artifacts in exports/artifacts/
    artifacts_dir = Path(__file__).parent.parent.parent.parent / "exports" / "artifacts"
    return ArtifactManager(artifacts_dir=artifacts_dir)


# ============================================================================
# API Endpoints
# ============================================================================


async def agent_run_generator(
    run: AgentRunDB,
    request: AgentRunRequest,
    runtime: SDKAgentRuntime,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Generator for streaming agent execution via SSE using SDK runtime.

    Args:
        run: Database record for this run
        request: Agent run request
        runtime: SDK agent runtime instance
        db: Database session

    Yields:
        SSE-formatted events
    """
    try:
        # Update status to running
        await db.execute(
            update(AgentRunDB).where(AgentRunDB.id == run.id).values(status="running")
        )
        await db.commit()

        # Execute agent using SDK runtime
        async for event in runtime.execute(
            run_id=str(run.id),
            task=request.task,
            context=request.context,
            tools=request.tools,  # Pass requested tools (None = all)
            max_turns=request.max_turns,
            attached_skills=request.attached_skills,
        ):
            # Event is already a dict from SDK runtime
            event_type = event.get("type")
            event_data = event.get("data", {})

            # Format as SSE with timestamp
            event_dict = {
                "type": event_type,
                "data": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            yield f"event: {event_type}\ndata: {json.dumps(event_dict)}\n\n"

            # Update database on certain events
            if event_type == "usage":
                await db.execute(
                    update(AgentRunDB)
                    .where(AgentRunDB.id == run.id)
                    .values(
                        input_tokens=event_data.get("input_tokens", 0),
                        output_tokens=event_data.get("output_tokens", 0),
                    )
                )
                await db.commit()

            elif event_type == "done":
                await db.execute(
                    update(AgentRunDB)
                    .where(AgentRunDB.id == run.id)
                    .values(
                        status="completed",
                        ended_at=datetime.now(timezone.utc),
                        turns=event_data.get("turns", 0),
                        tool_calls=event_data.get("tool_calls", 0),
                    )
                )
                await db.commit()

            elif event_type == "error":
                await db.execute(
                    update(AgentRunDB)
                    .where(AgentRunDB.id == run.id)
                    .values(
                        status="failed",
                        ended_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()

    except Exception as e:
        logger.error(f"Agent run {run.id} failed: {e}", exc_info=True)

        # Mark as failed
        await db.execute(
            update(AgentRunDB)
            .where(AgentRunDB.id == run.id)
            .values(
                status="failed",
                ended_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

        # Send error event
        error_event = {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"


@router.post("/run")
async def run_agent(
    request: AgentRunRequest,
    runtime: SDKAgentRuntime = Depends(get_sdk_agent_runtime),
    db: AsyncSession = Depends(get_db),
):
    """Start autonomous agent task with SSE streaming using Claude Agent SDK.

    Args:
        request: Agent run request
        runtime: SDK agent runtime instance
        db: Database session

    Returns:
        SSE stream of agent execution events
    """
    # Create agent run record
    run = AgentRunDB(
        task=request.task,
        status="running",
        attached_skills=request.attached_skills,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    logger.info(f"Starting agent run {run.id}: {request.task[:100]}...")

    # Stream execution
    return StreamingResponse(
        agent_run_generator(run, request, runtime, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Run-ID": str(run.id),
        },
    )


@router.get("/runs", response_model=list[AgentRun])
async def list_agent_runs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List agent runs.

    Args:
        limit: Maximum number of runs to return (default: 50)
        db: Database session

    Returns:
        List of agent runs, most recent first
    """
    result = await db.execute(
        select(AgentRunDB).order_by(AgentRunDB.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()

    # Convert to response models
    return [
        AgentRun(
            id=str(run.id),
            task=run.task,
            status=run.status,
            started_at=run.started_at,
            ended_at=run.ended_at,
            turns=run.turns,
            tool_calls=run.tool_calls,
            artifacts=[],  # Omit artifacts in list view for performance; use get_agent_run for full details
            usage=TokenUsage(
                input_tokens=run.input_tokens,
                output_tokens=run.output_tokens,
                total_tokens=run.input_tokens + run.output_tokens,
                estimated_cost_usd=(run.input_tokens / 1_000_000) * 3.0
                + (run.output_tokens / 1_000_000) * 15.0,
            )
            if run.input_tokens > 0
            else None,
        )
        for run in runs
    ]


@router.get("/runs/{run_id}", response_model=AgentRun)
async def get_agent_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get agent run details.

    Args:
        run_id: Agent run ID
        db: Database session

    Returns:
        Agent run details

    Raises:
        HTTPException: If run not found
    """
    result = await db.execute(select(AgentRunDB).where(AgentRunDB.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail=f"Agent run {run_id} not found")

    # Fetch artifacts
    artifacts_result = await db.execute(
        select(AgentArtifactDB).where(AgentArtifactDB.run_id == run_id)
    )
    artifacts = artifacts_result.scalars().all()

    return AgentRun(
        id=str(run.id),
        task=run.task,
        status=run.status,
        started_at=run.started_at,
        ended_at=run.ended_at,
        turns=run.turns,
        tool_calls=run.tool_calls,
        artifacts=[
            ArtifactRef(
                id=str(artifact.id),
                name=artifact.name,
                type=artifact.type,
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                download_url=f"/api/agent/runs/{run_id}/artifacts/{artifact.id}",
                created_at=artifact.created_at,
            )
            for artifact in artifacts
        ],
        usage=TokenUsage(
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            total_tokens=run.input_tokens + run.output_tokens,
            estimated_cost_usd=(run.input_tokens / 1_000_000) * 3.0
            + (run.output_tokens / 1_000_000) * 15.0,
        )
        if run.input_tokens > 0
        else None,
    )


@router.get("/runs/{run_id}/artifacts")
async def list_artifacts(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List artifacts from agent run.

    Args:
        run_id: Agent run ID
        db: Database session

    Returns:
        List of artifact references

    Raises:
        HTTPException: If run not found
    """
    # Verify run exists
    result = await db.execute(select(AgentRunDB).where(AgentRunDB.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Agent run {run_id} not found")

    # Fetch artifacts
    artifacts_result = await db.execute(
        select(AgentArtifactDB).where(AgentArtifactDB.run_id == run_id)
    )
    artifacts = artifacts_result.scalars().all()

    return [
        ArtifactRef(
            id=str(artifact.id),
            name=artifact.name,
            type=artifact.type,
            mime_type=artifact.mime_type,
            size_bytes=artifact.size_bytes,
            download_url=f"/api/agent/runs/{run_id}/artifacts/{artifact.id}",
            created_at=artifact.created_at,
        )
        for artifact in artifacts
    ]


@router.get("/runs/{run_id}/artifacts/{artifact_id}")
async def download_artifact(
    run_id: str,
    artifact_id: str,
    artifact_manager: ArtifactManager = Depends(get_artifact_manager),
    db: AsyncSession = Depends(get_db),
):
    """Download artifact file.

    Args:
        run_id: Agent run ID
        artifact_id: Artifact ID
        artifact_manager: Artifact manager instance
        db: Database session

    Returns:
        File download response

    Raises:
        HTTPException: If artifact not found
    """
    # Fetch artifact metadata
    result = await db.execute(
        select(AgentArtifactDB).where(
            AgentArtifactDB.id == artifact_id,
            AgentArtifactDB.run_id == run_id,
        )
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {artifact_id} not found in run {run_id}",
        )

    # Get file path
    file_path = artifact_manager.get_artifact_path(run_id, artifact.name)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Artifact file not found: {artifact.name}",
        )

    return FileResponse(
        path=str(file_path),
        media_type=artifact.mime_type,
        filename=artifact.name,
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_agent_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel running agent.

    Args:
        run_id: Agent run ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If run not found or not running
    """
    # Fetch run
    result = await db.execute(select(AgentRunDB).where(AgentRunDB.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail=f"Agent run {run_id} not found")

    if run.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel run with status: {run.status}",
        )

    # Update status to cancelled
    # Note: This doesn't actually stop the running task (would need task cancellation)
    # For now, just marks it as cancelled
    await db.execute(
        update(AgentRunDB)
        .where(AgentRunDB.id == run_id)
        .values(
            status="cancelled",
            ended_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    return {"message": f"Agent run {run_id} cancelled", "run_id": run_id}

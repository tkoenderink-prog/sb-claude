"""Chat and agent execution models for Phase 7."""

from datetime import datetime
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field
import uuid


# Literal types for type safety
ChatMode = Literal["quick", "tools", "agent"]
ChatEventType = Literal[
    "text",
    "tool_call",
    "tool_result",
    "file_ref",
    "artifact",
    "thinking",
    "error",
    "usage",
    "done",
    "proposal",
]
MessageRole = Literal["user", "assistant", "system", "tool"]
ToolCallStatus = Literal["pending", "success", "error"]
ArtifactType = Literal["report", "analysis", "export", "code", "other"]
AgentRunStatus = Literal["running", "completed", "failed", "cancelled"]


class FileRef(BaseModel):
    """Reference to a file in the vault (for file chips)."""

    path: str
    obsidian_uri: str
    heading: Optional[str] = None
    score: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "path": "Projects/Second Brain/Phase 7.md",
                "obsidian_uri": "obsidian://open?vault=Obsidian-Private&file=Projects%2FSecond%20Brain%2FPhase%207.md",
                "heading": "Implementation Details",
                "score": 0.89,
            }
        }


class ToolCall(BaseModel):
    """Tool invocation during chat or agent execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool: str
    arguments: dict[str, Any]
    status: ToolCallStatus = "pending"

    class Config:
        json_schema_extra = {
            "example": {
                "id": "tool_call_123",
                "tool": "get_today_events",
                "arguments": {"timezone": "Europe/Amsterdam"},
                "status": "success",
            }
        }


class ToolResult(BaseModel):
    """Result from a tool execution."""

    tool_call_id: str
    result: Any
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "tool_call_id": "tool_call_123",
                "result": {
                    "events": [
                        {"title": "Team standup", "start": "2025-12-20T10:00:00"}
                    ]
                },
                "error": None,
            }
        }


class ChatMessage(BaseModel):
    """Single message in a chat conversation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: Optional[list[ToolCall]] = None
    tool_results: Optional[list[ToolResult]] = None
    file_refs: Optional[list[FileRef]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_456",
                "role": "user",
                "content": "What's on my calendar today?",
                "timestamp": "2025-12-20T10:30:00Z",
                "tool_calls": None,
                "tool_results": None,
                "file_refs": None,
            }
        }


class ChatSession(BaseModel):
    """Persistent chat session with history."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: ChatMode
    provider: str
    model: str
    messages: list[ChatMessage] = Field(default_factory=list)
    attached_skills: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_789",
                "mode": "tools",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "messages": [],
                "attached_skills": ["context-aware-reasoning"],
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-20T10:30:00Z",
            }
        }


class ChatRequest(BaseModel):
    """Request to send a message in chat mode."""

    mode: ChatMode = "tools"
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    messages: list[ChatMessage]
    attached_skills: list[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    mode_id: Optional[str] = None  # Phase 9: Database mode reference

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "tools",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "messages": [
                    {
                        "role": "user",
                        "content": "What tasks are overdue?",
                        "timestamp": "2025-12-20T10:30:00Z",
                    }
                ],
                "attached_skills": [],
                "session_id": None,
                "mode_id": None,
            }
        }


class ChatEvent(BaseModel):
    """SSE event emitted during chat streaming."""

    type: ChatEventType
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "text",
                "data": "Let me check your calendar...",
                "timestamp": "2025-12-20T10:30:05Z",
            }
        }


class TokenUsage(BaseModel):
    """Token usage and cost tracking."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float

    class Config:
        json_schema_extra = {
            "example": {
                "input_tokens": 1500,
                "output_tokens": 300,
                "total_tokens": 1800,
                "estimated_cost_usd": 0.0234,
            }
        }


class ArtifactRef(BaseModel):
    """Reference to an artifact produced by agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: ArtifactType
    mime_type: str
    size_bytes: int
    download_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "artifact_abc",
                "name": "weekly_analysis.md",
                "type": "analysis",
                "mime_type": "text/markdown",
                "size_bytes": 4096,
                "download_url": "/api/agent/runs/run_xyz/artifacts/artifact_abc",
                "created_at": "2025-12-20T11:00:00Z",
            }
        }


class AgentRun(BaseModel):
    """Agent execution run record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    status: AgentRunStatus = "running"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    turns: int = 0
    tool_calls: int = 0
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    usage: Optional[TokenUsage] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "run_xyz",
                "task": "Analyze my calendar for next week and identify potential conflicts",
                "status": "running",
                "started_at": "2025-12-20T10:30:00Z",
                "ended_at": None,
                "turns": 3,
                "tool_calls": 5,
                "artifacts": [],
                "usage": None,
            }
        }


class AgentRunRequest(BaseModel):
    """Request to start an autonomous agent run."""

    task: str
    context: Optional[str] = None
    tools: Optional[list[str]] = None  # None = all tools available
    max_turns: int = 10
    attached_skills: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "task": "Analyze my task backlog and create prioritization report",
                "context": "Focus on work projects, exclude personal tasks",
                "tools": None,
                "max_turns": 10,
                "attached_skills": ["task-analyzer"],
            }
        }


class ProviderInfo(BaseModel):
    """Information about an LLM provider and its models."""

    id: str
    name: str
    models: list[dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "models": [
                    {
                        "id": "claude-opus-4-20250514",
                        "name": "Claude Opus 4",
                        "context_window": 200000,
                        "max_output": 16000,
                    },
                    {
                        "id": "claude-sonnet-4-20250514",
                        "name": "Claude Sonnet 4",
                        "context_window": 200000,
                        "max_output": 16000,
                    },
                ],
            }
        }

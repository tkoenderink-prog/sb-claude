"""SQLAlchemy ORM models for database tables."""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum


class JobTypeEnum(str, enum.Enum):
    processor = "processor"
    index = "index"
    agent = "agent"
    chat = "chat"


class JobStatusEnum(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class JobDB(Base):
    """Database model for jobs table."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    command = Column(String(255), nullable=False)
    args = Column(JSON, nullable=True)
    artifacts = Column(JSON, default=list)
    metrics = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "type": self.type,
            "status": self.status,
            "command": self.command,
            "args": self.args,
            "artifacts": self.artifacts or [],
            "metrics": self.metrics,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }


class CalendarEventDB(Base):
    """Database model for calendar_events table."""

    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # 'google' or 'm365'
    calendar_id = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(100), nullable=True)
    all_day = Column(Boolean, default=False)
    attendees = Column(JSON, nullable=True)
    visibility = Column(String(50), default="private")
    source_provenance = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "event_id": self.event_id,
            "provider": self.provider,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "timezone": self.timezone,
            "all_day": self.all_day,
            "attendees": self.attendees or [],
            "visibility": self.visibility,
            "source_provenance": self.source_provenance,
        }


class TaskDB(Base):
    """Database model for tasks table."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(1000), nullable=False)
    line_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    text_clean = Column(Text, nullable=False)
    status = Column(
        String(50), nullable=False
    )  # 'todo', 'done', 'in_progress', 'cancelled'
    due_date = Column(Date, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    priority = Column(
        String(20), nullable=True
    )  # 'highest', 'high', 'medium', 'low', 'lowest'
    tags = Column(JSON, default=list)
    estimate_min = Column(Integer, nullable=True)
    actual_min = Column(Integer, nullable=True)
    obsidian_uri = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "task_id": self.task_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "text": self.text,
            "text_clean": self.text_clean,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "scheduled_date": self.scheduled_date.isoformat()
            if self.scheduled_date
            else None,
            "priority": self.priority,
            "tags": self.tags or [],
            "estimate_min": self.estimate_min,
            "actual_min": self.actual_min,
            "obsidian_uri": self.obsidian_uri,
        }


# ============================================================================
# Phase 7: Chat & Agent Models
# ============================================================================


class ChatModeEnum(str, enum.Enum):
    tools = "tools"
    agent = "agent"


class ChatRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class AgentStatusEnum(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ChatSessionDB(Base):
    """Database model for chat_sessions table."""

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mode = Column(String(20), nullable=False)  # 'tools', 'agent'
    provider = Column(String(50), nullable=False)  # 'anthropic', 'openai'
    model = Column(String(100), nullable=False)  # 'claude-opus-4', 'gpt-4o', etc.
    title = Column(String(100), nullable=True)  # Phase 8: AI-generated title
    attached_skills = Column(JSON, default=list)
    injected_skills = Column(JSON, default=list)  # Phase 7B: Auto-injected skills
    # Phase 9: Token tracking
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Integer, default=0)  # Stored as microdollars (millionths)
    mode_id = Column(UUID(as_uuid=True), nullable=True)  # Phase 9: Mode reference
    # Phase 10: Persona and council support
    lead_persona_id = Column(UUID(as_uuid=True), nullable=True)  # Orchestrator persona
    council_member_ids = Column(ARRAY(Text), default=list)  # Available council members
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "mode": self.mode,
            "provider": self.provider,
            "model": self.model,
            "title": self.title,
            "attached_skills": self.attached_skills or [],
            "injected_skills": self.injected_skills or [],
            "total_input_tokens": self.total_input_tokens or 0,
            "total_output_tokens": self.total_output_tokens or 0,
            "total_cost_usd": (self.total_cost_usd or 0) / 1_000_000,  # Convert to dollars
            "mode_id": str(self.mode_id) if self.mode_id else None,
            "lead_persona_id": str(self.lead_persona_id) if self.lead_persona_id else None,
            "council_member_ids": self.council_member_ids or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessageDB(Base):
    """Database model for chat_messages table."""

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # Foreign key to chat_sessions
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    file_refs = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "file_refs": self.file_refs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentRunDB(Base):
    """Database model for agent_runs table."""

    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task = Column(Text, nullable=False)
    status = Column(
        String(20), nullable=False
    )  # 'running', 'completed', 'failed', 'cancelled'
    attached_skills = Column(JSON, default=list)
    turns = Column(Integer, default=0)
    tool_calls = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "task": self.task,
            "status": self.status,
            "attached_skills": self.attached_skills or [],
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }


class AgentArtifactDB(Base):
    """Database model for agent_artifacts table."""

    __tablename__ = "agent_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False)  # Foreign key to agent_runs
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'document', 'code', 'data', etc.
    mime_type = Column(
        String(100), nullable=False
    )  # 'text/markdown', 'application/json', etc.
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "name": self.name,
            "type": self.type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Phase 7B: Skills & Sessions Models
# ============================================================================


class SkillCategoryEnum(str, enum.Enum):
    """Skill categories for organization and filtering."""

    knowledge = "knowledge"  # Mental models, frameworks, references
    workflow = "workflow"  # Process automation, checklists
    analysis = "analysis"  # Data analysis, pattern recognition
    creation = "creation"  # Content creation, writing
    integration = "integration"  # External systems, APIs
    training = "training"  # Physical training, health
    productivity = "productivity"  # Task management, time management
    uncategorized = "uncategorized"


class UserSkillDB(Base):
    """User-created skills stored in database."""

    __tablename__ = "user_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    when_to_use = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="uncategorized")
    tags = Column(JSON, default=list)
    content = Column(Text, nullable=False)
    version = Column(String(20), nullable=True)
    # Phase 10: Persona scoping
    persona_ids = Column(JSON, nullable=True)  # NULL = universal, ["uuid1", "uuid2"] = scoped
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "category": self.category,
            "tags": self.tags or [],
            "content": self.content,
            "version": self.version,
            "persona_ids": self.persona_ids,
            "source": "database",
            "has_checklist": "[ ]" in (self.content or ""),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SkillUsageDB(Base):
    """Track skill usage for relevance scoring."""

    __tablename__ = "skill_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(String(255), nullable=False)
    skill_source = Column(String(20), nullable=False)  # "user", "vault", "database"
    session_id = Column(UUID(as_uuid=True), nullable=True)  # FK to chat_sessions
    matched_by = Column(String(20), nullable=False)  # "automatic" or "manual"
    relevance_score = Column(Integer, nullable=True)
    used_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "skill_id": self.skill_id,
            "skill_source": self.skill_source,
            "session_id": str(self.session_id) if self.session_id else None,
            "matched_by": self.matched_by,
            "relevance_score": self.relevance_score,
            "used_at": self.used_at.isoformat() if self.used_at else None,
        }


# ============================================================================
# Phase 8: Proposals & Settings Models
# ============================================================================


class ProposalStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"


class ProposalOperationEnum(str, enum.Enum):
    create = "create"
    modify = "modify"
    delete = "delete"


class ProposalDB(Base):
    """Database model for file change proposals."""

    __tablename__ = "proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)  # FK to chat_sessions
    status = Column(String(20), nullable=False, default="pending")
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)
    backup_path = Column(String(500), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "backup_path": self.backup_path,
        }


class ProposalFileDB(Base):
    """Database model for individual files in a proposal."""

    __tablename__ = "proposal_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(UUID(as_uuid=True), nullable=False)  # FK to proposals
    file_path = Column(String(1000), nullable=False)
    operation = Column(String(20), nullable=False)  # create, modify, delete
    original_content = Column(Text, nullable=True)
    proposed_content = Column(Text, nullable=True)
    diff_hunks = Column(JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "proposal_id": str(self.proposal_id),
            "file_path": self.file_path,
            "operation": self.operation,
            "original_content": self.original_content,
            "proposed_content": self.proposed_content,
            "diff_hunks": self.diff_hunks,
        }


class UserSettingsDB(Base):
    """Single-row table for user settings."""

    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    yolo_mode = Column(Boolean, default=False)
    default_model = Column(String(100), default="claude-sonnet-4-5-20250929")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Phase 9: System prompt customization
    system_prompt = Column(Text, nullable=True)
    system_prompt_history = Column(JSON, default=list)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "yolo_mode": self.yolo_mode,
            "default_model": self.default_model,
            "system_prompt": self.system_prompt,
            "system_prompt_history": self.system_prompt_history or [],
        }


# ============================================================================
# Phase 9: Conversation Intelligence & Mobile
# ============================================================================


class SyncStatusDB(Base):
    """Database model for sync status tracking."""

    __tablename__ = "sync_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="idle")
    last_sync_start = Column(DateTime(timezone=True), nullable=True)
    last_sync_end = Column(DateTime(timezone=True), nullable=True)
    files_processed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    sync_metadata = Column("metadata", JSON, default=dict)  # 'metadata' is reserved in SQLAlchemy
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sync_type": self.sync_type,
            "status": self.status,
            "last_sync_start": self.last_sync_start.isoformat() if self.last_sync_start else None,
            "last_sync_end": self.last_sync_end.isoformat() if self.last_sync_end else None,
            "files_processed": self.files_processed,
            "chunks_created": self.chunks_created,
            "error_message": self.error_message,
            "metadata": self.sync_metadata or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ApiKeyDB(Base):
    """Database model for encrypted API key storage."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False, unique=True)
    encrypted_key = Column(Text, nullable=False)
    key_suffix = Column(String(8), nullable=True)
    is_valid = Column(Boolean, default=True)
    last_validated = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "provider": self.provider,
            "key_suffix": self.key_suffix,
            "is_valid": self.is_valid,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ModeDB(Base):
    """Database model for custom conversation modes."""

    __tablename__ = "modes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="?")
    color = Column(String(7), default="#3B82F6")
    system_prompt_addition = Column(Text, nullable=True)
    default_model = Column(String(100), nullable=True)
    sort_order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    # Phase 10: Persona support
    is_persona = Column(Boolean, default=False)
    can_orchestrate = Column(Boolean, default=True)
    persona_config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "system_prompt_addition": self.system_prompt_addition,
            "default_model": self.default_model,
            "sort_order": self.sort_order,
            "is_default": self.is_default,
            "is_system": self.is_system,
            "is_persona": self.is_persona,
            "can_orchestrate": self.can_orchestrate,
            "persona_config": self.persona_config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StandardCommandDB(Base):
    """Database model for quick action commands."""

    __tablename__ = "standard_commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mode_id = Column(UUID(as_uuid=True), nullable=True)  # NULL = global
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    prompt = Column(Text, nullable=False)
    icon = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "mode_id": str(self.mode_id) if self.mode_id else None,
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatContextFileDB(Base):
    """Database model for context files attached to sessions."""

    __tablename__ = "chat_context_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    file_path = Column(String(1000), nullable=False)
    content_hash = Column(String(64), nullable=True)
    token_count = Column(Integer, nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "token_count": self.token_count,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

"""Job execution models."""

from datetime import datetime
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field
import uuid


JobType = Literal["processor", "index", "agent", "chat"]
JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class JobRunV1(BaseModel):
    """Job execution record (v1 schema)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: JobType
    status: JobStatus = "queued"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    command: str
    args: Optional[dict[str, Any]] = None
    artifacts: list[Any] = Field(default_factory=list)
    metrics: Optional[dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "processor",
                "status": "running",
                "started_at": "2025-12-20T10:30:00Z",
                "ended_at": None,
                "command": "calendar_sync",
                "args": {"sources": ["google", "m365"]},
                "artifacts": [],
                "metrics": None,
            }
        }

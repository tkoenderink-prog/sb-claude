"""Pydantic models for task parsing."""

from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field
import hashlib


class TaskItemV1(BaseModel):
    """
    Normalized task item matching contracts schema v1.

    Represents a single task parsed from an Obsidian markdown file.
    """
    task_id: str = Field(..., description="Unique task identifier (hash of file + line)")
    file_path: str = Field(..., description="Vault-relative path to file containing task")
    line_number: int = Field(..., description="1-based line number")
    text: str = Field(..., description="Full task text including metadata")
    text_clean: str = Field(..., description="Task description with metadata stripped")
    status: Literal['todo', 'done', 'in_progress', 'cancelled'] = Field(..., description="Task status")
    due_date: Optional[date] = Field(None, description="Due date")
    scheduled_date: Optional[date] = Field(None, description="Scheduled date")
    start_date: Optional[date] = Field(None, description="Start date")
    created_date: Optional[date] = Field(None, description="Created date")
    completed_date: Optional[date] = Field(None, description="Completed date")
    priority: Optional[Literal['highest', 'high', 'medium', 'low', 'lowest']] = Field(None, description="Priority level")
    tags: list[str] = Field(default_factory=list, description="List of #tags")
    contexts: list[str] = Field(default_factory=list, description="List of @contexts")
    estimate_min: Optional[int] = Field(None, description="Estimated time in minutes")
    actual_min: Optional[int] = Field(None, description="Actual time in minutes")
    recurrence: Optional[str] = Field(None, description="Recurrence pattern")
    obsidian_uri: Optional[str] = Field(None, description="Obsidian URI to open task")

    @classmethod
    def generate_task_id(cls, file_path: str, line_number: int) -> str:
        """Generate a unique task ID from file path and line number."""
        key = f"{file_path}:{line_number}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }

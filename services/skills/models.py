"""Pydantic models for skills."""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class SkillCategory(str, Enum):
    """Skill categories for organization and filtering."""

    KNOWLEDGE = "knowledge"  # Mental models, frameworks, references
    WORKFLOW = "workflow"  # Process automation, checklists
    ANALYSIS = "analysis"  # Data analysis, pattern recognition
    CREATION = "creation"  # Content creation, writing
    INTEGRATION = "integration"  # External systems, APIs
    TRAINING = "training"  # Physical training, health
    PRODUCTIVITY = "productivity"  # Task management, time management
    UNCATEGORIZED = "uncategorized"


class SkillMetadata(BaseModel):
    """Level 1: Lightweight metadata for all skills."""

    id: str
    name: str
    description: str
    when_to_use: str
    category: SkillCategory = SkillCategory.UNCATEGORIZED
    tags: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    source: str  # "user", "vault", "database"
    has_checklist: bool = False
    last_modified: Optional[datetime] = None
    trigger_keywords: List[str] = Field(default_factory=list)


class SkillInfo(SkillMetadata):
    """Level 2: Full skill with content (loaded on demand)."""

    path: str = ""  # Full path to skill directory (empty for DB skills)
    content: str = ""  # Full SKILL.md content


class SkillCreate(BaseModel):
    """Schema for creating a new skill."""

    name: str
    description: str
    when_to_use: str
    category: SkillCategory = SkillCategory.UNCATEGORIZED
    tags: List[str] = Field(default_factory=list)
    content: str


class SkillUpdate(BaseModel):
    """Schema for updating an existing skill."""

    name: Optional[str] = None
    description: Optional[str] = None
    when_to_use: Optional[str] = None
    category: Optional[SkillCategory] = None
    tags: Optional[List[str]] = None
    content: Optional[str] = None

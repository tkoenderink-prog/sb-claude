"""Skills API endpoints with CRUD and category support."""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

# Add services to path
services_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(services_path))

from skills.models import (  # noqa: E402
    SkillCreate,
    SkillUpdate,
)
from core.database import get_db  # noqa: E402
from core.skills_service import (  # noqa: E402
    list_skills_internal,
    get_categories_internal,
    get_skills_stats_internal,
    get_skill_internal,
    create_skill_internal,
    update_skill_internal,
    delete_skill_internal,
    search_skills_internal,
)

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillSummary(BaseModel):
    """Summary of a skill (without full content)."""

    id: str
    name: str
    description: str
    when_to_use: str
    category: str
    version: Optional[str] = None
    source: str
    has_checklist: bool = False
    tags: List[str] = []
    trigger_keywords: List[str] = []


class SkillDetail(BaseModel):
    """Full skill details including content."""

    id: str
    name: str
    description: str
    when_to_use: str
    category: str
    version: Optional[str] = None
    source: str
    path: str
    content: str
    has_checklist: bool = False
    tags: List[str] = []


class SkillsListResponse(BaseModel):
    """Response for listing skills."""

    skills: List[SkillSummary]
    count: int


class SkillStatsResponse(BaseModel):
    """Response for skill statistics."""

    total_skills: int
    by_source: dict
    by_category: dict
    with_checklist: int
    skill_roots: List[str]


# --- Read Operations ---


@router.get("", response_model=SkillsListResponse)
async def list_skills(
    source: Optional[str] = Query(
        None, description="Filter by source: user, vault, database"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    db: AsyncSession = Depends(get_db),
):
    """List all skills with optional filtering."""
    result = await list_skills_internal(
        db=db, source=source, category=category, search=search
    )
    # Convert internal models to Pydantic models
    skills = [SkillSummary(**skill.model_dump()) for skill in result.skills]
    return SkillsListResponse(skills=skills, count=result.count)


@router.get("/categories")
async def get_categories_with_counts(
    db: AsyncSession = Depends(get_db),
):
    """Get all categories with skill counts."""
    return await get_categories_internal(db=db)


@router.get("/stats", response_model=SkillStatsResponse)
async def get_skills_stats(db: AsyncSession = Depends(get_db)):
    """Get statistics about available skills."""
    result = await get_skills_stats_internal(db=db)
    return SkillStatsResponse(**result.model_dump())


@router.get("/{skill_id}", response_model=SkillDetail)
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_db)):
    """Get full skill details including content."""
    result = await get_skill_internal(db=db, skill_id=skill_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    return SkillDetail(**result.model_dump())


# --- Create/Update/Delete Operations ---


@router.post("", response_model=SkillDetail, status_code=201)
async def create_skill(
    skill: SkillCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user skill (stored in database)."""
    result = await create_skill_internal(db=db, skill=skill)
    return SkillDetail(**result.model_dump())


@router.patch("/{skill_id}", response_model=SkillDetail)
async def update_skill(
    skill_id: str,
    updates: SkillUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing skill (database or filesystem)."""
    result = await update_skill_internal(db=db, skill_id=skill_id, updates=updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    return SkillDetail(**result.model_dump())


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a skill (database skills only)."""
    try:
        deleted = await delete_skill_internal(db=db, skill_id=skill_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Skill not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search", response_model=SkillsListResponse)
async def search_skills(query: str, db: AsyncSession = Depends(get_db)):
    """Search skills by name, description, or when_to_use."""
    result = await search_skills_internal(db=db, query=query)
    skills = [SkillSummary(**skill.model_dump()) for skill in result.skills]
    return SkillsListResponse(skills=skills, count=result.count)

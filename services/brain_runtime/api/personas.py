"""Personas API endpoints for Phase 10 - Council & Persona System."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.skill_loader import load_skills_for_persona
from models.db_models import ModeDB

router = APIRouter(prefix="/personas", tags=["personas"])


# ============================================================================
# Pydantic Models
# ============================================================================


class PersonaResponse(BaseModel):
    """Response for a persona."""

    id: str
    name: str
    description: Optional[str]
    icon: str
    color: str
    system_prompt_addition: Optional[str]
    can_orchestrate: bool
    persona_config: dict
    sort_order: int
    is_system: bool


class PersonaSkillResponse(BaseModel):
    """Response for a persona's skill."""

    id: str
    name: str
    description: str
    when_to_use: str
    category: str
    tags: List[str] = []
    version: Optional[str] = None
    is_universal: bool  # True if persona_ids is NULL


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=List[PersonaResponse])
async def list_personas(db: AsyncSession = Depends(get_db)):
    """List all personas (modes where is_persona = true).

    Returns all available personas sorted by sort_order.
    Personas are special modes with distinct reasoning styles and exclusive skills.
    """
    result = await db.execute(
        select(ModeDB)
        .where(ModeDB.is_persona, ModeDB.deleted_at.is_(None))
        .order_by(ModeDB.sort_order)
    )
    personas = result.scalars().all()

    return [
        PersonaResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            icon=p.icon,
            color=p.color,
            system_prompt_addition=p.system_prompt_addition,
            can_orchestrate=getattr(p, 'can_orchestrate', True),  # Default to True for backwards compatibility
            persona_config=getattr(p, 'persona_config', {}) or {},  # Default to empty dict
            sort_order=p.sort_order,
            is_system=p.is_system,
        )
        for p in personas
    ]


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific persona by ID.

    Args:
        persona_id: UUID of the persona

    Returns:
        Persona details

    Raises:
        404: If persona not found
    """
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.id == persona_id,
            ModeDB.is_persona,
            ModeDB.deleted_at.is_(None)
        )
    )
    persona = result.scalar_one_or_none()

    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")

    return PersonaResponse(
        id=str(persona.id),
        name=persona.name,
        description=persona.description,
        icon=persona.icon,
        color=persona.color,
        system_prompt_addition=persona.system_prompt_addition,
        can_orchestrate=getattr(persona, 'can_orchestrate', True),
        persona_config=getattr(persona, 'persona_config', {}) or {},
        sort_order=persona.sort_order,
        is_system=persona.is_system,
    )


@router.get("/{persona_id}/skills", response_model=List[PersonaSkillResponse])
async def get_persona_skills(persona_id: str, db: AsyncSession = Depends(get_db)):
    """Get skills available to a specific persona.

    Returns both:
    - Universal skills (persona_ids is NULL)
    - Skills explicitly assigned to this persona

    Args:
        persona_id: UUID of the persona

    Returns:
        List of skills available to this persona

    Raises:
        404: If persona not found
    """
    # Verify persona exists
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.id == persona_id,
            ModeDB.is_persona,
            ModeDB.deleted_at.is_(None)
        )
    )
    persona = result.scalar_one_or_none()

    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")

    # Load skills for this persona
    skills = await load_skills_for_persona(persona_id, db)

    return [
        PersonaSkillResponse(
            id=str(s.id),
            name=s.name,
            description=s.description,
            when_to_use=s.when_to_use,
            category=s.category,
            tags=s.tags or [],
            version=s.version,
            is_universal=(s.persona_ids is None or len(s.persona_ids) == 0) if hasattr(s, 'persona_ids') else True,
        )
        for s in skills
    ]

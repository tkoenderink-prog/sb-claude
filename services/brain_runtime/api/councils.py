"""Councils API endpoints for Phase 10 - Council & Persona System."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.council import get_skill_by_name
from models.db_models import UserSkillDB

router = APIRouter(prefix="/councils", tags=["councils"])


# ============================================================================
# Pydantic Models
# ============================================================================


class CouncilResponse(BaseModel):
    """Response for a council skill."""

    id: str
    name: str
    description: str
    when_to_use: str
    category: str
    tags: List[str] = []
    version: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=List[CouncilResponse])
async def list_councils(db: AsyncSession = Depends(get_db)):
    """List all council skills.

    Councils are special skills with category='council' that define:
    - Which personas to convene
    - How to structure the consultation
    - How to synthesize responses

    Returns all available council configurations.
    """
    result = await db.execute(
        select(UserSkillDB)
        .where(UserSkillDB.category == "council", UserSkillDB.deleted_at.is_(None))
        .order_by(UserSkillDB.name)
    )
    councils = result.scalars().all()

    return [
        CouncilResponse(
            id=str(c.id),
            name=c.name,
            description=c.description,
            when_to_use=c.when_to_use,
            category=c.category,
            tags=c.tags or [],
            version=c.version,
        )
        for c in councils
    ]


@router.get("/{council_name}", response_model=CouncilResponse)
async def get_council(council_name: str, db: AsyncSession = Depends(get_db)):
    """Get a specific council by name.

    Args:
        council_name: Name of the council (e.g., "Decision Council")

    Returns:
        Council details

    Raises:
        404: If council not found
    """
    council = await get_skill_by_name(council_name, db)

    if not council:
        raise HTTPException(status_code=404, detail=f"Council not found: {council_name}")

    if council.category != "council":
        raise HTTPException(
            status_code=400,
            detail=f"Skill '{council_name}' is not a council (category: {council.category})"
        )

    return CouncilResponse(
        id=str(council.id),
        name=council.name,
        description=council.description,
        when_to_use=council.when_to_use,
        category=council.category,
        tags=council.tags or [],
        version=council.version,
    )

"""Council helper functions for multi-persona consultations."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import ModeDB, UserSkillDB


async def get_persona_by_id(persona_id: str, db: AsyncSession) -> Optional[ModeDB]:
    """Get a persona by ID."""
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.id == persona_id,
            ModeDB.is_persona.is_(True),
            ModeDB.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def get_persona_by_name(persona_name: str, db: AsyncSession) -> Optional[ModeDB]:
    """Get a persona by name."""
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.name.ilike(persona_name),
            ModeDB.is_persona.is_(True),
            ModeDB.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def get_skill_by_name(skill_name: str, db: AsyncSession) -> Optional[UserSkillDB]:
    """Get a skill by name."""
    result = await db.execute(
        select(UserSkillDB).where(
            UserSkillDB.name.ilike(skill_name),
            UserSkillDB.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def get_all_personas(db: AsyncSession) -> List[ModeDB]:
    """Get all personas from database."""
    result = await db.execute(
        select(ModeDB)
        .where(ModeDB.is_persona.is_(True), ModeDB.deleted_at.is_(None))
        .order_by(ModeDB.name)
    )
    return list(result.scalars().all())


async def get_council_skill_by_name(council_name: str, db: AsyncSession) -> Optional[UserSkillDB]:
    """Get a council skill by name."""
    result = await db.execute(
        select(UserSkillDB).where(
            UserSkillDB.name.ilike(council_name),
            UserSkillDB.category == "council",
            UserSkillDB.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()

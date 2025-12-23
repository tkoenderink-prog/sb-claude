"""Persona skill loading and system prompt building."""

from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import UserSkillDB, ModeDB


async def load_skills_for_persona(
    persona_id: str,
    db: AsyncSession,
    categories: Optional[List[str]] = None,
) -> List[UserSkillDB]:
    """Load skills available to a specific persona.

    Returns:
        - Skills explicitly assigned to this persona (persona_ids contains persona_id)
        - Universal skills (persona_ids is NULL)

    Args:
        persona_id: UUID of the persona
        db: Database session
        categories: Optional list of categories to filter by
    """
    query = select(UserSkillDB).where(
        UserSkillDB.deleted_at.is_(None),
        or_(
            UserSkillDB.persona_ids.is_(None),  # Universal skills
            UserSkillDB.persona_ids.contains([persona_id])  # Persona-specific
        )
    )

    if categories:
        query = query.where(UserSkillDB.category.in_(categories))

    query = query.order_by(UserSkillDB.name)

    result = await db.execute(query)
    return list(result.scalars().all())


def build_persona_system_prompt(
    base_prompt: str,
    persona: ModeDB,
    skills: List[UserSkillDB],
) -> str:
    """Build complete system prompt for a persona.

    Combines:
    1. Base system prompt (user-customized or default)
    2. Persona's system_prompt_addition
    3. Available skills metadata (Level 1 disclosure)

    Args:
        base_prompt: Base system prompt (user-customized or default)
        persona: Persona mode from database
        skills: List of skills available to this persona

    Returns:
        Complete system prompt string
    """
    parts = [base_prompt]

    # Add persona identity
    if persona.system_prompt_addition:
        parts.append(f"\n\n## Your Persona: {persona.name}\n\n{persona.system_prompt_addition}")

    # Add available skills (metadata only, full content loaded on demand)
    if skills:
        skill_list = "\n".join([
            f"- **{s.name}**: {s.description} (use when: {s.when_to_use})"
            for s in skills
        ])
        parts.append(f"\n\n## Available Skills\n\n{skill_list}")

    return "\n".join(parts)

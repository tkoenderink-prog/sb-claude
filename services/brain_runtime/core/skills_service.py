"""Internal skills service - business logic without FastAPI dependencies."""

import sys
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

# Add services to path
services_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(services_path))

from skills.scanner import SkillScanner  # noqa: E402
from skills.models import SkillCreate, SkillUpdate, SkillCategory  # noqa: E402
from models.db_models import UserSkillDB  # noqa: E402

# Default skill roots
DEFAULT_SKILL_ROOTS = [
    "~/.claude/skills",
]


class SkillSummary:
    """Summary of a skill (without full content)."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        when_to_use: str,
        category: str,
        version: Optional[str] = None,
        source: str = "",
        has_checklist: bool = False,
        tags: List[str] = None,
        trigger_keywords: List[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.when_to_use = when_to_use
        self.category = category
        self.version = version
        self.source = source
        self.has_checklist = has_checklist
        self.tags = tags or []
        self.trigger_keywords = trigger_keywords or []

    def model_dump(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "category": self.category,
            "version": self.version,
            "source": self.source,
            "has_checklist": self.has_checklist,
            "tags": self.tags,
            "trigger_keywords": self.trigger_keywords,
        }


class SkillDetail:
    """Full skill details including content."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        when_to_use: str,
        category: str,
        version: Optional[str] = None,
        source: str = "",
        path: str = "",
        content: str = "",
        has_checklist: bool = False,
        tags: List[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.when_to_use = when_to_use
        self.category = category
        self.version = version
        self.source = source
        self.path = path
        self.content = content
        self.has_checklist = has_checklist
        self.tags = tags or []

    def model_dump(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "category": self.category,
            "version": self.version,
            "source": self.source,
            "path": self.path,
            "content": self.content,
            "has_checklist": self.has_checklist,
            "tags": self.tags,
        }


class SkillsListResponse:
    """Response for listing skills."""

    def __init__(self, skills: List[SkillSummary], count: int):
        self.skills = skills
        self.count = count


class SkillStatsResponse:
    """Response for skill statistics."""

    def __init__(
        self,
        total_skills: int,
        by_source: dict,
        by_category: dict,
        with_checklist: int,
        skill_roots: List[str],
    ):
        self.total_skills = total_skills
        self.by_source = by_source
        self.by_category = by_category
        self.with_checklist = with_checklist
        self.skill_roots = skill_roots

    def model_dump(self):
        return {
            "total_skills": self.total_skills,
            "by_source": self.by_source,
            "by_category": self.by_category,
            "with_checklist": self.with_checklist,
            "skill_roots": self.skill_roots,
        }


def _get_scanner() -> SkillScanner:
    """Get skill scanner instance."""
    return SkillScanner(skill_roots=DEFAULT_SKILL_ROOTS)


# --- Internal Service Functions ---


async def list_skills_internal(
    db: AsyncSession,
    source: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> SkillsListResponse:
    """List all skills with optional filtering.

    Args:
        db: Database session
        source: Filter by source (user, vault, database) or None for all
        category: Filter by category or None for all
        search: Search in name/description or None for no search

    Returns:
        SkillsListResponse with filtered skills
    """
    skills = []

    # 1. Filesystem skills (user + vault)
    if source is None or source in ("user", "vault"):
        scanner = _get_scanner()

        if search:
            fs_skills = scanner.search(search)
        else:
            fs_skills = scanner.scan_all(include_content=False)

        for skill in fs_skills:
            if source and skill.source != source:
                continue
            if category and skill.category.value != category:
                continue
            skills.append(
                SkillSummary(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                    when_to_use=skill.when_to_use,
                    category=skill.category.value,
                    version=skill.version,
                    source=skill.source,
                    has_checklist=skill.has_checklist,
                    tags=skill.tags,
                    trigger_keywords=skill.trigger_keywords,
                )
            )

    # 2. Database skills
    if source is None or source == "database":
        query = select(UserSkillDB).where(UserSkillDB.deleted_at.is_(None))

        if category:
            query = query.where(UserSkillDB.category == category)

        result = await db.execute(query)
        db_skills = result.scalars().all()

        for db_skill in db_skills:
            skill_name = db_skill.name.lower()
            skill_desc = db_skill.description.lower()
            if search and search.lower() not in f"{skill_name} {skill_desc}":
                continue
            skills.append(
                SkillSummary(
                    id=f"db_{db_skill.id}",
                    name=db_skill.name,
                    description=db_skill.description,
                    when_to_use=db_skill.when_to_use,
                    category=db_skill.category,
                    version=db_skill.version,
                    source="database",
                    has_checklist="[ ]" in (db_skill.content or ""),
                    tags=db_skill.tags or [],
                    trigger_keywords=[],
                )
            )

    return SkillsListResponse(skills=skills, count=len(skills))


async def get_categories_internal(db: AsyncSession) -> dict:
    """Get all categories with skill counts.

    Args:
        db: Database session

    Returns:
        Dictionary mapping category names to counts
    """
    scanner = _get_scanner()
    fs_skills = scanner.scan_all()

    counts = {cat.value: 0 for cat in SkillCategory}

    # Count filesystem skills
    for skill in fs_skills:
        counts[skill.category.value] += 1

    # Count database skills
    result = await db.execute(
        select(UserSkillDB.category, func.count(UserSkillDB.id))
        .where(UserSkillDB.deleted_at.is_(None))
        .group_by(UserSkillDB.category)
    )
    for category, count in result.all():
        counts[category] = counts.get(category, 0) + count

    return counts


async def get_skills_stats_internal(db: AsyncSession) -> SkillStatsResponse:
    """Get statistics about available skills.

    Args:
        db: Database session

    Returns:
        SkillStatsResponse with statistics
    """
    scanner = _get_scanner()
    stats = scanner.get_stats()

    # Add database skills count
    result = await db.execute(
        select(func.count(UserSkillDB.id)).where(UserSkillDB.deleted_at.is_(None))
    )
    db_count = result.scalar_one()

    if db_count > 0:
        stats["by_source"]["database"] = db_count
        stats["total_skills"] += db_count

    return SkillStatsResponse(**stats)


async def get_skill_internal(db: AsyncSession, skill_id: str) -> Optional[SkillDetail]:
    """Get full skill details including content.

    Args:
        db: Database session
        skill_id: Skill identifier

    Returns:
        SkillDetail or None if not found
    """
    # Check if database skill
    if skill_id.startswith("db_"):
        db_id = skill_id[3:]
        result = await db.execute(
            select(UserSkillDB)
            .where(UserSkillDB.id == UUID(db_id))
            .where(UserSkillDB.deleted_at.is_(None))
        )
        db_skill = result.scalar_one_or_none()

        if not db_skill:
            return None

        return SkillDetail(
            id=skill_id,
            name=db_skill.name,
            description=db_skill.description,
            when_to_use=db_skill.when_to_use,
            category=db_skill.category,
            version=db_skill.version,
            source="database",
            has_checklist="[ ]" in (db_skill.content or ""),
            tags=db_skill.tags or [],
            path="",  # Database skills have no path
            content=db_skill.content,
        )

    # Filesystem skill
    scanner = _get_scanner()
    skill = scanner.get_skill(skill_id)

    if not skill:
        return None

    return SkillDetail(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        when_to_use=skill.when_to_use,
        category=skill.category.value,
        version=skill.version,
        source=skill.source,
        path=skill.path,
        content=skill.content or "",
        has_checklist=skill.has_checklist,
        tags=skill.tags,
    )


async def create_skill_internal(
    db: AsyncSession, skill: SkillCreate
) -> SkillDetail:
    """Create a new user skill (stored in database).

    Args:
        db: Database session
        skill: Skill data to create

    Returns:
        Created SkillDetail
    """
    db_skill = UserSkillDB(
        id=uuid4(),
        name=skill.name,
        description=skill.description,
        when_to_use=skill.when_to_use,
        category=skill.category.value,
        tags=skill.tags,
        content=skill.content,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_skill)
    await db.commit()
    await db.refresh(db_skill)

    return SkillDetail(
        id=f"db_{db_skill.id}",
        name=db_skill.name,
        description=db_skill.description,
        when_to_use=db_skill.when_to_use,
        category=db_skill.category,
        version=db_skill.version,
        source="database",
        has_checklist="[ ]" in (db_skill.content or ""),
        tags=db_skill.tags or [],
        path="",
        content=db_skill.content,
    )


async def update_skill_internal(
    db: AsyncSession, skill_id: str, updates: SkillUpdate
) -> Optional[SkillDetail]:
    """Update an existing skill (database or filesystem).

    Args:
        db: Database session
        skill_id: Skill identifier
        updates: Updates to apply

    Returns:
        Updated SkillDetail or None if not found
    """
    # Database skill
    if skill_id.startswith("db_"):
        db_id = skill_id[3:]
        result = await db.execute(
            select(UserSkillDB)
            .where(UserSkillDB.id == UUID(db_id))
            .where(UserSkillDB.deleted_at.is_(None))
        )
        db_skill = result.scalar_one_or_none()

        if not db_skill:
            return None

        # Apply updates
        if updates.name is not None:
            db_skill.name = updates.name
        if updates.description is not None:
            db_skill.description = updates.description
        if updates.when_to_use is not None:
            db_skill.when_to_use = updates.when_to_use
        if updates.category is not None:
            db_skill.category = updates.category.value
        if updates.tags is not None:
            db_skill.tags = updates.tags
        if updates.content is not None:
            db_skill.content = updates.content

        db_skill.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(db_skill)

        return SkillDetail(
            id=skill_id,
            name=db_skill.name,
            description=db_skill.description,
            when_to_use=db_skill.when_to_use,
            category=db_skill.category,
            version=db_skill.version,
            source="database",
            has_checklist="[ ]" in (db_skill.content or ""),
            tags=db_skill.tags or [],
            path="",
            content=db_skill.content,
        )

    # Filesystem skill
    scanner = _get_scanner()
    updated_skill = scanner.update_skill(
        skill_id=skill_id,
        name=updates.name,
        description=updates.description,
        when_to_use=updates.when_to_use,
        category=updates.category.value if updates.category else None,
        tags=updates.tags,
        content=updates.content,
    )

    if not updated_skill:
        return None

    return SkillDetail(
        id=updated_skill.id,
        name=updated_skill.name,
        description=updated_skill.description,
        when_to_use=updated_skill.when_to_use,
        category=updated_skill.category.value,
        version=updated_skill.version,
        source=updated_skill.source,
        path=updated_skill.path,
        content=updated_skill.content or "",
        has_checklist=updated_skill.has_checklist,
        tags=updated_skill.tags,
    )


async def delete_skill_internal(db: AsyncSession, skill_id: str) -> bool:
    """Soft delete a skill (database skills only).

    Args:
        db: Database session
        skill_id: Skill identifier (must start with 'db_')

    Returns:
        True if deleted, False if not found or invalid

    Raises:
        ValueError: If skill_id doesn't start with 'db_'
    """
    if not skill_id.startswith("db_"):
        raise ValueError(
            "Only database skills can be deleted via API. "
            "Filesystem skills must be deleted directly."
        )

    db_id = skill_id[3:]
    result = await db.execute(
        update(UserSkillDB)
        .where(UserSkillDB.id == UUID(db_id))
        .where(UserSkillDB.deleted_at.is_(None))
        .values(deleted_at=datetime.now(timezone.utc))
        .returning(UserSkillDB.id)
    )

    deleted = result.scalar_one_or_none() is not None
    if deleted:
        await db.commit()

    return deleted


async def search_skills_internal(
    db: AsyncSession, query: str
) -> SkillsListResponse:
    """Search skills by name, description, or when_to_use.

    Args:
        db: Database session
        query: Search query string

    Returns:
        SkillsListResponse with matching skills
    """
    scanner = _get_scanner()
    fs_skills = scanner.search(query)

    summaries = [
        SkillSummary(
            id=s.id,
            name=s.name,
            description=s.description,
            when_to_use=s.when_to_use,
            category=s.category.value,
            version=s.version,
            source=s.source,
            has_checklist=s.has_checklist,
            tags=s.tags,
            trigger_keywords=s.trigger_keywords,
        )
        for s in fs_skills
    ]

    # Also search database skills
    query_lower = query.lower()
    result = await db.execute(
        select(UserSkillDB).where(UserSkillDB.deleted_at.is_(None))
    )
    db_skills = result.scalars().all()

    for db_skill in db_skills:
        searchable = f"{db_skill.name} {db_skill.description} {db_skill.when_to_use}"
        if query_lower in searchable.lower():
            summaries.append(
                SkillSummary(
                    id=f"db_{db_skill.id}",
                    name=db_skill.name,
                    description=db_skill.description,
                    when_to_use=db_skill.when_to_use,
                    category=db_skill.category,
                    version=db_skill.version,
                    source="database",
                    has_checklist="[ ]" in (db_skill.content or ""),
                    tags=db_skill.tags or [],
                    trigger_keywords=[],
                )
            )

    return SkillsListResponse(skills=summaries, count=len(summaries))

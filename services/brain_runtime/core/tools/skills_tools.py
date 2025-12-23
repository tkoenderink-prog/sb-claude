"""Skills tools wrapping the /skills API."""

from typing import Optional
import logging

from .registry import tool

logger = logging.getLogger(__name__)


@tool(
    name="list_skills",
    description="List all available skills (thinking frameworks, workflows, procedures). Can filter by source (user, vault, database) or category.",
    parameters={
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "enum": ["user", "vault", "database"],
                "description": "Filter by source location",
            },
            "category": {
                "type": "string",
                "description": "Filter by category (e.g., 'knowledge', 'workflow', 'analysis')",
            }
        },
        "required": [],
    },
)
async def list_skills(source: Optional[str] = None, category: Optional[str] = None):
    """List all available skills."""
    from core.skills_service import list_skills_internal
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        result = await list_skills_internal(
            db=db, source=source, category=category, search=None
        )
        return {
            "skills": [skill.model_dump() for skill in result.skills],
            "count": result.count,
        }


@tool(
    name="get_skill",
    description="Get full details of a specific skill by ID, including complete content.",
    parameters={
        "type": "object",
        "properties": {
            "skill_id": {
                "type": "string",
                "description": "Unique skill identifier (e.g., 'solving-with-frameworks')",
            }
        },
        "required": ["skill_id"],
    },
)
async def get_skill(skill_id: str):
    """Get a specific skill by ID."""
    from core.skills_service import get_skill_internal
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        result = await get_skill_internal(db=db, skill_id=skill_id)
        if not result:
            return {"error": f"Skill not found: {skill_id}"}
        return result.model_dump()


@tool(
    name="search_skills",
    description="Search skills by name, description, or when_to_use text. Useful for finding relevant frameworks.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to match against skill metadata",
            }
        },
        "required": ["query"],
    },
)
async def search_skills(query: str):
    """Search skills by query."""
    from core.skills_service import search_skills_internal
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        result = await search_skills_internal(db=db, query=query)
        return {
            "query": query,
            "skills": [skill.model_dump() for skill in result.skills],
            "count": result.count,
        }


@tool(
    name="get_skills_stats",
    description="Get statistics about available skills (total count, breakdown by source, etc.).",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_skills_stats():
    """Get skills statistics."""
    from core.skills_service import get_skills_stats_internal
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        result = await get_skills_stats_internal(db=db)
        return result.model_dump()


@tool(
    name="create_skill",
    description="Create a new skill (stored in database). Skills are reusable thinking frameworks, workflows, or procedures.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Human-readable skill name (e.g., 'Quick Recognition')",
            },
            "description": {
                "type": "string",
                "description": "Brief description of what the skill does",
            },
            "when_to_use": {
                "type": "string",
                "description": "When this skill should be triggered/used",
            },
            "category": {
                "type": "string",
                "enum": ["knowledge", "workflow", "analysis", "creation", "integration", "training", "productivity"],
                "description": "Skill category",
            },
            "content": {
                "type": "string",
                "description": "Full skill content/instructions in markdown format",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for categorization",
            },
        },
        "required": ["name", "description", "when_to_use", "category", "content"],
    },
)
async def create_skill(
    name: str,
    description: str,
    when_to_use: str,
    category: str,
    content: str,
    tags: Optional[list] = None,
):
    """Create a new skill in the database."""
    from core.skills_service import create_skill_internal
    from skills.models import SkillCreate, SkillCategory
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        skill_data = SkillCreate(
            name=name,
            description=description,
            when_to_use=when_to_use,
            category=SkillCategory(category),
            content=content,
            tags=tags or [],
        )
        result = await create_skill_internal(db=db, skill=skill_data)
        return {
            "success": True,
            "skill": result.model_dump(),
            "message": f"Skill '{name}' created successfully",
        }


@tool(
    name="update_skill",
    description="Update an existing skill. Can update any field. Only database skills (id starts with 'db_') can be updated via this tool.",
    parameters={
        "type": "object",
        "properties": {
            "skill_id": {
                "type": "string",
                "description": "Skill ID to update (e.g., 'db_abc123...')",
            },
            "name": {
                "type": "string",
                "description": "New name (optional)",
            },
            "description": {
                "type": "string",
                "description": "New description (optional)",
            },
            "when_to_use": {
                "type": "string",
                "description": "New when_to_use text (optional)",
            },
            "category": {
                "type": "string",
                "enum": ["knowledge", "workflow", "analysis", "creation", "integration", "training", "productivity"],
                "description": "New category (optional)",
            },
            "content": {
                "type": "string",
                "description": "New content (optional)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "New tags (optional)",
            },
        },
        "required": ["skill_id"],
    },
)
async def update_skill(
    skill_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    when_to_use: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[list] = None,
):
    """Update an existing skill."""
    from core.skills_service import update_skill_internal
    from skills.models import SkillUpdate, SkillCategory
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        updates = SkillUpdate(
            name=name,
            description=description,
            when_to_use=when_to_use,
            category=SkillCategory(category) if category else None,
            content=content,
            tags=tags,
        )
        result = await update_skill_internal(db=db, skill_id=skill_id, updates=updates)
        if not result:
            return {"success": False, "error": f"Skill not found: {skill_id}"}
        return {
            "success": True,
            "skill": result.model_dump(),
            "message": f"Skill '{result.name}' updated successfully",
        }


@tool(
    name="delete_skill",
    description="Delete a skill (soft delete). Only database skills can be deleted via this tool.",
    parameters={
        "type": "object",
        "properties": {
            "skill_id": {
                "type": "string",
                "description": "Skill ID to delete (must start with 'db_')",
            },
        },
        "required": ["skill_id"],
    },
)
async def delete_skill(skill_id: str):
    """Delete a skill from the database."""
    from core.skills_service import delete_skill_internal
    from core.database import get_session_factory

    if not skill_id.startswith("db_"):
        return {
            "success": False,
            "error": "Only database skills (id starting with 'db_') can be deleted via this tool",
        }

    async with get_session_factory()() as db:
        try:
            deleted = await delete_skill_internal(db=db, skill_id=skill_id)
            if not deleted:
                return {"success": False, "error": f"Skill not found: {skill_id}"}
            return {
                "success": True,
                "message": f"Skill '{skill_id}' deleted successfully",
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}


def register_skills_tools():
    """Register all skills tools (called by decorator)."""
    # Tools are auto-registered by the @tool decorator
    logger.info("Skills tools registered")

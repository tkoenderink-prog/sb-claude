"""Test to verify the skills service fix for Query() object leak bug.

This test ensures that the internal service functions can be called directly
from tools without FastAPI's Query() default resolution causing issues.

Bug: When skills_tools.py called api/skills.py functions directly (not via HTTP),
FastAPI's Query() defaults were not resolved, causing Query(None) objects to leak
into SQLAlchemy queries, resulting in: "invalid input for query argument $1: Query(None)"

Fix: Created core/skills_service.py with internal service functions that have no
FastAPI dependencies, allowing both HTTP routes and tools to use the same logic.
"""

import asyncio
from core.skills_service import (
    list_skills_internal,
    search_skills_internal,
    get_skills_stats_internal,
)
from core.database import get_session_factory


async def test_list_skills_with_none_parameters():
    """Test that list_skills_internal works with None parameters (no Query() leak)."""
    async with get_session_factory()() as db:
        result = await list_skills_internal(
            db=db, source=None, category=None, search=None
        )
        assert result.count > 0
        assert len(result.skills) == result.count


async def test_list_skills_with_category_filter():
    """Test that category filtering works correctly."""
    async with get_session_factory()() as db:
        result = await list_skills_internal(
            db=db, source=None, category="workflow", search=None
        )
        # All returned skills should have category "workflow"
        for skill in result.skills:
            assert skill.category == "workflow"


async def test_list_skills_with_source_filter():
    """Test that source filtering works correctly."""
    async with get_session_factory()() as db:
        result = await list_skills_internal(
            db=db, source="user", category=None, search=None
        )
        # All returned skills should have source "user" or "vault"
        for skill in result.skills:
            assert skill.source in ("user", "vault")


async def test_search_skills():
    """Test that search works correctly."""
    async with get_session_factory()() as db:
        result = await search_skills_internal(db=db, query="workflow")
        assert result.count > 0


async def test_get_skills_stats():
    """Test that stats endpoint works correctly."""
    async with get_session_factory()() as db:
        result = await get_skills_stats_internal(db=db)
        assert result.total_skills > 0
        assert "user" in result.by_source or "vault" in result.by_source


async def test_tool_function_integration():
    """Test that tool functions can call internal service functions successfully."""
    from core.tools.skills_tools import list_skills

    # This was the failing case - tool function calling with default None values
    result = await list_skills()
    assert result["count"] > 0
    assert len(result["skills"]) == result["count"]

    # Test with filters
    result2 = await list_skills(category="workflow")
    assert result2["count"] > 0


if __name__ == "__main__":
    # Run tests standalone
    async def run_tests():
        print("Testing skills service fix...")
        await test_list_skills_with_none_parameters()
        print("✓ list_skills with None parameters works")

        await test_list_skills_with_category_filter()
        print("✓ category filtering works")

        await test_list_skills_with_source_filter()
        print("✓ source filtering works")

        await test_search_skills()
        print("✓ search works")

        await test_get_skills_stats()
        print("✓ stats works")

        await test_tool_function_integration()
        print("✓ tool integration works")

        print("\nAll tests passed! ✅")

    asyncio.run(run_tests())

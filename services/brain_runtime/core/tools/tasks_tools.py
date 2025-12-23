"""Tasks tools wrapping the /tasks API."""

from datetime import date
from typing import Optional
import logging

from .registry import tool

logger = logging.getLogger(__name__)


@tool(
    name="get_overdue_tasks",
    description="Get tasks that are overdue (due date before today, not done or cancelled). Sorted by due date (oldest first).",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_overdue_tasks():
    """Get overdue tasks."""
    from api.tasks import get_tasks_overdue

    result = await get_tasks_overdue()
    return {
        "tasks": [task.model_dump() for task in result.tasks],
        "count": result.count,
        "query_date": result.query_date.isoformat(),
    }


@tool(
    name="get_today_tasks",
    description="Get tasks due today that are not done or cancelled.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_today_tasks():
    """Get tasks due today."""
    from api.tasks import get_tasks_today

    result = await get_tasks_today()
    return {
        "tasks": [task.model_dump() for task in result.tasks],
        "count": result.count,
        "query_date": result.query_date.isoformat(),
    }


@tool(
    name="get_week_tasks",
    description="Get tasks due in the next 7 days (including today) that are not done or cancelled. Sorted by due date.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_week_tasks():
    """Get tasks due in the next 7 days."""
    from api.tasks import get_tasks_week

    result = await get_tasks_week()
    return {
        "tasks": [task.model_dump() for task in result.tasks],
        "count": result.count,
        "query_date": result.query_date.isoformat(),
    }


@tool(
    name="query_tasks",
    description="Query tasks with flexible filters. Can filter by status, priority, tags, project, and due dates.",
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["todo", "done", "in_progress", "cancelled"],
                "description": "Filter by task status",
            },
            "priority": {
                "type": "string",
                "enum": ["highest", "high", "medium", "low"],
                "description": "Filter by task priority",
            },
            "tag": {
                "type": "string",
                "description": "Filter by tag (include # symbol, e.g., '#work')",
            },
            "project": {
                "type": "string",
                "description": "Filter by project name (matches file path)",
            },
            "due_before": {
                "type": "string",
                "description": "Tasks due before this date (ISO format, e.g., '2025-12-31')",
            },
            "due_after": {
                "type": "string",
                "description": "Tasks due after this date (ISO format, e.g., '2025-12-01')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of tasks to return (default: 100, max: 500)",
                "default": 100,
            },
        },
        "required": [],
    },
)
async def query_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    project: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    limit: int = 100,
):
    """Query tasks with filters."""
    from api.tasks import query_tasks as api_query_tasks

    # Convert date strings to date objects
    due_before_date = date.fromisoformat(due_before) if due_before else None
    due_after_date = date.fromisoformat(due_after) if due_after else None

    result = await api_query_tasks(
        status=status,
        priority=priority,
        tag=tag,
        project=project,
        due_before=due_before_date,
        due_after=due_after_date,
        limit=limit,
    )

    return {
        "tasks": [task.model_dump() for task in result.tasks],
        "count": result.count,
        "query_date": result.query_date.isoformat(),
    }


@tool(
    name="get_tasks_by_project",
    description="Get tasks grouped by project folder. Shows up to 10 tasks per project.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_tasks_by_project():
    """Get tasks grouped by project."""
    from api.tasks import get_tasks_by_project as api_get_tasks_by_project

    result = await api_get_tasks_by_project()
    return result


def register_tasks_tools():
    """Register all tasks tools (called by decorator)."""
    # Tools are auto-registered by the @tool decorator
    logger.info("Tasks tools registered")

"""Tasks query endpoints."""

from datetime import date, timedelta
from pathlib import Path
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import json


router = APIRouter(prefix="/tasks", tags=["tasks"])

# Path to tasks export
app_root = Path(__file__).parent.parent.parent.parent
exports_path = app_root / "exports" / "normalized" / "tasks_v1.json"


class TaskSummary(BaseModel):
    """Summary of a task."""

    task_id: str
    text_clean: str
    status: str
    due_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    priority: Optional[str] = None
    tags: list[str] = []
    file_path: str
    obsidian_uri: Optional[str] = None


class TasksResponse(BaseModel):
    """Response containing tasks."""

    tasks: list[TaskSummary]
    count: int
    query_date: date


class TaskStats(BaseModel):
    """Task statistics."""

    total_tasks: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    with_due_date: int
    overdue: int


class TasksStatusResponse(BaseModel):
    """Status of tasks data."""

    available: bool
    last_updated: Optional[str] = None
    task_count: int
    stats: Optional[TaskStats] = None


def _load_tasks() -> tuple[list[dict], dict]:
    """Load tasks from JSON export."""
    if not exports_path.exists():
        return [], {}

    data = json.loads(exports_path.read_text())
    return data.get("tasks", []), data.get("stats", {})


def _filter_tasks(
    tasks: list[dict],
    status: Optional[str] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
    due_on: Optional[date] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    project: Optional[str] = None,
) -> list[dict]:
    """Filter tasks by criteria."""
    result = []

    for task in tasks:
        # Status filter
        if status and task.get("status") != status:
            continue

        # Due date filters
        due_str = task.get("due_date")
        task_due = date.fromisoformat(due_str) if due_str else None

        if due_on and task_due != due_on:
            continue
        if due_before and (not task_due or task_due >= due_before):
            continue
        if due_after and (not task_due or task_due <= due_after):
            continue

        # Priority filter
        if priority and task.get("priority") != priority:
            continue

        # Tag filter
        if tag and tag not in task.get("tags", []):
            continue

        # Project filter (match in file path)
        if project:
            file_path = task.get("file_path", "").lower()
            if project.lower() not in file_path:
                continue

        result.append(task)

    return result


def _task_to_summary(task: dict) -> TaskSummary:
    """Convert task dict to TaskSummary."""
    return TaskSummary(
        task_id=task["task_id"],
        text_clean=task["text_clean"],
        status=task["status"],
        due_date=date.fromisoformat(task["due_date"]) if task.get("due_date") else None,
        scheduled_date=date.fromisoformat(task["scheduled_date"])
        if task.get("scheduled_date")
        else None,
        priority=task.get("priority"),
        tags=task.get("tags", []),
        file_path=task["file_path"],
        obsidian_uri=task.get("obsidian_uri"),
    )


@router.get("/status", response_model=TasksStatusResponse)
async def get_tasks_status():
    """Get status of tasks data."""
    if not exports_path.exists():
        return TasksStatusResponse(
            available=False,
            task_count=0,
        )

    data = json.loads(exports_path.read_text())
    stats_data = data.get("stats", {})

    return TasksStatusResponse(
        available=True,
        last_updated=data.get("generated_at"),
        task_count=stats_data.get("total_tasks", 0),
        stats=TaskStats(
            total_tasks=stats_data.get("total_tasks", 0),
            by_status=stats_data.get("by_status", {}),
            by_priority=stats_data.get("by_priority", {}),
            with_due_date=stats_data.get("with_due_date", 0),
            overdue=stats_data.get("overdue", 0),
        )
        if stats_data
        else None,
    )


@router.get("/today", response_model=TasksResponse)
async def get_tasks_today():
    """Get tasks due today."""
    tasks, _ = _load_tasks()
    today = date.today()

    # Filter for due today AND not done/cancelled
    filtered = []
    for task in tasks:
        if task.get("status") in ("done", "cancelled"):
            continue
        due_str = task.get("due_date")
        if due_str and date.fromisoformat(due_str) == today:
            filtered.append(task)

    return TasksResponse(
        tasks=[_task_to_summary(t) for t in filtered],
        count=len(filtered),
        query_date=today,
    )


@router.get("/overdue", response_model=TasksResponse)
async def get_tasks_overdue():
    """Get overdue tasks (due before today, not done/cancelled)."""
    tasks, _ = _load_tasks()
    today = date.today()

    filtered = []
    for task in tasks:
        if task.get("status") in ("done", "cancelled"):
            continue
        due_str = task.get("due_date")
        if due_str and date.fromisoformat(due_str) < today:
            filtered.append(task)

    # Sort by due date (oldest first)
    filtered.sort(key=lambda t: t.get("due_date", "9999-12-31"))

    return TasksResponse(
        tasks=[_task_to_summary(t) for t in filtered],
        count=len(filtered),
        query_date=today,
    )


@router.get("/week", response_model=TasksResponse)
async def get_tasks_week():
    """Get tasks due in the next 7 days (including today)."""
    tasks, _ = _load_tasks()
    today = date.today()
    week_end = today + timedelta(days=7)

    filtered = []
    for task in tasks:
        if task.get("status") in ("done", "cancelled"):
            continue
        due_str = task.get("due_date")
        if due_str:
            due = date.fromisoformat(due_str)
            if today <= due <= week_end:
                filtered.append(task)

    # Sort by due date
    filtered.sort(key=lambda t: t.get("due_date", "9999-12-31"))

    return TasksResponse(
        tasks=[_task_to_summary(t) for t in filtered],
        count=len(filtered),
        query_date=today,
    )


@router.get("/query", response_model=TasksResponse)
async def query_tasks(
    status: Optional[str] = Query(
        None, description="Filter by status: todo, done, in_progress, cancelled"
    ),
    priority: Optional[str] = Query(
        None, description="Filter by priority: highest, high, medium, low"
    ),
    tag: Optional[str] = Query(None, description="Filter by tag (include #)"),
    project: Optional[str] = Query(
        None, description="Filter by project name (matches file path)"
    ),
    due_before: Optional[date] = Query(None, description="Tasks due before this date"),
    due_after: Optional[date] = Query(None, description="Tasks due after this date"),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of tasks to return"
    ),
):
    """Query tasks with filters."""
    tasks, _ = _load_tasks()

    filtered = _filter_tasks(
        tasks,
        status=status,
        due_before=due_before,
        due_after=due_after,
        priority=priority,
        tag=tag,
        project=project,
    )

    # Sort by due date, then priority
    priority_order = {"highest": 0, "high": 1, "medium": 2, "low": 3, None: 4}
    filtered.sort(
        key=lambda t: (
            t.get("due_date") or "9999-12-31",
            priority_order.get(t.get("priority"), 4),
        )
    )

    # Apply limit
    filtered = filtered[:limit]

    return TasksResponse(
        tasks=[_task_to_summary(t) for t in filtered],
        count=len(filtered),
        query_date=date.today(),
    )


@router.get("/by-project")
async def get_tasks_by_project():
    """Get tasks grouped by project folder."""
    tasks, _ = _load_tasks()

    # Group by top-level PARA folder
    projects: dict[str, list[dict]] = {}

    for task in tasks:
        if task.get("status") in ("done", "cancelled"):
            continue

        file_path = task.get("file_path", "")
        parts = file_path.split("/")

        # Get project identifier (first two path components usually)
        if len(parts) >= 2:
            project_key = f"{parts[0]}/{parts[1]}"
        elif len(parts) >= 1:
            project_key = parts[0]
        else:
            project_key = "Unknown"

        if project_key not in projects:
            projects[project_key] = []
        projects[project_key].append(task)

    # Convert to response format
    result = {}
    for project, tasks_list in sorted(projects.items()):
        result[project] = {
            "count": len(tasks_list),
            "tasks": [
                _task_to_summary(t) for t in tasks_list[:10]
            ],  # Top 10 per project
        }

    return {
        "projects": result,
        "project_count": len(projects),
        "query_date": date.today().isoformat(),
    }

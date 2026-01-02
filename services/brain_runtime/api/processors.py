"""Processor management endpoints."""

import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

# Add services to path to find processors module
services_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(services_path))

from processors.lock import LockManager  # noqa: E402
from processors.calendar.processor import CalendarProcessor  # noqa: E402
from processors.tasks.processor import TaskProcessor  # noqa: E402
from processors.rag.processor import RAGProcessor  # noqa: E402
from core.config import get_settings  # noqa: E402
from core.database import get_db  # noqa: E402
from core.job_manager import get_job_manager  # noqa: E402

router = APIRouter(prefix="/processors", tags=["processors"])

# Initialize lock manager
settings = get_settings()

# Determine data path: use DATA_PATH env var if set (Docker), otherwise fallback to local dev path
if settings.data_path:
    data_root = Path(settings.data_path)
else:
    # Local dev: go up from services/brain_runtime/api to project root
    data_root = Path(__file__).parent.parent.parent.parent / "data"

locks_path = data_root / "locks"
exports_path = data_root / "exports"

lock_manager = LockManager(locks_path)


class RunProcessorRequest(BaseModel):
    """Request to run a processor."""

    processor: str  # "calendar", "tasks", "whoop", etc.
    args: Optional[dict[str, Any]] = None


class ProcessorInfo(BaseModel):
    """Information about a processor."""

    name: str
    description: str
    is_locked: bool
    last_run: Optional[datetime] = None


@router.get("", response_model=list[ProcessorInfo])
async def list_processors():
    """List all available processors and their status."""
    processors = [
        ProcessorInfo(
            name="calendar",
            description="Fetches and normalizes calendar data from ICS URLs",
            is_locked=lock_manager.is_locked("calendar"),
        ),
        ProcessorInfo(
            name="tasks",
            description="Parses Obsidian Tasks from vault markdown files (emoji metadata, priorities, dates)",
            is_locked=lock_manager.is_locked("tasks"),
        ),
        ProcessorInfo(
            name="rag",
            description="Indexes vault for semantic search with E5-multilingual embeddings",
            is_locked=lock_manager.is_locked("rag"),
        ),
    ]
    return processors


@router.post("/run")
async def run_processor(
    request: RunProcessorRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Run a processor.

    Creates a job and runs the processor in the background.
    """
    # Check if processor is already running
    if lock_manager.is_locked(request.processor):
        raise HTTPException(
            status_code=409,
            detail=f"Processor '{request.processor}' is already running",
        )

    # Create job record
    job_manager = get_job_manager(db)
    job = await job_manager.create_job(
        job_type="processor", command=f"run_{request.processor}", args=request.args
    )

    # Schedule background task
    background_tasks.add_task(
        _run_processor_task,
        processor_name=request.processor,
        job_id=job.id,
        args=request.args or {},
    )

    return {"message": f"Processor '{request.processor}' started", "job_id": job.id}


async def _run_processor_task(processor_name: str, job_id: str, args: dict[str, Any]):
    """Background task to run a processor."""
    from core.database import get_session_factory
    from core.job_manager import JobManager

    # Get a fresh database session
    session_factory = get_session_factory()
    async with session_factory() as session:
        job_manager = JobManager(session)

        # Acquire lock
        if not lock_manager.acquire(processor_name):
            await job_manager.update_job_status(
                job_id, "failed", metrics={"error": "Could not acquire lock"}
            )
            return

        try:
            # Update job to running
            await job_manager.update_job_status(job_id, "running")

            # Get processor instance with database session
            processor = _get_processor(processor_name, args, session)
            if processor is None:
                await job_manager.update_job_status(
                    job_id,
                    "failed",
                    metrics={"error": f"Unknown processor: {processor_name}"},
                )
                return

            # Run processor
            result = await processor.run()

            # Update job with result
            if result.success:
                await job_manager.update_job_status(
                    job_id,
                    "succeeded",
                    metrics={
                        "output_path": result.output_path,
                        "processor_metrics": result.metrics,
                    },
                )
            else:
                await job_manager.update_job_status(
                    job_id, "failed", metrics={"error": result.error}
                )

        except Exception as e:
            await job_manager.update_job_status(
                job_id, "failed", metrics={"error": str(e)}
            )
        finally:
            lock_manager.release(processor_name)


def _get_processor(
    name: str, args: dict[str, Any], session: Optional[AsyncSession] = None
):
    """Get processor instance by name."""
    settings = get_settings()
    cache_dir = app_root / "data" / "cache" / "calendar"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if name == "calendar":
        ics_urls = {}
        if settings.calendar_work_url:
            ics_urls["work"] = settings.calendar_work_url
        if settings.calendar_private_url:
            ics_urls["private"] = settings.calendar_private_url
        return CalendarProcessor(
            exports_path=exports_path,
            ics_urls=ics_urls,
            cache_dir=cache_dir,
            timezone="Europe/Amsterdam",
            db_session=session,
        )

    if name == "tasks":
        vault_path = Path(settings.get_vault_path())
        return TaskProcessor(
            exports_path=exports_path,
            vault_path=vault_path,
            vault_name="Obsidian-Private",
            db_session=session,
        )

    if name == "rag":
        vault_path = Path(settings.get_vault_path())
        data_path = app_root / "data"
        recreate = args.get("recreate", False) if args else False
        return RAGProcessor(
            exports_path=exports_path,
            vault_path=vault_path,
            data_path=data_path,
            vault_name="Obsidian-Private",
            recreate=recreate,
        )

    return None

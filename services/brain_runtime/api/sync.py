"""Sync Status API endpoints for Phase 9 - RAG/Calendar/Tasks sync status."""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, get_session_factory
from models.db_models import SyncStatusDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"])

# Track running sync tasks to prevent duplicates
_running_syncs: dict[str, asyncio.Task] = {}


class SyncStatusResponse(BaseModel):
    """Response for a single sync status."""

    sync_type: str
    status: str  # 'idle', 'running', 'failed'
    last_sync_start: Optional[datetime]
    last_sync_end: Optional[datetime]
    files_processed: int
    chunks_created: int
    error_message: Optional[str]
    metadata: dict


class AllSyncStatusResponse(BaseModel):
    """Response for all sync statuses."""

    statuses: List[SyncStatusResponse]


class TriggerSyncResponse(BaseModel):
    """Response for triggering a sync."""

    message: str
    sync_type: str
    status: str


async def reset_stuck_syncs():
    """Reset any syncs stuck in 'running' state on startup."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await db.execute(
            select(SyncStatusDB).where(SyncStatusDB.status == "running")
        )
        stuck = result.scalars().all()
        for sync in stuck:
            logger.warning(f"Resetting stuck sync: {sync.sync_type}")
            sync.status = "idle"
            sync.error_message = "Reset on server restart"
        await db.commit()


@router.get("/status", response_model=AllSyncStatusResponse)
async def get_all_sync_status(db: AsyncSession = Depends(get_db)):
    """Get status of all sync types."""
    result = await db.execute(select(SyncStatusDB))
    statuses = result.scalars().all()

    return AllSyncStatusResponse(
        statuses=[
            SyncStatusResponse(
                sync_type=s.sync_type,
                status=s.status,
                last_sync_start=s.last_sync_start,
                last_sync_end=s.last_sync_end,
                files_processed=s.files_processed or 0,
                chunks_created=s.chunks_created or 0,
                error_message=s.error_message,
                metadata=s.sync_metadata or {},
            )
            for s in statuses
        ]
    )


@router.get("/status/{sync_type}", response_model=SyncStatusResponse)
async def get_sync_status(sync_type: str, db: AsyncSession = Depends(get_db)):
    """Get status of a specific sync type."""
    result = await db.execute(
        select(SyncStatusDB).where(SyncStatusDB.sync_type == sync_type)
    )
    status = result.scalar_one_or_none()

    if not status:
        raise HTTPException(status_code=404, detail=f"Sync type '{sync_type}' not found")

    return SyncStatusResponse(
        sync_type=status.sync_type,
        status=status.status,
        last_sync_start=status.last_sync_start,
        last_sync_end=status.last_sync_end,
        files_processed=status.files_processed or 0,
        chunks_created=status.chunks_created or 0,
        error_message=status.error_message,
        metadata=status.sync_metadata or {},
    )


@router.post("/trigger/{sync_type}", response_model=TriggerSyncResponse)
async def trigger_sync(
    sync_type: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a manual resync for a specific type.

    Valid sync_types: 'rag', 'calendar', 'tasks'
    """
    valid_types = ["rag", "calendar", "tasks"]
    if sync_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sync_type. Must be one of: {valid_types}",
        )

    # Check if already running (either in DB or in our task dict)
    result = await db.execute(
        select(SyncStatusDB).where(SyncStatusDB.sync_type == sync_type)
    )
    status = result.scalar_one_or_none()

    if status and status.status == "running":
        # Check if the task is actually still running
        if sync_type in _running_syncs and not _running_syncs[sync_type].done():
            raise HTTPException(
                status_code=409,
                detail=f"Sync '{sync_type}' is already running",
            )
        else:
            # Task died but status wasn't updated - reset it
            status.status = "idle"
            status.error_message = "Previous sync was interrupted"
            await db.commit()

    # Update status to running
    await db.execute(
        update(SyncStatusDB)
        .where(SyncStatusDB.sync_type == sync_type)
        .values(
            status="running",
            last_sync_start=datetime.utcnow(),
            error_message=None,
        )
    )
    await db.commit()

    # Create and track the async task
    if sync_type == "rag":
        task = asyncio.create_task(run_rag_sync())
    elif sync_type == "calendar":
        task = asyncio.create_task(run_calendar_sync())
    elif sync_type == "tasks":
        task = asyncio.create_task(run_tasks_sync())
    else:
        task = None

    if task:
        _running_syncs[sync_type] = task
        # Add callback to clean up when done
        task.add_done_callback(lambda t: _running_syncs.pop(sync_type, None))

    return TriggerSyncResponse(
        message=f"Sync '{sync_type}' started",
        sync_type=sync_type,
        status="running",
    )


async def run_rag_sync():
    """Background task to run RAG sync."""
    sync_type = "rag"
    logger.info(f"Starting {sync_type} sync...")

    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            # Import processor
            import sys
            from pathlib import Path
            from core.config import get_settings

            services_path = Path(__file__).parent.parent.parent
            if str(services_path) not in sys.path:
                sys.path.insert(0, str(services_path))

            from processors.rag.processor import RAGProcessor

            settings = get_settings()
            app_root = Path(__file__).parent.parent.parent.parent
            exports_path = app_root / "exports"
            vault_path = Path(settings.get_vault_path())
            data_path = app_root / "data"

            logger.info(f"RAG sync: vault={vault_path}")

            processor = RAGProcessor(
                exports_path=exports_path,
                vault_path=vault_path,
                data_path=data_path,
                vault_name="Obsidian-Private",
                recreate=False,
            )
            result = await processor.run()
            logger.info(f"RAG sync completed: success={result.success}, metrics={result.metrics}")

            await db.execute(
                update(SyncStatusDB)
                .where(SyncStatusDB.sync_type == sync_type)
                .values(
                    status="idle" if result.success else "failed",
                    last_sync_end=datetime.utcnow(),
                    files_processed=result.metrics.get("files_processed", 0),
                    chunks_created=result.metrics.get("chunks_created", 0),
                    error_message=None if result.success else result.error,
                )
            )
            await db.commit()

        except Exception as e:
            logger.error(f"RAG sync failed: {e}\n{traceback.format_exc()}")
            await db.execute(
                update(SyncStatusDB)
                .where(SyncStatusDB.sync_type == sync_type)
                .values(
                    status="failed",
                    last_sync_end=datetime.utcnow(),
                    error_message=str(e)[:500],
                )
            )
            await db.commit()


async def run_calendar_sync():
    """Background task to run calendar sync."""
    sync_type = "calendar"
    logger.info(f"Starting {sync_type} sync...")

    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            import sys
            from pathlib import Path
            from core.config import get_settings

            services_path = Path(__file__).parent.parent.parent
            if str(services_path) not in sys.path:
                sys.path.insert(0, str(services_path))

            from processors.calendar.processor import CalendarProcessor

            settings = get_settings()
            app_root = Path(__file__).parent.parent.parent.parent
            exports_path = app_root / "exports"
            cache_dir = app_root / "data" / "cache" / "calendar"
            cache_dir.mkdir(parents=True, exist_ok=True)

            ics_urls = {}
            if settings.calendar_work_url:
                ics_urls["work"] = settings.calendar_work_url
            if settings.calendar_private_url:
                ics_urls["private"] = settings.calendar_private_url

            logger.info(f"Calendar sync with {len(ics_urls)} calendars")

            processor = CalendarProcessor(
                exports_path=exports_path,
                ics_urls=ics_urls,
                cache_dir=cache_dir,
                timezone="Europe/Amsterdam",
                db_session=db,
            )
            result = await processor.run()
            logger.info(f"Calendar sync completed: success={result.success}, metrics={result.metrics}")

            await db.execute(
                update(SyncStatusDB)
                .where(SyncStatusDB.sync_type == sync_type)
                .values(
                    status="idle" if result.success else "failed",
                    last_sync_end=datetime.utcnow(),
                    files_processed=result.metrics.get("events_count", 0),
                    error_message=None if result.success else result.error,
                )
            )
            await db.commit()

        except Exception as e:
            logger.error(f"Calendar sync failed: {e}\n{traceback.format_exc()}")
            await db.execute(
                update(SyncStatusDB)
                .where(SyncStatusDB.sync_type == sync_type)
                .values(
                    status="failed",
                    last_sync_end=datetime.utcnow(),
                    error_message=str(e)[:500],
                )
            )
            await db.commit()


async def run_tasks_sync():
    """Background task to run tasks sync."""
    sync_type = "tasks"
    logger.info(f"Starting {sync_type} sync...")

    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            import sys
            from pathlib import Path
            from core.config import get_settings

            services_path = Path(__file__).parent.parent.parent
            if str(services_path) not in sys.path:
                sys.path.insert(0, str(services_path))

            from processors.tasks.processor import TaskProcessor

            settings = get_settings()
            app_root = Path(__file__).parent.parent.parent.parent
            exports_path = app_root / "exports"
            vault_path = Path(settings.get_vault_path())

            logger.info(f"Tasks sync: vault={vault_path}")

            processor = TaskProcessor(
                exports_path=exports_path,
                vault_path=vault_path,
                vault_name="Obsidian-Private",
                db_session=db,
            )
            result = await processor.run()
            logger.info(f"Tasks sync completed: success={result.success}, metrics={result.metrics}")

            await db.execute(
                update(SyncStatusDB)
                .where(SyncStatusDB.sync_type == sync_type)
                .values(
                    status="idle" if result.success else "failed",
                    last_sync_end=datetime.utcnow(),
                    files_processed=result.metrics.get("files_scanned", 0),
                    chunks_created=result.metrics.get("tasks_count", 0),
                    error_message=None if result.success else result.error,
                )
            )
            await db.commit()

        except Exception as e:
            logger.error(f"Tasks sync failed: {e}\n{traceback.format_exc()}")
            await db.execute(
                update(SyncStatusDB)
                .where(SyncStatusDB.sync_type == sync_type)
                .values(
                    status="failed",
                    last_sync_end=datetime.utcnow(),
                    error_message=str(e)[:500],
                )
            )
            await db.commit()

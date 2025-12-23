"""Job management endpoints."""

import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from models.job import JobRunV1, JobType
from core.job_manager import get_job_manager
from core.database import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    """Request to create a new job."""

    type: JobType
    command: str
    args: Optional[dict[str, Any]] = None


@router.post("/run", response_model=JobRunV1)
async def run_job(request: CreateJobRequest, db: AsyncSession = Depends(get_db)):
    """
    Create and queue a new job.

    Args:
        request: Job creation request
        db: Database session

    Returns:
        The created job
    """
    job_manager = get_job_manager(db)
    job = await job_manager.create_job(
        job_type=request.type, command=request.command, args=request.args
    )
    return job


@router.get("", response_model=list[JobRunV1])
async def list_jobs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    List recent jobs.

    Args:
        limit: Maximum number of jobs to return (default: 50)
        db: Database session

    Returns:
        List of jobs, most recent first
    """
    job_manager = get_job_manager(db)
    return await job_manager.list_jobs(limit=limit)


@router.get("/{job_id}", response_model=JobRunV1)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific job by ID.

    Args:
        job_id: The job ID
        db: Database session

    Returns:
        The job details

    Raises:
        HTTPException: If job not found
    """
    job_manager = get_job_manager(db)
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


async def job_log_generator(job_id: str, db: AsyncSession) -> AsyncGenerator[str, None]:
    """
    Generator for streaming job logs via SSE.

    Args:
        job_id: The job ID to stream logs for
        db: Database session

    Yields:
        SSE-formatted log events
    """
    job_manager = get_job_manager(db)
    job = await job_manager.get_job(job_id)
    if not job:
        yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
        return

    # Send initial status
    yield f"event: status\ndata: {json.dumps({'status': 'started', 'job_id': job_id})}\n\n"

    # Update job to running
    await job_manager.update_job_status(job_id, "running")

    # Simulate job execution with log messages
    log_messages = [
        "Initializing job...",
        f"Running command: {job.command}",
        "Processing...",
        "Job completed successfully",
    ]

    for i, message in enumerate(log_messages):
        await asyncio.sleep(0.5)  # Simulate work
        log_event = {
            "type": "log",
            "level": "info",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"event: log\ndata: {json.dumps(log_event)}\n\n"

    # Mark job as completed
    await job_manager.update_job_status(job_id, "succeeded")

    # Send completion status
    yield f"event: status\ndata: {json.dumps({'status': 'completed', 'job_id': job_id})}\n\n"


@router.get("/{job_id}/stream")
async def stream_job_logs(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Stream job logs via Server-Sent Events.

    Args:
        job_id: The job ID to stream logs for
        db: Database session

    Returns:
        SSE stream of log events
    """
    job_manager = get_job_manager(db)
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return StreamingResponse(
        job_log_generator(job_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

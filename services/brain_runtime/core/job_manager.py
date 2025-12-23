"""Job manager for tracking and executing jobs with database persistence."""

from datetime import datetime, timezone
from typing import Optional, Any
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from models.job import JobRunV1, JobType, JobStatus
from models.db_models import JobDB


class JobManager:
    """Manages job lifecycle with database persistence."""

    def __init__(self, session: AsyncSession):
        """Initialize the job manager with database session."""
        self.session = session

    async def create_job(
        self, job_type: JobType, command: str, args: Optional[dict[str, Any]] = None
    ) -> JobRunV1:
        """
        Create a new job and persist to database.

        Args:
            job_type: Type of job (processor, index, agent, chat)
            command: Command to execute
            args: Optional arguments for the job

        Returns:
            The created job
        """
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        # Create database record
        db_job = JobDB(
            id=job_id,
            type=job_type,
            status="queued",
            command=command,
            args=args,
            artifacts=[],
            started_at=now,
        )
        self.session.add(db_job)
        await self.session.commit()
        await self.session.refresh(db_job)

        # Return Pydantic model
        return JobRunV1(
            id=str(db_job.id),
            type=db_job.type,
            status=db_job.status,
            command=db_job.command,
            args=db_job.args,
            artifacts=db_job.artifacts or [],
            started_at=db_job.started_at,
            ended_at=db_job.ended_at,
            metrics=db_job.metrics,
        )

    async def get_job(self, job_id: str) -> Optional[JobRunV1]:
        """
        Get a job by ID from database.

        Args:
            job_id: The job ID

        Returns:
            The job if found, None otherwise
        """
        try:
            result = await self.session.execute(select(JobDB).where(JobDB.id == job_id))
            db_job = result.scalar_one_or_none()
            if not db_job:
                return None

            return JobRunV1(
                id=str(db_job.id),
                type=db_job.type,
                status=db_job.status,
                command=db_job.command,
                args=db_job.args,
                artifacts=db_job.artifacts or [],
                started_at=db_job.started_at,
                ended_at=db_job.ended_at,
                metrics=db_job.metrics,
            )
        except Exception:
            return None

    async def list_jobs(self, limit: int = 50) -> list[JobRunV1]:
        """
        List recent jobs from database.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of jobs, most recent first
        """
        result = await self.session.execute(
            select(JobDB).order_by(desc(JobDB.started_at)).limit(limit)
        )
        db_jobs = result.scalars().all()

        return [
            JobRunV1(
                id=str(db_job.id),
                type=db_job.type,
                status=db_job.status,
                command=db_job.command,
                args=db_job.args,
                artifacts=db_job.artifacts or [],
                started_at=db_job.started_at,
                ended_at=db_job.ended_at,
                metrics=db_job.metrics,
            )
            for db_job in db_jobs
        ]

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        ended_at: Optional[datetime] = None,
        metrics: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Update job status in database.

        Args:
            job_id: The job ID
            status: New status
            ended_at: Optional end time (set automatically if not provided)
            metrics: Optional metrics to store
        """
        update_data = {"status": status}

        if status in ("succeeded", "failed", "cancelled"):
            update_data["ended_at"] = ended_at or datetime.now(timezone.utc)
        elif ended_at:
            update_data["ended_at"] = ended_at

        if metrics:
            update_data["metrics"] = metrics

        await self.session.execute(
            update(JobDB).where(JobDB.id == job_id).values(**update_data)
        )
        await self.session.commit()


def get_job_manager(session: AsyncSession) -> JobManager:
    """Factory function to create a JobManager with session."""
    return JobManager(session)

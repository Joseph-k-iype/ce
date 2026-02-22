"""
Job Manager Service
====================
Background task execution for rule generation and other long-running operations.
Supports concurrent job execution, status tracking, and progress streaming via SSE.
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobInfo(BaseModel):
    """Tracked job metadata."""
    job_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    progress_pct: float = 0.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    input_summary: str = ""


class JobManager:
    """Manages background jobs with asyncio tasks."""

    _instance: Optional['JobManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._jobs: Dict[str, JobInfo] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._max_history = 100
        self._initialized = True
        logger.info("Job Manager initialized")

    def submit(
        self,
        job_type: str,
        func: Callable,
        kwargs: Dict[str, Any],
        input_summary: str = "",
    ) -> str:
        """Submit a job for background execution.

        Args:
            job_type: Type identifier (e.g., 'rule_generation')
            func: Synchronous function to run in a thread
            kwargs: Arguments to pass to the function
            input_summary: Human-readable summary of inputs

        Returns:
            job_id string
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = JobInfo(
            job_id=job_id,
            job_type=job_type,
            input_summary=input_summary,
        )
        self._jobs[job_id] = job

        # Launch background task
        task = asyncio.create_task(self._run_job(job_id, func, kwargs))
        self._tasks[job_id] = task

        # Cleanup old jobs if history grows too large
        if len(self._jobs) > self._max_history:
            self._cleanup_old_jobs()

        logger.info(f"Job submitted: {job_id} ({job_type})")
        return job_id

    async def _run_job(self, job_id: str, func: Callable, kwargs: Dict[str, Any]):
        """Execute the job function in a thread pool."""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()

        try:
            result = await asyncio.to_thread(func, **kwargs)

            job.status = JobStatus.COMPLETED
            job.progress_pct = 100.0
            job.completed_at = datetime.now().isoformat()

            # Store result (convert to dict if possible)
            if hasattr(result, 'model_dump'):
                job.result = result.model_dump()
            elif hasattr(result, '__dict__'):
                job.result = {k: str(v) for k, v in result.__dict__.items()}
            elif isinstance(result, dict):
                job.result = result
            else:
                job.result = {"value": str(result)}

            job.message = "Job completed successfully"
            logger.info(f"Job completed: {job_id}")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now().isoformat()
            job.message = f"Job failed: {e}"
            logger.error(f"Job failed: {job_id}: {e}")

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job info by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50, job_type: Optional[str] = None) -> list[JobInfo]:
        """List recent jobs, optionally filtered by type."""
        jobs = list(self._jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now().isoformat()
                job.message = "Job cancelled"
            return True
        return False

    def update_progress(self, job_id: str, progress_pct: float, message: str = ""):
        """Update job progress (called from within the job function)."""
        job = self._jobs.get(job_id)
        if job:
            job.progress_pct = progress_pct
            if message:
                job.message = message

    def _cleanup_old_jobs(self):
        """Remove oldest completed/failed jobs when history exceeds limit."""
        terminal = [
            (jid, j) for jid, j in self._jobs.items()
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        ]
        terminal.sort(key=lambda x: x[1].created_at)
        to_remove = len(self._jobs) - self._max_history
        for jid, _ in terminal[:to_remove]:
            del self._jobs[jid]
            self._tasks.pop(jid, None)


_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get the global JobManager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager

"""
Jobs Router
=============
Background job submission, tracking, and SSE streaming.
Supports concurrent rule generation and other long-running tasks.
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.job_manager import get_job_manager, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobSubmitRequest(BaseModel):
    """Request to submit a rule generation job."""
    job_type: str = Field(default="rule_generation", description="Type of job")
    origin_country: str = Field(..., description="Origin country")
    rule_text: str = Field(..., description="Rule text")
    receiving_countries: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)
    is_pii_related: bool = False


class JobSubmitResponse(BaseModel):
    """Response after job submission."""
    job_id: str
    status: str
    message: str


@router.post("/submit", response_model=JobSubmitResponse)
async def submit_job(request: JobSubmitRequest):
    """Submit a background job for rule generation."""
    manager = get_job_manager()

    if request.job_type == "rule_generation":
        from agents.workflows.rule_ingestion_workflow import run_rule_ingestion

        job_id = manager.submit(
            job_type="rule_generation",
            func=run_rule_ingestion,
            kwargs={
                "origin_country": request.origin_country,
                "scenario_type": "attribute",
                "receiving_countries": request.receiving_countries,
                "rule_text": request.rule_text,
                "data_categories": request.data_categories,
                "is_pii_related": request.is_pii_related,
                "thread_id": None,
            },
            input_summary=f"Rule generation for {request.origin_country}: {request.rule_text[:80]}...",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown job type: {request.job_type}")

    return JobSubmitResponse(
        job_id=job_id,
        status="pending",
        message="Job submitted successfully",
    )


@router.get("/{job_id}/status")
async def get_job_status(job_id: str):
    """Get status of a job."""
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.model_dump()


@router.get("/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """SSE stream for job progress updates."""
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_pct = -1
        last_status = None
        while True:
            current_job = manager.get_job(job_id)
            if not current_job:
                break

            # Emit update if progress or status changed
            if current_job.progress_pct != last_pct or current_job.status != last_status:
                last_pct = current_job.progress_pct
                last_status = current_job.status
                data = {
                    "job_id": job_id,
                    "status": current_job.status.value,
                    "progress_pct": current_job.progress_pct,
                    "message": current_job.message,
                }
                yield f"event: job_update\ndata: {json.dumps(data)}\n\n"

            # Stop on terminal status
            if current_job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                final = current_job.model_dump()
                yield f"event: job_complete\ndata: {json.dumps(final, default=str)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("")
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    job_type: Optional[str] = Query(default=None),
):
    """List recent jobs."""
    manager = get_job_manager()
    jobs = manager.list_jobs(limit=limit, job_type=job_type)
    return [j.model_dump() for j in jobs]


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    manager = get_job_manager()
    if manager.cancel_job(job_id):
        return {"message": f"Job {job_id} cancelled"}
    raise HTTPException(status_code=400, detail="Job not found or already completed")

"""
Health Router
==============
Health check, statistics, AI status, cache management, and audit endpoints.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from config.settings import settings
from models.schemas import (
    HealthCheckResponse,
    StatsResponse,
)
from services.database import get_db_service
from services.cache import get_cache_service
from agents.ai_service import get_ai_service
from agents.audit.event_store import get_event_store
from rules.dictionaries.rules_definitions import (
    get_enabled_case_matching_rules,
    get_enabled_transfer_rules,
    get_enabled_attribute_rules,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def get_db():
    return get_db_service()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    db = get_db_service()
    ai = get_ai_service()

    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        database_connected=db.check_connection(),
        rules_graph_loaded=db.check_rules_graph(),
        data_graph_loaded=db.check_data_graph(),
        ai_service_available=ai.is_enabled and ai.check_availability(),
        timestamp=datetime.now(),
    )


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(db=Depends(get_db)):
    """Get dashboard statistics."""
    cache = get_cache_service()
    cached_stats = cache.get("dashboard_stats", "metadata")
    if cached_stats:
        return StatsResponse(**cached_stats)

    try:
        case_query = """
        MATCH (c:Case)
        WHERE c.case_status IN ['Completed', 'Complete', 'Active', 'Published']
        RETURN count(c) as total_cases,
               count(CASE WHEN c.pia_status = 'Completed' THEN 1 END) as pia_completed,
               count(CASE WHEN c.tia_status = 'Completed' THEN 1 END) as tia_completed,
               count(CASE WHEN c.hrpr_status = 'Completed' THEN 1 END) as hrpr_completed
        """
        case_result = db.execute_data_query(case_query)
        case_data = case_result[0] if case_result else {}

        country_query = "MATCH (c:Country) RETURN count(c) as count"
        country_result = db.execute_data_query(country_query)
        country_count = country_result[0].get('count', 0) if country_result else 0

        jurisdiction_query = "MATCH (j:Jurisdiction) RETURN count(j) as count"
        jurisdiction_result = db.execute_data_query(jurisdiction_query)
        jurisdiction_count = jurisdiction_result[0].get('count', 0) if jurisdiction_result else 0

        purpose_query = "MATCH (p:Purpose) RETURN count(p) as count"
        purpose_result = db.execute_data_query(purpose_query)
        purpose_count = purpose_result[0].get('count', 0) if purpose_result else 0

        rules_count = (
            len(get_enabled_case_matching_rules()) +
            len(get_enabled_transfer_rules()) +
            len(get_enabled_attribute_rules())
        )

        stats = {
            "total_cases": case_data.get('total_cases', 0),
            "total_countries": country_count,
            "total_jurisdictions": jurisdiction_count,
            "total_purposes": purpose_count,
            "pia_completed_count": case_data.get('pia_completed', 0),
            "tia_completed_count": case_data.get('tia_completed', 0),
            "hrpr_completed_count": case_data.get('hrpr_completed', 0),
            "rules_count": rules_count,
            "cache_hit_rate": cache.get_all_stats().get('queries', {}).get('hit_rate', 0),
        }

        cache.set("dashboard_stats", stats, "metadata", ttl=60)
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/ai/status")
async def get_ai_status():
    """Get AI service status."""
    ai = get_ai_service()
    return {
        "enabled": ai.is_enabled,
        "available": ai.check_availability() if ai.is_enabled else False,
        "model": settings.ai.llm_model,
    }


# Agent audit endpoints (using new event store)
@router.get("/api/agent/sessions")
async def get_agent_sessions(limit: int = 50):
    """Get recent agent sessions from event store."""
    event_store = get_event_store()
    return event_store.list_sessions(limit=limit)


@router.get("/api/agent/sessions/{session_id}")
async def get_agent_session(session_id: str):
    """Get detailed agent session events."""
    event_store = get_event_store()
    summary = event_store.get_session_summary(session_id)
    if summary.get("total_events", 0) == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    events = event_store.get_events(session_id)
    return {
        "summary": summary,
        "events": [e.model_dump() for e in events],
    }


@router.get("/api/agent/sessions/{session_id}/export")
async def export_agent_session(session_id: str):
    """Export agent session events as JSON."""
    event_store = get_event_store()
    export = event_store.export_session(session_id)
    if export == "[]":
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse(
        content=json.loads(export),
        headers={"Content-Disposition": f"attachment; filename=agent_session_{session_id}.json"},
    )


@router.get("/api/agent/stats")
async def get_agent_stats():
    """Get agent event store statistics."""
    event_store = get_event_store()
    sessions = event_store.list_sessions(limit=1000)
    total_events = sum(s.get("total_events", 0) for s in sessions)
    return {
        "total_sessions": len(sessions),
        "total_events": total_events,
    }


# Cache management
@router.get("/api/cache/clear")
async def clear_cache():
    """Clear all caches."""
    cache = get_cache_service()
    cleared = cache.clear()
    return {"message": f"Cleared {cleared} cache entries"}


@router.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    cache = get_cache_service()
    return cache.get_all_stats()

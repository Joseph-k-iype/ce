"""
Sandbox Router
===============
Sandbox graph management endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException

from services.sandbox_service import get_sandbox_service
from models.wizard_models import SandboxEvaluationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


@router.post("/create")
async def create_sandbox(session_id: str):
    """Create a new sandbox graph."""
    sandbox = get_sandbox_service()
    try:
        graph_name = sandbox.create_sandbox(session_id)
        return {"graph_name": graph_name, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{graph_name}/add-rule")
async def add_rule_to_sandbox(graph_name: str, rule_def: dict):
    """Add a rule to the sandbox graph."""
    sandbox = get_sandbox_service()
    success = sandbox.add_rule_to_sandbox(graph_name, rule_def)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add rule to sandbox")
    return {"message": "Rule added to sandbox", "graph_name": graph_name}


@router.post("/{graph_name}/evaluate")
async def evaluate_in_sandbox(graph_name: str, request: SandboxEvaluationRequest):
    """Run evaluation against sandbox graph."""
    sandbox = get_sandbox_service()
    try:
        result = sandbox.evaluate_in_sandbox(
            graph_name=graph_name,
            origin_country=request.origin_country,
            receiving_country=request.receiving_country,
            pii=request.pii,
            purposes=request.purposes,
            process_l1=request.process_l1,
            process_l2=request.process_l2,
            process_l3=request.process_l3,
            personal_data_names=request.personal_data_names,
            metadata=request.metadata,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{graph_name}")
async def cleanup_sandbox(graph_name: str):
    """Delete a sandbox graph."""
    sandbox = get_sandbox_service()
    sandbox.cleanup_sandbox(graph_name)
    return {"message": f"Sandbox {graph_name} cleaned up"}

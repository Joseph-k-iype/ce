"""
Rule Links Router
==================
CRUD endpoints for managing rule-entity links (LINKED_TO relationships)
and fetching rule subgraphs for the per-rule editor.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from services.database import get_db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rules", tags=["Internal - Rule Links Management"])


def get_db():
    return get_db_service()


# ── Request/Response Models ──────────────────────────────────────────

class LinkRequest(BaseModel):
    """Request to create a LINKED_TO relationship."""
    target_type: str = Field(..., description="Node label: Regulator, Authority, Process, etc.")
    target_name: str = Field(..., description="Name of the target node")


class LinkResponse(BaseModel):
    """Information about a linked entity."""
    target_type: str
    target_name: str
    target_id: Optional[str] = None


class RuleSubgraphNode(BaseModel):
    """Node in a rule subgraph (for React Flow)."""
    id: str
    label: str
    node_type: str
    properties: dict = Field(default_factory=dict)


class RuleSubgraphEdge(BaseModel):
    """Edge in a rule subgraph."""
    id: str
    source: str
    target: str
    relationship_type: str


class RuleSubgraphResponse(BaseModel):
    """Rule subgraph for React Flow rendering."""
    rule_id: str
    nodes: List[RuleSubgraphNode]
    edges: List[RuleSubgraphEdge]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/{rule_id}/links", response_model=List[LinkResponse])
async def get_rule_links(rule_id: str, db=Depends(get_db)):
    """Get all entities linked to a rule."""
    try:
        query = """
        MATCH (r:Rule {rule_id: $rule_id})-[:LINKED_TO]->(target)
        RETURN labels(target)[0] AS target_type,
               target.name AS target_name,
               target.id AS target_id
        ORDER BY target_type, target_name
        """
        rows = db.execute_rules_query(query, params={"rule_id": rule_id})
        return [
            LinkResponse(
                target_type=row.get("target_type", ""),
                target_name=row.get("target_name", ""),
                target_id=row.get("target_id"),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error getting rule links: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{rule_id}/link", response_model=dict)
async def create_rule_link(rule_id: str, request: LinkRequest, db=Depends(get_db)):
    """Create a LINKED_TO relationship between a rule and an entity."""
    try:
        # Validate target exists
        check_query = f"""
        MATCH (target:{request.target_type} {{name: $target_name}})
        RETURN count(target) AS cnt
        """
        result = db.execute_rules_query(check_query, params={"target_name": request.target_name})
        if not result or result[0].get("cnt", 0) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"{request.target_type} '{request.target_name}' not found in graph"
            )

        # Create link
        link_query = f"""
        MATCH (r:Rule {{rule_id: $rule_id}})
        MATCH (target:{request.target_type} {{name: $target_name}})
        MERGE (r)-[:LINKED_TO]->(target)
        RETURN r.rule_id AS rule_id
        """
        db.execute_rules_query(link_query, params={
            "rule_id": rule_id,
            "target_name": request.target_name,
        })
        return {"message": f"Linked rule {rule_id} to {request.target_type} '{request.target_name}'"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}/unlink", response_model=dict)
async def remove_rule_link(rule_id: str, request: LinkRequest, db=Depends(get_db)):
    """Remove a LINKED_TO relationship between a rule and an entity."""
    try:
        query = f"""
        MATCH (r:Rule {{rule_id: $rule_id}})-[rel:LINKED_TO]->(target:{request.target_type} {{name: $target_name}})
        DELETE rel
        RETURN count(rel) AS deleted
        """
        result = db.execute_rules_query(query, params={
            "rule_id": rule_id,
            "target_name": request.target_name,
        })
        deleted = result[0].get("deleted", 0) if result else 0
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Link not found")
        return {"message": f"Unlinked rule {rule_id} from {request.target_type} '{request.target_name}'"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing rule link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{rule_id}/link-regulator", response_model=dict)
async def link_regulator(rule_id: str, name: str, db=Depends(get_db)):
    """Convenience endpoint to link a rule to a regulator."""
    return await create_rule_link(rule_id, LinkRequest(target_type="Regulator", target_name=name), db)


@router.post("/{rule_id}/link-authority", response_model=dict)
async def link_authority(rule_id: str, name: str, db=Depends(get_db)):
    """Convenience endpoint to link a rule to an authority."""
    return await create_rule_link(rule_id, LinkRequest(target_type="Authority", target_name=name), db)


@router.get("/{rule_id}/subgraph", response_model=RuleSubgraphResponse)
async def get_rule_subgraph(rule_id: str, db=Depends(get_db)):
    """Get the full subgraph for a single rule (for React Flow editor)."""
    try:
        # Get the rule node + all connected nodes (1-hop)
        query = """
        MATCH (r:Rule {rule_id: $rule_id})
        OPTIONAL MATCH (r)-[rel]-(neighbor)
        RETURN r, rel, neighbor,
               type(rel) AS rel_type,
               startNode(rel) = r AS is_outgoing
        """
        rows = db.execute_rules_query(query, params={"rule_id": rule_id})

        if not rows:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        nodes_map = {}
        edges_list = []
        edge_counter = 0

        # Add the rule node
        rule_data = rows[0].get("r", {})
        rule_node_id = f"rule_{rule_id}"
        nodes_map[rule_node_id] = RuleSubgraphNode(
            id=rule_node_id,
            label=rule_data.get("name", rule_id),
            node_type="Rule",
            properties={k: v for k, v in rule_data.items() if v is not None},
        )

        for row in rows:
            neighbor = row.get("neighbor")
            if not neighbor:
                continue

            rel_type = row.get("rel_type", "RELATED")
            is_outgoing = row.get("is_outgoing", True)

            # Determine neighbor label and ID
            neighbor_name = neighbor.get("name", neighbor.get("id", "unknown"))
            # Use a stable ID based on type + name
            neighbor_type = "Unknown"
            for label_candidate in ["Country", "CountryGroup", "Regulator", "Authority",
                                     "Process", "Purpose", "PurposeOfProcessing",
                                     "DataCategory", "SensitiveDataCategory",
                                     "GDC", "DataSubject", "LegalEntity",
                                     "GlobalBusinessFunction", "Permission",
                                     "Prohibition", "Duty", "Action"]:
                # We can't determine label from FalkorDB row directly,
                # so use rel_type as a hint
                pass

            # Infer type from relationship
            type_hints = {
                "TRIGGERED_BY_ORIGIN": "Country/Group",
                "TRIGGERED_BY_RECEIVING": "Country/Group",
                "ORIGINATES_FROM": "Country",
                "RECEIVED_IN": "Country",
                "HAS_PERMISSION": "Permission",
                "HAS_PROHIBITION": "Prohibition",
                "CAN_HAVE_DUTY": "Duty",
                "LINKED_TO": "LinkedEntity",
                "HAS_PROCESS": "Process",
                "HAS_PURPOSE": "Purpose",
                "HAS_DATA_CATEGORY": "DataCategory",
            }
            neighbor_type = type_hints.get(rel_type, "Entity")
            neighbor_id = f"{neighbor_type}_{neighbor_name}".replace(" ", "_")

            if neighbor_id not in nodes_map:
                nodes_map[neighbor_id] = RuleSubgraphNode(
                    id=neighbor_id,
                    label=neighbor_name,
                    node_type=neighbor_type,
                    properties={k: v for k, v in neighbor.items() if v is not None},
                )

            edge_counter += 1
            edge_id = f"e_{edge_counter}"
            if is_outgoing:
                edges_list.append(RuleSubgraphEdge(
                    id=edge_id, source=rule_node_id, target=neighbor_id,
                    relationship_type=rel_type,
                ))
            else:
                edges_list.append(RuleSubgraphEdge(
                    id=edge_id, source=neighbor_id, target=rule_node_id,
                    relationship_type=rel_type,
                ))

        return RuleSubgraphResponse(
            rule_id=rule_id,
            nodes=list(nodes_map.values()),
            edges=edges_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule subgraph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

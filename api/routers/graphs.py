"""
Graphs API Router

Endpoints for managing and querying multiple graphs.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.multi_graph_query import MultiGraphQuery
from services.graph_registry import get_graph_registry

router = APIRouter(prefix="/api/graphs", tags=["graphs"])


class GraphQueryRequest(BaseModel):
    """Request model for graph query."""
    cypher: str
    params: Optional[Dict[str, Any]] = None


class MultiGraphQueryRequest(BaseModel):
    """Request model for multi-graph query."""
    queries: Dict[str, Dict[str, Any]]  # graph_name -> {cypher, params}


class SearchRequest(BaseModel):
    """Request model for cross-graph search."""
    node_label: str
    filters: Dict[str, Any]
    graph_types: Optional[List[str]] = None
    limit: int = 100


class RelationshipSearchRequest(BaseModel):
    """Request model for relationship search."""
    relationship_type: str
    source_filters: Optional[Dict[str, Any]] = None
    target_filters: Optional[Dict[str, Any]] = None
    graph_types: Optional[List[str]] = None
    limit: int = 100


class GraphRegistrationRequest(BaseModel):
    """Request model for registering a new graph."""
    name: str
    graph_type: str
    description: str = ""
    metadata: Optional[Dict[str, Any]] = None


@router.get("/list")
async def list_graphs(
    graph_type: Optional[str] = None,
    enabled_only: bool = True
):
    """List all registered graphs.

    Args:
        graph_type: Optional filter by graph type (rules, data_transfer, external)
        enabled_only: Only return enabled graphs

    Returns:
        List of graph metadata
    """
    try:
        multi_query = MultiGraphQuery()
        graphs = multi_query.list_available_graphs(enabled_only=enabled_only)

        if graph_type:
            graphs = [g for g in graphs if g["graph_type"] == graph_type]

        return {
            "status": "success",
            "count": len(graphs),
            "graphs": graphs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/schema")
async def get_graph_schema(name: str):
    """Get graph schema (node labels, relationship types).

    Args:
        name: Graph name

    Returns:
        Graph schema information
    """
    try:
        registry = get_graph_registry()
        graph_meta = registry.get_graph(name)

        if not graph_meta:
            raise HTTPException(status_code=404, detail=f"Graph '{name}' not found")

        return {
            "status": "success",
            "name": graph_meta.name,
            "graph_type": graph_meta.graph_type,
            "description": graph_meta.description,
            "node_labels": list(graph_meta.node_labels),
            "relationship_types": list(graph_meta.relationship_types),
            "enabled": graph_meta.enabled,
            "created_at": graph_meta.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/query")
async def query_graph(name: str, request: GraphQueryRequest):
    """Execute Cypher query on specific graph.

    Args:
        name: Graph name
        request: Query request with cypher and params

    Returns:
        Query results
    """
    try:
        multi_query = MultiGraphQuery()
        results = multi_query.query(name, request.cypher, request.params)

        return {
            "status": "success",
            "graph": name,
            "count": len(results),
            "results": results
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-query")
async def multi_query(request: MultiGraphQueryRequest):
    """Execute queries on multiple graphs in parallel.

    Args:
        request: Dict mapping graph_name -> {cypher, params}

    Returns:
        Dict mapping graph_name -> results
    """
    try:
        # Convert request format to service format
        queries = {}
        for graph_name, query_spec in request.queries.items():
            # Support both "cypher" and "query" field names
            cypher = query_spec.get("cypher") or query_spec.get("query")
            params = query_spec.get("params", {})
            if not cypher:
                raise ValueError(f"Missing 'cypher' or 'query' field for graph '{graph_name}'")
            queries[graph_name] = (cypher, params)

        multi_query_service = MultiGraphQuery()
        results = multi_query_service.multi_query(queries)

        return {
            "status": "success",
            "results": results
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_across_graphs(request: SearchRequest):
    """Search for nodes across multiple graphs.

    Args:
        request: Search request with node_label, filters, graph_types, limit

    Returns:
        Dict mapping graph_name -> matching nodes
    """
    try:
        multi_query = MultiGraphQuery()
        results = multi_query.search_across_graphs(
            node_label=request.node_label,
            property_filters=request.filters,
            graph_types=request.graph_types,
            limit=request.limit
        )

        # Count total results
        total_count = sum(len(nodes) for nodes in results.values())

        return {
            "status": "success",
            "node_label": request.node_label,
            "graphs_searched": len(results),
            "total_results": total_count,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/relationships")
async def search_relationships(request: RelationshipSearchRequest):
    """Search for relationships across multiple graphs.

    Args:
        request: Relationship search request

    Returns:
        Dict mapping graph_name -> matching relationships
    """
    try:
        multi_query = MultiGraphQuery()
        results = multi_query.search_by_relationship(
            relationship_type=request.relationship_type,
            source_filters=request.source_filters,
            target_filters=request.target_filters,
            graph_types=request.graph_types,
            limit=request.limit
        )

        total_count = sum(len(rels) for rels in results.values())

        return {
            "status": "success",
            "relationship_type": request.relationship_type,
            "graphs_searched": len(results),
            "total_results": total_count,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/node-counts")
async def get_node_counts(
    node_label: str,
    graph_types: Optional[List[str]] = None
):
    """Count nodes of a specific label across graphs.

    Args:
        node_label: Node label to count
        graph_types: Optional list of graph types to include

    Returns:
        Dict mapping graph_name -> count
    """
    try:
        multi_query = MultiGraphQuery()
        counts = multi_query.aggregate_node_counts(node_label, graph_types)

        total_count = sum(counts.values())

        return {
            "status": "success",
            "node_label": node_label,
            "total_count": total_count,
            "counts_by_graph": counts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/enable")
async def enable_graph(name: str):
    """Enable a graph for queries.

    Args:
        name: Graph name

    Returns:
        Success status
    """
    try:
        registry = get_graph_registry()
        success = registry.enable_graph(name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Graph '{name}' not found")

        return {
            "status": "success",
            "message": f"Graph '{name}' enabled"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/disable")
async def disable_graph(name: str):
    """Disable a graph from queries.

    Args:
        name: Graph name

    Returns:
        Success status
    """
    try:
        registry = get_graph_registry()
        success = registry.disable_graph(name)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot disable graph '{name}' (not found or is system graph)"
            )

        return {
            "status": "success",
            "message": f"Graph '{name}' disabled"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/refresh-schema")
async def refresh_schema(name: str):
    """Refresh node labels and relationship types for a graph.

    Args:
        name: Graph name

    Returns:
        Updated schema information
    """
    try:
        registry = get_graph_registry()
        success = registry.refresh_schema(name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Graph '{name}' not found")

        # Return updated schema
        graph_meta = registry.get_graph(name)
        return {
            "status": "success",
            "name": graph_meta.name,
            "node_labels": list(graph_meta.node_labels),
            "relationship_types": list(graph_meta.relationship_types)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_graph(request: GraphRegistrationRequest):
    """Register a new graph in the registry.

    Args:
        request: Graph registration details

    Returns:
        Registered graph metadata
    """
    try:
        registry = get_graph_registry()
        graph_meta = registry.register_graph(
            name=request.name,
            graph_type=request.graph_type,
            description=request.description,
            metadata=request.metadata
        )

        return {
            "status": "success",
            "message": f"Graph '{request.name}' registered successfully",
            "graph": {
                "name": graph_meta.name,
                "graph_type": graph_meta.graph_type,
                "description": graph_meta.description,
                "node_labels": list(graph_meta.node_labels),
                "relationship_types": list(graph_meta.relationship_types),
                "enabled": graph_meta.enabled
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

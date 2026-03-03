"""
Multi-Graph Query Service

Execute queries across multiple graphs for comprehensive compliance analysis.
Supports parallel queries, cross-graph search, and result aggregation.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from services.database import get_db_service
from services.graph_registry import get_graph_registry, GraphMetadata

logger = logging.getLogger(__name__)


class MultiGraphQuery:
    """Execute queries across multiple graphs."""

    def __init__(self, timeout: int = 5):
        """Initialize multi-graph query service.

        Args:
            timeout: Maximum seconds to wait for each graph query (default: 5)
        """
        self.db = get_db_service()
        self.registry = get_graph_registry()
        self.timeout = timeout

    def query(
        self,
        graph_name: str,
        cypher: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute query on a specific graph.

        Args:
            graph_name: Name of the graph to query
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        graph_meta = self.registry.get_graph(graph_name)
        if not graph_meta:
            raise ValueError(f"Graph '{graph_name}' not found in registry")

        if not graph_meta.enabled:
            raise ValueError(f"Graph '{graph_name}' is disabled")

        try:
            graph = self.db.db.select_graph(graph_name)
            result = graph.query(cypher, params or {})

            # Convert result to list of dicts
            if not result.result_set:
                return []

            # Get column names from result header
            if hasattr(result, 'header'):
                columns = [col[1] for col in result.header]
            else:
                # Fallback: generate column names
                columns = [f"col{i}" for i in range(len(result.result_set[0]))]

            def _serialize(val):
                if hasattr(val, 'labels') and hasattr(val, 'properties'):
                    return {"labels": list(val.labels) if val.labels else [], "properties": val.properties or {}}
                if hasattr(val, 'relation') and hasattr(val, 'properties'):
                    return {"type": getattr(val, 'relation', ''), "properties": getattr(val, 'properties', {})}
                if isinstance(val, list):
                    return [_serialize(v) for v in val]
                if isinstance(val, dict):
                    return {k: _serialize(v) for k, v in val.items()}
                return val

            return [
                {k: _serialize(v) for k, v in zip(columns, row)}
                for row in result.result_set
            ]

        except Exception as e:
            logger.error(f"Query failed on graph '{graph_name}': {e}")
            raise

    def multi_query(
        self,
        queries: Dict[str, Tuple[str, Optional[Dict[str, Any]]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Execute queries on multiple graphs in parallel.

        Args:
            queries: Dict mapping graph_name -> (cypher, params)

        Returns:
            Dict mapping graph_name -> results

        Example:
            results = multi_query({
                "RulesGraph": ("MATCH (r:Rule) RETURN r LIMIT 5", None),
                "DataTransferGraph": ("MATCH (t:Transfer) RETURN t LIMIT 5", None)
            })
        """
        results = {}

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = {}

            for graph_name, (cypher, params) in queries.items():
                future = executor.submit(self.query, graph_name, cypher, params)
                futures[graph_name] = future

            for graph_name, future in futures.items():
                try:
                    results[graph_name] = future.result(timeout=self.timeout)
                except TimeoutError:
                    logger.warning(f"Query timeout on graph '{graph_name}' ({self.timeout}s)")
                    results[graph_name] = []
                except Exception as e:
                    logger.error(f"Query failed on graph '{graph_name}': {e}")
                    results[graph_name] = []

        return results

    def search_across_graphs(
        self,
        node_label: str,
        property_filters: Dict[str, Any],
        graph_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search for nodes across multiple graphs.

        Args:
            node_label: Node label to search for (e.g., "Rule", "DataCategory")
            property_filters: Dict of property_name -> value to filter by
            graph_types: Optional list of graph types to search (e.g., ["rules", "external"])
            limit: Maximum results per graph

        Returns:
            Dict mapping graph_name -> list of matching nodes

        Example:
            results = search_across_graphs(
                "DataCategory",
                {"name": "Health Data"},
                graph_types=["rules", "external"]
            )
        """
        # Find graphs containing the node label
        candidate_graphs = self.registry.get_graphs_with_node_label(node_label)

        # Filter by graph type if specified
        if graph_types:
            graphs_to_search = []
            for graph_name in candidate_graphs:
                graph_meta = self.registry.get_graph(graph_name)
                if graph_meta and graph_meta.graph_type in graph_types:
                    graphs_to_search.append(graph_name)
        else:
            graphs_to_search = candidate_graphs

        if not graphs_to_search:
            logger.info(f"No graphs found with node label '{node_label}'")
            return {}

        # Build MATCH query with WHERE clauses
        where_clauses = [f"n.{k} = ${k}" for k in property_filters.keys()]
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"

        cypher = f"""
        MATCH (n:{node_label})
        WHERE {where_clause}
        RETURN n
        LIMIT {limit}
        """

        # Build queries dict for parallel execution
        queries = {
            graph_name: (cypher, property_filters)
            for graph_name in graphs_to_search
        }

        return self.multi_query(queries)

    def search_by_relationship(
        self,
        relationship_type: str,
        source_filters: Optional[Dict[str, Any]] = None,
        target_filters: Optional[Dict[str, Any]] = None,
        graph_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search for relationships across multiple graphs.

        Args:
            relationship_type: Relationship type to search for
            source_filters: Optional filters for source node
            target_filters: Optional filters for target node
            graph_types: Optional list of graph types to search
            limit: Maximum results per graph

        Returns:
            Dict mapping graph_name -> list of matching relationships
        """
        # Find graphs containing the relationship type
        candidate_graphs = self.registry.get_graphs_with_relationship(relationship_type)

        # Filter by graph type if specified
        if graph_types:
            graphs_to_search = []
            for graph_name in candidate_graphs:
                graph_meta = self.registry.get_graph(graph_name)
                if graph_meta and graph_meta.graph_type in graph_types:
                    graphs_to_search.append(graph_name)
        else:
            graphs_to_search = candidate_graphs

        if not graphs_to_search:
            logger.info(f"No graphs found with relationship '{relationship_type}'")
            return {}

        # Build MATCH query
        source_where = ""
        target_where = ""
        params = {}

        if source_filters:
            source_clauses = [f"s.{k} = $s_{k}" for k in source_filters.keys()]
            source_where = " WHERE " + " AND ".join(source_clauses)
            params.update({f"s_{k}": v for k, v in source_filters.items()})

        if target_filters:
            target_clauses = [f"t.{k} = $t_{k}" for k in target_filters.keys()]
            target_where = " WHERE " + " AND ".join(target_clauses)
            params.update({f"t_{k}": v for k, v in target_filters.items()})

        cypher = f"""
        MATCH (s)-[r:{relationship_type}]->(t)
        {source_where}
        {target_where}
        RETURN s, r, t
        LIMIT {limit}
        """

        # Build queries dict for parallel execution
        queries = {
            graph_name: (cypher, params)
            for graph_name in graphs_to_search
        }

        return self.multi_query(queries)

    def aggregate_node_counts(
        self,
        node_label: str,
        graph_types: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Count nodes of a specific label across graphs.

        Args:
            node_label: Node label to count
            graph_types: Optional list of graph types to include

        Returns:
            Dict mapping graph_name -> count
        """
        # Find graphs containing the node label
        candidate_graphs = self.registry.get_graphs_with_node_label(node_label)

        # Filter by graph type if specified
        if graph_types:
            graphs_to_query = []
            for graph_name in candidate_graphs:
                graph_meta = self.registry.get_graph(graph_name)
                if graph_meta and graph_meta.graph_type in graph_types:
                    graphs_to_query.append(graph_name)
        else:
            graphs_to_query = candidate_graphs

        if not graphs_to_query:
            return {}

        cypher = f"MATCH (n:{node_label}) RETURN count(n) as count"

        queries = {
            graph_name: (cypher, None)
            for graph_name in graphs_to_query
        }

        results = self.multi_query(queries)

        # Extract counts from results
        counts = {}
        for graph_name, rows in results.items():
            if rows and len(rows) > 0:
                counts[graph_name] = rows[0].get('count', 0)
            else:
                counts[graph_name] = 0

        return counts

    def list_available_graphs(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """List all available graphs with their metadata.

        Args:
            enabled_only: Only return enabled graphs

        Returns:
            List of graph metadata dicts
        """
        graphs = self.registry.list_graphs(enabled_only=enabled_only)

        return [
            {
                "name": g.name,
                "graph_type": g.graph_type,
                "description": g.description,
                "created_at": g.created_at.isoformat(),
                "node_labels": list(g.node_labels),
                "relationship_types": list(g.relationship_types),
                "enabled": g.enabled,
                "metadata": g.metadata
            }
            for g in graphs
        ]

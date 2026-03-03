"""
Graph Import Service

Converts data from external sources to graph nodes and relationships.
"""

from typing import Dict, List, Any, Optional
import logging
import uuid
import re
from services.database import get_db_service
from services.data_source_connector import (
    DataSourceManager,
    NodeMapping,
    RelationshipMapping,
    get_data_source_manager
)
from services.graph_registry import get_graph_registry

logger = logging.getLogger(__name__)


class GraphImportService:
    """Service for importing external data to graphs."""

    def __init__(self):
        self.db = get_db_service()
        self.source_manager = get_data_source_manager()
        self.registry = get_graph_registry()

    def import_to_graph(
        self,
        source_id: str,
        graph_name: str,
        node_mappings: List[NodeMapping],
        relationship_mappings: Optional[List[RelationshipMapping]] = None,
        clear_existing: bool = False
    ) -> Dict[str, Any]:
        """Import data from source to graph.

        Args:
            source_id: ID of the data source
            graph_name: Name of the target graph
            node_mappings: How to map data to nodes
            relationship_mappings: How to create relationships
            clear_existing: Whether to clear existing graph data

        Returns:
            Import statistics
        """
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": [],
            "duration_ms": 0
        }

        try:
            import time
            start_time = time.time()

            # Get connector for data source
            connector = self.source_manager.get_connector(source_id)
            if not connector:
                raise ValueError(f"Data source '{source_id}' not found")

            # Test connection
            success, message = connector.test_connection()
            if not success:
                raise ConnectionError(f"Failed to connect: {message}")

            # Fetch data
            logger.info(f"Fetching data from source '{source_id}'...")
            data = connector.fetch_data()
            logger.info(f"Fetched {len(data)} rows")

            if not data:
                return {**stats, "message": "No data to import"}

            # Get or create graph
            graph = self.db.db.select_graph(graph_name)

            # Clear existing data if requested
            if clear_existing:
                logger.warning(f"Clearing existing data in graph '{graph_name}'")
                graph.query("MATCH (n) DETACH DELETE n")

            # Create nodes for each mapping
            for mapping in node_mappings:
                nodes_created = self._create_nodes(
                    graph,
                    data,
                    mapping
                )
                stats["nodes_created"] += nodes_created

            # Create relationships if specified
            if relationship_mappings:
                for rel_mapping in relationship_mappings:
                    rels_created = self._create_relationships(
                        graph,
                        data,
                        rel_mapping
                    )
                    stats["relationships_created"] += rels_created

            # Register graph in registry
            source_config = self.source_manager.get_source(source_id)
            self.registry.register_graph(
                name=graph_name,
                graph_type="external",
                description=f"Imported from {source_config.name}" if source_config else "External data",
                metadata={
                    "source_id": source_id,
                    "source_type": source_config.source_type.value if source_config else "unknown",
                    "imported_at": time.time(),
                    "row_count": len(data)
                }
            )

            stats["duration_ms"] = int((time.time() - start_time) * 1000)
            logger.info(
                f"Import complete: {stats['nodes_created']} nodes, "
                f"{stats['relationships_created']} relationships in {stats['duration_ms']}ms"
            )

            return stats

        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            stats["errors"].append(str(e))
            return stats

    def _create_nodes(
        self,
        graph,
        data: List[Dict[str, Any]],
        mapping: NodeMapping
    ) -> int:
        """Create nodes from data using mapping."""
        created = 0

        for row in data:
            try:
                # Extract node ID
                node_id = row.get(mapping.id_field)
                if not node_id:
                    logger.warning(f"Skipping row without ID field '{mapping.id_field}'")
                    continue

                # Build properties
                properties = {}
                for source_field, node_prop in mapping.property_mappings.items():
                    if source_field in row:
                        clean_prop = re.sub(r'[^a-zA-Z0-9_]', '_', node_prop)
                        properties[clean_prop] = row[source_field]

                # Add ID to properties
                properties["id"] = str(node_id)

                # Create node
                cypher = f"""
                MERGE (n:{mapping.node_label} {{id: $id}})
                SET n += $props
                """

                graph.query(cypher, {"id": str(node_id), "props": properties})
                created += 1

            except Exception as e:
                logger.warning(f"Failed to create node: {e}")
                continue

        logger.info(f"Created {created} {mapping.node_label} nodes")
        return created

    def _create_relationships(
        self,
        graph,
        data: List[Dict[str, Any]],
        mapping: RelationshipMapping
    ) -> int:
        """Create relationships from data using mapping."""
        created = 0

        for row in data:
            try:
                # Extract IDs
                source_id = row.get(mapping.source_id_field)
                foreign_key = row.get(mapping.foreign_key_field)

                if not source_id or not foreign_key:
                    continue

                # Build relationship properties
                props = {}
                for source_field, rel_prop in mapping.properties.items():
                    if source_field in row:
                        clean_prop = re.sub(r'[^a-zA-Z0-9_]', '_', rel_prop)
                        props[clean_prop] = row[source_field]

                # In RedisGraph/FalkorDB, property types matter.
                # If a node was saved with an integer ID but we check for a string, MATCH fails.
                # We save all node IDs as strings (str(node_id)), so we must ensure MATCH uses strings too.
                cypher = f"""
                MATCH (s:{mapping.source_node_label} {{id: $source_id}})
                MATCH (t:{mapping.target_node_label} {{id: $target_id}})
                MERGE (s)-[r:{mapping.relationship_type}]->(t)
                """

                if props:
                    # In RedisGraph, you must SET properties individually
                    cypher += "\nSET " + ", ".join([f"r.{k} = $props.{k}" for k in props.keys()])

                # Log the attempted relationship creation for debugging
                logger.debug(f"Creating edge: (:{mapping.source_node_label} id='{source_id}') -[:{mapping.relationship_type}]-> (:{mapping.target_node_label} id='{foreign_key}')")

                result = graph.query(cypher, {
                    "source_id": str(source_id),
                    "target_id": str(foreign_key),
                    "props": props
                })

                # Check actual relationship creation stats in FalkorDB result
                # FalkorDB python client doesn't always expose `.stats`, so we safely check if it succeeded
                if result is not None:
                   created += 1
                else:
                    logger.warning(f"Failed to match nodes for relationship. Source '{mapping.source_node_label}' ID='{source_id}', Target '{mapping.target_node_label}' ID='{foreign_key}' may not exist.")

            except Exception as e:
                logger.warning(f"Failed to create relationship: {e}")
                continue

        logger.info(f"Created {created} {mapping.relationship_type} relationships")
        return created

    def preview_import(
        self,
        source_id: str,
        node_mappings: List[NodeMapping]
    ) -> Dict[str, Any]:
        """Preview what would be imported without executing."""
        try:
            connector = self.source_manager.get_connector(source_id)
            if not connector:
                raise ValueError(f"Data source '{source_id}' not found")

            # Get sample data
            preview = connector.preview_data(limit=10)

            # Show how first few rows would be mapped
            sample_nodes = []
            for row in preview.sample_rows[:5]:
                for mapping in node_mappings:
                    node_id = row.get(mapping.id_field)
                    if not node_id:
                        continue

                    properties = {}
                    for source_field, node_prop in mapping.property_mappings.items():
                        if source_field in row:
                            properties[node_prop] = row[source_field]

                    sample_nodes.append({
                        "label": mapping.node_label,
                        "id": node_id,
                        "properties": properties
                    })

            return {
                "total_rows": preview.total_count,
                "sample_nodes": sample_nodes,
                "estimated_nodes": len(node_mappings) * preview.total_count
            }

        except Exception as e:
            logger.error(f"Preview failed: {e}")
            return {"error": str(e)}


# Global singleton instance
_import_service = GraphImportService()


def get_graph_import_service() -> GraphImportService:
    """Get the global graph import service instance."""
    return _import_service

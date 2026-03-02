"""
Graph Registry Service

Centralized registry of all available graphs in the compliance engine.
Tracks metadata, schema, and capabilities of each graph.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
from services.database import get_db_service

logger = logging.getLogger(__name__)


@dataclass
class GraphMetadata:
    """Metadata about a registered graph."""
    name: str
    graph_type: str  # "rules", "data_transfer", "external", "sandbox"
    description: str
    created_at: datetime
    node_labels: Set[str] = field(default_factory=set)
    relationship_types: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Custom metadata
    enabled: bool = True


class GraphRegistry:
    """Centralized registry of all available graphs."""

    _instance = None
    _graphs: Dict[str, GraphMetadata] = {}
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern to ensure one registry instance."""
        if cls._instance is None:
            cls._instance = super(GraphRegistry, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize registry with default graphs."""
        if self._initialized:
            return

        logger.info("Initializing GraphRegistry...")

        # Register default graphs
        self.register_graph(
            name="RulesGraph",
            graph_type="rules",
            description="Primary compliance rules and entity relationships",
            metadata={"is_default": True, "is_system": True}
        )

        self.register_graph(
            name="DataTransferGraph",
            graph_type="data_transfer",
            description="Data transfer scenarios for TIA/PIA/HRPR precedent search",
            metadata={"is_default": True, "is_system": True}
        )

        self._initialized = True
        logger.info(f"GraphRegistry initialized with {len(self._graphs)} graphs")

    def register_graph(
        self,
        name: str,
        graph_type: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> GraphMetadata:
        """Register a graph in the registry."""
        if name in self._graphs:
            logger.warning(f"Graph '{name}' already registered, updating...")

        try:
            db = get_db_service()
            graph = db.db.select_graph(name)

            # Introspect schema
            node_labels = self._get_node_labels(graph)
            rel_types = self._get_relationship_types(graph)

            graph_meta = GraphMetadata(
                name=name,
                graph_type=graph_type,
                description=description,
                created_at=datetime.now(),
                node_labels=node_labels,
                relationship_types=rel_types,
                metadata=metadata or {},
                enabled=True
            )

            self._graphs[name] = graph_meta
            logger.info(f"Registered graph '{name}' ({graph_type}) with {len(node_labels)} node types, {len(rel_types)} relationships")

            return graph_meta

        except Exception as e:
            logger.error(f"Failed to register graph '{name}': {e}")
            # Register with empty schema as fallback
            graph_meta = GraphMetadata(
                name=name,
                graph_type=graph_type,
                description=description,
                created_at=datetime.now(),
                node_labels=set(),
                relationship_types=set(),
                metadata=metadata or {},
                enabled=False
            )
            self._graphs[name] = graph_meta
            return graph_meta

    def list_graphs(self, graph_type: Optional[str] = None, enabled_only: bool = False) -> List[GraphMetadata]:
        """List all registered graphs, optionally filtered by type."""
        graphs = list(self._graphs.values())

        if graph_type:
            graphs = [g for g in graphs if g.graph_type == graph_type]

        if enabled_only:
            graphs = [g for g in graphs if g.enabled]

        return graphs

    def get_graph(self, name: str) -> Optional[GraphMetadata]:
        """Get graph metadata by name."""
        return self._graphs.get(name)

    def unregister_graph(self, name: str) -> bool:
        """Unregister a graph from the registry."""
        if name in self._graphs:
            # Don't allow unregistering system graphs
            if self._graphs[name].metadata.get("is_system"):
                logger.warning(f"Cannot unregister system graph '{name}'")
                return False

            del self._graphs[name]
            logger.info(f"Unregistered graph '{name}'")
            return True

        return False

    def enable_graph(self, name: str) -> bool:
        """Enable a graph for queries."""
        if name in self._graphs:
            self._graphs[name].enabled = True
            logger.info(f"Enabled graph '{name}'")
            return True
        return False

    def disable_graph(self, name: str) -> bool:
        """Disable a graph from queries."""
        if name in self._graphs:
            # Don't allow disabling RulesGraph (primary graph)
            if name == "RulesGraph":
                logger.warning("Cannot disable RulesGraph (primary graph)")
                return False

            self._graphs[name].enabled = False
            logger.info(f"Disabled graph '{name}'")
            return True
        return False

    def refresh_schema(self, name: str) -> bool:
        """Refresh node labels and relationship types for a graph."""
        if name not in self._graphs:
            logger.warning(f"Graph '{name}' not found")
            return False

        try:
            db = get_db_service()
            graph = db.db.select_graph(name)

            self._graphs[name].node_labels = self._get_node_labels(graph)
            self._graphs[name].relationship_types = self._get_relationship_types(graph)

            logger.info(f"Refreshed schema for graph '{name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh schema for '{name}': {e}")
            return False

    def _get_node_labels(self, graph) -> Set[str]:
        """Query graph to get all node labels."""
        try:
            result = graph.query("CALL db.labels()")
            return {row[0] for row in result.result_set if row}
        except Exception as e:
            logger.warning(f"Failed to get node labels: {e}")
            return set()

    def _get_relationship_types(self, graph) -> Set[str]:
        """Query graph to get all relationship types."""
        try:
            result = graph.query("CALL db.relationshipTypes()")
            return {row[0] for row in result.result_set if row}
        except Exception as e:
            logger.warning(f"Failed to get relationship types: {e}")
            return set()

    def get_graphs_with_node_label(self, node_label: str) -> List[str]:
        """Find all graphs containing a specific node label."""
        return [
            name for name, meta in self._graphs.items()
            if node_label in meta.node_labels and meta.enabled
        ]

    def get_graphs_with_relationship(self, rel_type: str) -> List[str]:
        """Find all graphs containing a specific relationship type."""
        return [
            name for name, meta in self._graphs.items()
            if rel_type in meta.relationship_types and meta.enabled
        ]


# Global singleton instance
_registry = GraphRegistry()


def get_graph_registry() -> GraphRegistry:
    """Get the global graph registry instance."""
    if not _registry._initialized:
        _registry.initialize()
    return _registry

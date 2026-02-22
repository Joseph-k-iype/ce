"""
Database Service
================
Handles FalkorDB connections and query execution.
Supports both RulesGraph and DataTransferGraph.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import time
import uuid

from falkordb import FalkorDB
from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    FalkorDB database service for managing graph connections and queries.
    Supports connection pooling and query timeout management.
    """

    _instance: Optional['DatabaseService'] = None
    _db: Optional[FalkorDB] = None

    def __new__(cls):
        """Singleton pattern for database service"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize database connection"""
        if self._initialized:
            return

        self._connect()
        self._initialized = True

    def _connect(self):
        """Establish database connection"""
        try:
            self._db = FalkorDB(
                host=settings.database.host,
                port=settings.database.port,
                password=settings.database.password
            )
            logger.info(f"Connected to FalkorDB at {settings.database.host}:{settings.database.port}")
        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            raise

    @property
    def db(self) -> FalkorDB:
        """Get database connection"""
        if self._db is None:
            self._connect()
        return self._db

    def get_rules_graph(self):
        """Get the RulesGraph instance"""
        return self.db.select_graph(settings.database.rules_graph_name)

    def get_data_graph(self):
        """Get the DataTransferGraph instance"""
        return self.db.select_graph(settings.database.data_graph_name)

    def get_temp_graph(self, suffix: Optional[str] = None) -> Tuple[Any, str]:
        """
        Get a temporary graph for testing.
        Returns tuple of (graph, graph_name).
        """
        if suffix is None:
            suffix = str(uuid.uuid4())[:8]
        graph_name = f"{settings.database.temp_graph_prefix}{suffix}"
        return self.db.select_graph(graph_name), graph_name

    def delete_temp_graph(self, graph_name: str) -> bool:
        """Delete a temporary graph"""
        try:
            if graph_name.startswith(settings.database.temp_graph_prefix):
                graph = self.db.select_graph(graph_name)
                graph.delete()
                logger.info(f"Deleted temporary graph: {graph_name}")
                return True
            else:
                logger.warning(f"Refusing to delete non-temporary graph: {graph_name}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete graph {graph_name}: {e}")
            return False

    def cleanup_stale_temp_graphs(self) -> int:
        """Delete all temporary graphs. Call on startup or after workflow errors."""
        cleaned = 0
        prefix = settings.database.temp_graph_prefix
        try:
            graphs = self.db.list_graphs()
            for graph_name in graphs:
                if graph_name.startswith(prefix):
                    try:
                        graph = self.db.select_graph(graph_name)
                        graph.delete()
                        cleaned += 1
                        logger.info(f"Cleaned stale temp graph: {graph_name}")
                    except Exception as e:
                        logger.warning(f"Failed to clean temp graph {graph_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to list graphs for cleanup: {e}")
        return cleaned

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        graph_name: Optional[str] = None,
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            params: Query parameters
            graph_name: Target graph name (defaults to data graph)
            timeout_ms: Query timeout in milliseconds

        Returns:
            List of result dictionaries
        """
        if timeout_ms is None:
            timeout_ms = settings.api.default_query_timeout_ms

        if graph_name is None:
            graph = self.get_data_graph()
        elif graph_name == settings.database.rules_graph_name:
            graph = self.get_rules_graph()
        else:
            graph = self.db.select_graph(graph_name)

        start_time = time.time()
        try:
            if params:
                result = graph.query(query, params, timeout=timeout_ms)
            else:
                result = graph.query(query, timeout=timeout_ms)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"Query executed in {elapsed_ms:.2f}ms")

            return self._process_result(result)

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Query failed after {elapsed_ms:.2f}ms: {e}")
            raise

    def execute_rules_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Execute query on the RulesGraph"""
        return self.execute_query(
            query,
            params,
            graph_name=settings.database.rules_graph_name,
            timeout_ms=timeout_ms
        )

    def execute_data_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Execute query on the DataTransferGraph"""
        return self.execute_query(
            query,
            params,
            graph_name=settings.database.data_graph_name,
            timeout_ms=timeout_ms
        )

    def _process_result(self, result) -> List[Dict[str, Any]]:
        """Process query result into list of dictionaries"""
        if result is None:
            return []

        processed = []
        raw_headers = result.header if hasattr(result, 'header') else []

        # Convert headers to strings (FalkorDB may return tuples/lists for complex return types)
        headers = []
        for h in raw_headers:
            if isinstance(h, (list, tuple)):
                # Join tuple/list elements or take the last element (usually the alias)
                headers.append(str(h[-1]) if h else f"col_{len(headers)}")
            else:
                headers.append(str(h) if h is not None else f"col_{len(headers)}")

        result_set = result.result_set if hasattr(result, 'result_set') else []

        for row in result_set:
            row_dict = {}
            for i, value in enumerate(row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_dict[key] = self._convert_value(value)
            processed.append(row_dict)

        return processed

    def _convert_value(self, value: Any) -> Any:
        """Convert FalkorDB value types to Python types"""
        if value is None:
            return None

        # Handle Node type
        if hasattr(value, 'properties'):
            props = dict(value.properties)
            props['_labels'] = list(value.labels) if hasattr(value, 'labels') else []
            return props

        # Handle Edge type
        if hasattr(value, 'relation'):
            return {
                '_type': 'edge',
                'relation': value.relation,
                'properties': dict(value.properties) if hasattr(value, 'properties') else {}
            }

        # Handle list
        if isinstance(value, list):
            return [self._convert_value(v) for v in value]

        return value

    def check_connection(self) -> bool:
        """Check if database connection is healthy"""
        try:
            self.execute_query("RETURN 1 as test")
            return True
        except Exception:
            return False

    def check_rules_graph(self) -> bool:
        """Check if RulesGraph exists and has data"""
        try:
            result = self.execute_rules_query("MATCH (n) RETURN count(n) as count LIMIT 1")
            return len(result) > 0 and result[0].get('count', 0) > 0
        except Exception:
            return False

    def check_data_graph(self) -> bool:
        """Check if DataTransferGraph exists and has data"""
        try:
            result = self.execute_data_query("MATCH (n) RETURN count(n) as count LIMIT 1")
            return len(result) > 0 and result[0].get('count', 0) > 0
        except Exception:
            return False

    def get_graph_stats(self, graph_name: Optional[str] = None) -> Dict[str, int]:
        """Get node and edge counts for a graph"""
        try:
            # Get node count
            node_query = "MATCH (n) RETURN count(n) as node_count"
            node_result = self.execute_query(node_query, graph_name=graph_name)
            node_count = node_result[0].get('node_count', 0) if node_result else 0

            # Get edge count separately to avoid issues with empty graphs
            edge_query = "MATCH ()-[r]->() RETURN count(r) as edge_count"
            edge_result = self.execute_query(edge_query, graph_name=graph_name)
            edge_count = edge_result[0].get('edge_count', 0) if edge_result else 0

            return {
                'node_count': node_count,
                'edge_count': edge_count
            }
        except Exception as e:
            logger.warning(f"Failed to get graph stats: {e}")
            return {'node_count': 0, 'edge_count': 0}


# Lazy singleton instance
_db_service: DatabaseService | None = None


def get_db_service() -> DatabaseService:
    """Get the database service instance (lazy initialization)."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service

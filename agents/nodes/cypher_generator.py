"""
Cypher Generator Node
======================
Thin shim: wraps CypherGeneratorExecutor as a LangGraph node function.
Injects DatabaseService for FalkorDB syntax validation.
"""

from agents.executors.cypher_generator_executor import CypherGeneratorExecutor
from agents.executors.base_executor import wrap_executor_as_node
from services.database import get_db_service

_executor = CypherGeneratorExecutor(db_service=None)
_node_fn = wrap_executor_as_node(_executor)


def cypher_generator_node(state):
    """Lazy-init db_service on first call, then delegate to wrapped executor."""
    if _executor.db_service is None:
        _executor.db_service = get_db_service()
    return _node_fn(state)

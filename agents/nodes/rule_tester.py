"""
Rule Tester Node
=================
Thin shim: wraps RuleTesterExecutor as a LangGraph node function.
Injects DatabaseService for FalkorDB temp graph testing.
"""

from agents.executors.rule_tester_executor import RuleTesterExecutor
from agents.executors.base_executor import wrap_executor_as_node
from services.database import get_db_service

_executor = RuleTesterExecutor(db_service=None)
_node_fn = wrap_executor_as_node(_executor)


def rule_tester_node(state):
    """Lazy-init db_service on first call, then delegate to wrapped executor."""
    if _executor.db_service is None:
        _executor.db_service = get_db_service()
    return _node_fn(state)

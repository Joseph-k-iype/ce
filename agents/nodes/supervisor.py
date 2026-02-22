"""
Supervisor Node
================
Thin shim: wraps SupervisorExecutor as a LangGraph node function.
"""

from agents.executors.supervisor_executor import SupervisorExecutor
from agents.executors.base_executor import wrap_executor_as_node

_executor = SupervisorExecutor()
supervisor_node = wrap_executor_as_node(_executor)

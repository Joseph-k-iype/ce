"""
Data Dictionary Node
=====================
Thin shim: wraps DataDictionaryExecutor as a LangGraph node function.
"""

from agents.executors.data_dictionary_executor import DataDictionaryExecutor
from agents.executors.base_executor import wrap_executor_as_node

_executor = DataDictionaryExecutor()
data_dictionary_node = wrap_executor_as_node(_executor)

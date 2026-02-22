"""
Rule Analyzer Node
===================
Thin shim: wraps RuleAnalyzerExecutor as a LangGraph node function.
"""

from agents.executors.rule_analyzer_executor import RuleAnalyzerExecutor
from agents.executors.base_executor import wrap_executor_as_node

_executor = RuleAnalyzerExecutor()
rule_analyzer_node = wrap_executor_as_node(_executor)

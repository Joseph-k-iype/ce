"""
Supervisor Executor
====================
Orchestrates the wizard workflow, manages routing decisions.
Implements Google A2A SDK AgentExecutor interface.
"""

import json
import logging

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.supervisor_prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    SUPERVISOR_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_supervisor_prompt
from agents.audit.event_types import AuditEventType
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)


def _compress_agent_outputs(agent_outputs: dict) -> dict:
    """Compress agent outputs to summary-only for retry iterations.

    Instead of sending full outputs on every supervisor call, send only
    existence flags and key metrics to reduce prompt size.
    """
    compressed = {}
    for key, value in agent_outputs.items():
        if value is None:
            compressed[key] = None
        elif isinstance(value, dict):
            # Extract just the key summary fields
            summary = {"_present": True}
            for field in ("rule_id", "name", "rule_type", "outcome", "overall_valid",
                          "confidence_score", "skipped", "total", "passed", "failed",
                          "auto_completed", "reason"):
                if field in value:
                    summary[field] = value[field]
            compressed[key] = summary
        else:
            compressed[key] = str(value)[:200]
    return compressed


class SupervisorExecutor(ComplianceAgentExecutor):
    """Supervisor agent executor - orchestrates workflow routing."""

    agent_name = "supervisor"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state

        await self.emit_working(event_queue, ctx)
        self.record_invocation(state)

        session_id = state.get("origin_country", "unknown")

        # Build agent outputs summary — compress on retry iterations to reduce prompt size
        agent_outputs = {
            "analysis_result": state.get("analysis_result"),
            "dictionary_result": state.get("dictionary_result"),
            "rule_definition": state.get("rule_definition"),
            "cypher_queries": state.get("cypher_queries"),
            "validation_result": state.get("validation_result"),
        }
        iteration = state.get("iteration", 0)
        if iteration > 0:
            agent_outputs = _compress_agent_outputs(agent_outputs)

        # Limit shared_reasoning to last 2 entries on retries to reduce prompt bloat
        shared_reasoning = state.get("shared_reasoning", [])
        if iteration > 0 and len(shared_reasoning) > 2:
            state["shared_reasoning"] = shared_reasoning[-2:]

        validation_status = "Not yet validated"
        if state.get("validation_result"):
            v = state["validation_result"]
            validation_status = (
                f"Valid: {v.get('overall_valid', False)}, "
                f"Confidence: {v.get('confidence_score', 0)}"
            )

        user_prompt = build_supervisor_prompt(
            template=SUPERVISOR_USER_TEMPLATE,
            rule_text=state.get("rule_text", ""),
            origin_country=state.get("origin_country", ""),
            scenario_type=state.get("scenario_type", "transfer"),
            receiving_countries=state.get("receiving_countries", []),
            data_categories=state.get("data_categories", []),
            current_phase=state.get("current_phase", "supervisor"),
            iteration=state.get("iteration", 0),
            max_iterations=state.get("max_iterations", 10),
            agent_outputs=agent_outputs,
            validation_status=validation_status,
            feedback="",
            graph_step=state.get("graph_step", 0),
            agent_retry_counts=state.get("agent_retry_counts", {}),
        )

        try:
            response = self.call_ai_with_retry(user_prompt, SUPERVISOR_SYSTEM_PROMPT)
            parsed = parse_json_response(response)

            if parsed:
                next_agent = parsed.get("next_agent") or "fail"
                reasoning = parsed.get("reasoning", "")

                # Validate the next agent is a known route
                valid_agents = {
                    "rule_analyzer", "data_dictionary", "cypher_generator",
                    "validator", "reference_data", "rule_tester", "human_review", "complete", "fail"
                }
                if next_agent not in valid_agents:
                    logger.warning(f"Supervisor returned unknown agent '{next_agent}', defaulting to 'fail'")
                    next_agent = "fail"

                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.AGENT_COMPLETED,
                    agent_name=self.agent_name,
                    data={"next_agent": next_agent, "reasoning": reasoning},
                )

                state["current_phase"] = next_agent

                # Track per-agent invocations for circuit breaker
                if next_agent not in ("complete", "fail", "human_review", "supervisor"):
                    counts = state.get("agent_retry_counts", {})
                    counts[next_agent] = counts.get(next_agent, 0) + 1
                    state["agent_retry_counts"] = counts

                logger.info(
                    f"Supervisor routing to: {next_agent} "
                    f"(iteration {state.get('iteration', 0)}, "
                    f"step {state.get('graph_step', 0)}) - {reasoning}"
                )
            else:
                state["current_phase"] = "fail"
                state["error_message"] = "Supervisor failed to produce valid response"

        except AIRequestError as e:
            logger.error(f"Supervisor error: {e}")
            state["current_phase"] = "fail"
            state["error_message"] = str(e)

        await self.emit_completed(event_queue, ctx)

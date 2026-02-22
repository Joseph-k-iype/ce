"""
Rule Analyzer Executor
=======================
Chain of Thought reasoning to extract rule structure from text.
Implements Google A2A SDK AgentExecutor interface.
"""

import logging
import time
import uuid

from pydantic import ValidationError

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.analyzer_prompts import (
    RULE_ANALYZER_SYSTEM_PROMPT,
    RULE_ANALYZER_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_analyzer_prompt, build_country_groups_context, build_graph_entities_context
from agents.audit.event_types import AuditEventType
from agents.nodes.validation_models import RuleDefinitionModel
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)


class RuleAnalyzerExecutor(ComplianceAgentExecutor):
    """Rule analyzer agent executor - extracts rule structure via CoT."""

    agent_name = "rule_analyzer"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state
        start_time = time.time()
        session_id = state.get("origin_country", "unknown")

        await self.emit_working(event_queue, ctx)
        self.record_invocation(state)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        system_prompt = RULE_ANALYZER_SYSTEM_PROMPT.format(
            country_groups=build_country_groups_context(),
            graph_entities=build_graph_entities_context(),
        )

        user_prompt = build_analyzer_prompt(
            template=RULE_ANALYZER_USER_TEMPLATE,
            rule_text=state.get("rule_text", ""),
            origin_country=state.get("origin_country", ""),
            receiving_countries=state.get("receiving_countries", []),
            scenario_type=state.get("scenario_type", "transfer"),
            data_categories=state.get("data_categories", []),
            feedback="",
            is_pii_related=state.get("is_pii_related", False),
        )

        try:
            response = self.call_ai_with_retry(user_prompt, system_prompt)
            parsed = parse_json_response(response)

            if parsed:
                state["analysis_result"] = {
                    "chain_of_thought": parsed.get("chain_of_thought", {}),
                    "tree_of_thought": parsed.get("tree_of_thought", {}),
                    "expert_perspectives": parsed.get("expert_perspectives", {}),
                    "confidence": parsed.get("confidence"),
                }

                rule_def = parsed.get("rule_definition", {})

                # Merge suggested_linked_entities into rule_def for downstream agents
                suggested_entities = parsed.get("suggested_linked_entities", {})
                if suggested_entities:
                    rule_def["suggested_linked_entities"] = suggested_entities

                # Auto-generate rule_id if AI returned placeholder
                raw_id = rule_def.get("rule_id", "")
                if not raw_id or "<" in raw_id or "unique_id" in raw_id.lower():
                    short_id = uuid.uuid4().hex[:8].upper()
                    rule_def["rule_id"] = f"RULE_{short_id}"

                # Normalise priority to high/medium/low
                raw_priority = rule_def.get("priority", "medium")
                if isinstance(raw_priority, (int, float)):
                    if raw_priority <= 33:
                        rule_def["priority"] = "high"
                    elif raw_priority <= 66:
                        rule_def["priority"] = "medium"
                    else:
                        rule_def["priority"] = "low"
                elif isinstance(raw_priority, str) and raw_priority not in ("high", "medium", "low"):
                    rule_def["priority"] = "medium"

                try:
                    validated = RuleDefinitionModel(**rule_def)
                    state["rule_definition"] = validated.model_dump()
                    self.record_success(state)
                    state["current_phase"] = (
                        "data_dictionary" if state.get("data_categories") else "cypher_generator"
                    )

                    duration = (time.time() - start_time) * 1000
                    self.event_store.append(
                        session_id=session_id,
                        event_type=AuditEventType.RULE_ANALYZED,
                        agent_name=self.agent_name,
                        data={"rule_id": rule_def.get("rule_id")},
                        duration_ms=duration,
                    )
                    logger.info(f"Rule analyzed: {rule_def.get('rule_id')}")

                    # Populate shared_reasoning
                    state.setdefault("shared_reasoning", []).append({
                        "agent": self.agent_name,
                        "summary": f"Analyzed rule '{rule_def.get('name', '')}' ({rule_def.get('rule_id', '')})",
                        "key_findings": [
                            f"Rule type: {rule_def.get('rule_type', 'unknown')}",
                            f"Outcome: {rule_def.get('outcome', 'unknown')}",
                            f"Origin: {rule_def.get('origin_group', '') or ', '.join(rule_def.get('origin_countries', []) or [])}",
                            f"Requires PII: {rule_def.get('requires_pii', False)}",
                            f"Confidence: {parsed.get('confidence', 'N/A')}",
                        ],
                    })

                except ValidationError as ve:
                    errors = [str(e) for e in ve.errors()]
                    self.record_failure(state, f"Validation errors: {errors}")
                    state["current_phase"] = "supervisor"
                    state["iteration"] = state.get("iteration", 0) + 1
                    self.event_store.append(
                        session_id=session_id,
                        event_type=AuditEventType.AGENT_FAILED,
                        agent_name=self.agent_name,
                        error=f"Validation errors: {errors}",
                    )
                    logger.warning(f"Rule validation failed: {errors}")
            else:
                self.record_failure(state, "Failed to parse response")
                state["current_phase"] = "supervisor"
                state["iteration"] = state.get("iteration", 0) + 1
                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.AGENT_FAILED,
                    agent_name=self.agent_name,
                    error="Failed to parse response",
                )

        except AIRequestError as e:
            logger.error(f"Rule analyzer error: {e}")
            self.record_failure(state, str(e))
            state["current_phase"] = "supervisor"
            state["iteration"] = state.get("iteration", 0) + 1
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_FAILED,
                agent_name=self.agent_name,
                error=str(e),
            )

        await self.emit_completed(event_queue, ctx)

"""
Data Dictionary Executor
=========================
Generates keyword dictionaries per data category.
Implements Google A2A SDK AgentExecutor interface.
"""

import logging
import time

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.dictionary_prompts import (
    DICTIONARY_SYSTEM_PROMPT,
    DICTIONARY_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_dictionary_prompt
from agents.audit.event_types import AuditEventType
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)


class DataDictionaryExecutor(ComplianceAgentExecutor):
    """Data dictionary agent executor - generates keyword dictionaries."""

    agent_name = "data_dictionary"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state
        start_time = time.time()
        session_id = state.get("origin_country", "unknown")

        # Skip if no data categories
        if not state.get("data_categories"):
            state["current_phase"] = "cypher_generator"
            state["dictionary_result"] = {"skipped": True, "reason": "No data categories specified"}
            await self.emit_completed(event_queue, ctx)
            return

        await self.emit_working(event_queue, ctx)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        user_prompt = build_dictionary_prompt(
            template=DICTIONARY_USER_TEMPLATE,
            data_categories=state.get("data_categories", []),
            rule_text=state.get("rule_text", ""),
            origin_country=state.get("origin_country", ""),
            scenario_type=state.get("scenario_type", "transfer"),
            feedback="",
            is_pii_related=state.get("is_pii_related", False),
        )

        try:
            response = self.call_ai_with_retry(user_prompt, DICTIONARY_SYSTEM_PROMPT)
            parsed = parse_json_response(response)

            if parsed:
                state["dictionary_result"] = parsed
                state["current_phase"] = "cypher_generator"

                duration = (time.time() - start_time) * 1000
                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.DICTIONARY_GENERATED,
                    agent_name=self.agent_name,
                    data={"categories": list(parsed.get("dictionaries", {}).keys())},
                    duration_ms=duration,
                )
                logger.info("Dictionary generated successfully")

                # Populate shared_reasoning
                categories = list(parsed.get("dictionaries", {}).keys())
                total_keywords = sum(
                    len(v.get("keywords", []))
                    for v in parsed.get("dictionaries", {}).values()
                    if isinstance(v, dict)
                )
                state.setdefault("shared_reasoning", []).append({
                    "agent": self.agent_name,
                    "summary": f"Generated dictionaries for {len(categories)} categories with ~{total_keywords} keywords",
                    "key_findings": [
                        f"Categories: {', '.join(categories[:5])}",
                        f"Total keyword entries: ~{total_keywords}",
                    ],
                })
            else:
                state["current_phase"] = "supervisor"
                state["iteration"] = state.get("iteration", 0) + 1
                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.AGENT_FAILED,
                    agent_name=self.agent_name,
                    error="Failed to parse response",
                )

        except AIRequestError as e:
            logger.error(f"Data dictionary error: {e}")
            state["current_phase"] = "supervisor"
            state["iteration"] = state.get("iteration", 0) + 1
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_FAILED,
                agent_name=self.agent_name,
                error=str(e),
            )

        await self.emit_completed(event_queue, ctx)

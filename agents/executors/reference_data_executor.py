"""
Reference Data Executor
========================
Creates country groups and attribute configurations.
Supports FalkorDB queries for existing group lookup.
Implements Google A2A SDK AgentExecutor interface.
"""

import logging
import time

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.reference_prompts import (
    REFERENCE_DATA_SYSTEM_PROMPT,
    REFERENCE_DATA_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_reference_prompt, build_country_groups_context
from agents.audit.event_types import AuditEventType
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)


class ReferenceDataExecutor(ComplianceAgentExecutor):
    """Reference data agent executor - manages country groups and attribute configs."""

    agent_name = "reference_data"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state
        start_time = time.time()
        session_id = state.get("origin_country", "unknown")

        if not state.get("rule_definition"):
            state["current_phase"] = "supervisor"
            await self.emit_completed(event_queue, ctx)
            return

        await self.emit_working(event_queue, ctx)
        self.record_invocation(state)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        # Optionally enrich country groups context from FalkorDB
        country_groups_context = build_country_groups_context()
        if self.db_service:
            country_groups_context = self._enrich_from_db(country_groups_context)

        system_prompt = REFERENCE_DATA_SYSTEM_PROMPT.format(
            country_groups=country_groups_context
        )

        user_prompt = build_reference_prompt(
            template=REFERENCE_DATA_USER_TEMPLATE,
            rule_definition=state.get("rule_definition", {}),
            rule_text=state.get("rule_text", ""),
            feedback="",
        )

        try:
            response = self.call_ai_with_retry(user_prompt, system_prompt)
            parsed = parse_json_response(response)

            if parsed:
                self.record_success(state)
                actions = parsed.get("actions_needed", [])
                duration = (time.time() - start_time) * 1000

                if not actions or parsed.get("no_action_needed"):
                    state["current_phase"] = "supervisor"
                    self.event_store.append(
                        session_id=session_id,
                        event_type=AuditEventType.AGENT_COMPLETED,
                        agent_name=self.agent_name,
                        data={"actions": 0, "message": "No reference data needed"},
                        duration_ms=duration,
                    )
                else:
                    state["requires_human_input"] = True
                    state["current_phase"] = "human_review"
                    self.event_store.append(
                        session_id=session_id,
                        event_type=AuditEventType.REFERENCE_DATA_CREATED,
                        agent_name=self.agent_name,
                        data={"actions": len(actions), "details": actions},
                        duration_ms=duration,
                    )
                    await self.emit_input_required(event_queue, ctx)

                logger.info(f"Reference data check complete: {len(actions)} actions needed")
            else:
                state["current_phase"] = "supervisor"

        except AIRequestError as e:
            logger.error(f"Reference data error: {e}")
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

    def _enrich_from_db(self, base_context: str) -> str:
        """Query FalkorDB for existing country groups to enrich the context."""
        try:
            results = self.db_service.execute_rules_query(
                "MATCH (g:CountryGroup) RETURN g.name AS name"
            )
            if results:
                db_groups = [r.get("name") for r in results if r.get("name")]
                if db_groups:
                    return base_context + f"\n\nExisting groups in FalkorDB: {', '.join(db_groups)}"
        except Exception as e:
            logger.debug(f"Could not query FalkorDB for country groups: {e}")
        return base_context

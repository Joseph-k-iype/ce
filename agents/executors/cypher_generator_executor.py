"""
Cypher Generator Executor
===========================
Mixture of Experts Cypher query generation with FalkorDB syntax validation.
Implements Google A2A SDK AgentExecutor interface.
"""

import logging
import time

from pydantic import ValidationError

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.cypher_prompts import (
    CYPHER_GENERATOR_SYSTEM_PROMPT,
    CYPHER_GENERATOR_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_cypher_prompt, build_graph_entities_context
from agents.audit.event_types import AuditEventType
from agents.nodes.validation_models import CypherQueriesModel
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)


class CypherGeneratorExecutor(ComplianceAgentExecutor):
    """Cypher generator agent executor - MoE query generation with FalkorDB validation."""

    agent_name = "cypher_generator"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state
        start_time = time.time()
        session_id = state.get("origin_country", "unknown")

        # Guard: require rule_definition before generating Cypher
        if not state.get("rule_definition"):
            state["current_phase"] = "supervisor"
            return

        await self.emit_working(event_queue, ctx)
        self.record_invocation(state)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        system_prompt = CYPHER_GENERATOR_SYSTEM_PROMPT.format(
            graph_entities=build_graph_entities_context(),
        )

        user_prompt = build_cypher_prompt(
            template=CYPHER_GENERATOR_USER_TEMPLATE,
            rule_definition=state.get("rule_definition", {}),
            feedback="",
        )

        try:
            response = self.call_ai_with_retry(user_prompt, system_prompt)
            parsed = parse_json_response(response)

            if parsed:
                queries = parsed.get("cypher_queries", {})
                try:
                    validated = CypherQueriesModel(**queries)
                    # Sanitize query_params keys: strip $ prefix and embedded quotes
                    # that LLMs sometimes produce (e.g. "$rule_id" or '"rule_id"')
                    raw_params = parsed.get("query_params", {})
                    sanitized_params = {}
                    for k, v in raw_params.items():
                        clean_key = k.strip().strip('"').strip("'").lstrip('$')
                        if clean_key:
                            sanitized_params[clean_key] = v
                    state["cypher_queries"] = {
                        "queries": validated.model_dump(),
                        "params": sanitized_params,
                        "optimization_notes": parsed.get("optimization_notes", []),
                    }

                    # FalkorDB syntax validation via EXPLAIN
                    if self.db_service:
                        syntax_ok = self._validate_cypher_syntax(validated, session_id)
                        if not syntax_ok:
                            logger.warning("Cypher EXPLAIN validation failed, routing back to supervisor for retry")
                            state["current_phase"] = "supervisor"
                            state["iteration"] = state.get("iteration", 0) + 1
                            await self.emit_completed(event_queue, ctx)
                            return

                    self.record_success(state)
                    state["current_phase"] = "validator"

                    duration = (time.time() - start_time) * 1000
                    self.event_store.append(
                        session_id=session_id,
                        event_type=AuditEventType.CYPHER_GENERATED,
                        agent_name=self.agent_name,
                        duration_ms=duration,
                    )
                    logger.info("Cypher queries generated successfully")

                    # Populate shared_reasoning
                    query_names = list(validated.model_dump().keys())
                    state.setdefault("shared_reasoning", []).append({
                        "agent": self.agent_name,
                        "summary": f"Generated {len(query_names)} Cypher queries",
                        "key_findings": [
                            f"Queries: {', '.join(query_names)}",
                            f"Optimization notes: {len(parsed.get('optimization_notes', []))} notes",
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
            logger.error(f"Cypher generator error: {e}")
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

    def _validate_cypher_syntax(
        self,
        queries: CypherQueriesModel,
        session_id: str,
    ) -> bool:
        """Validate generated Cypher queries for FalkorDB compatibility.

        FalkorDB's EXPLAIN requires actual parameter values, so we do
        structural validation instead of running EXPLAIN with $params.
        Returns True if all queries pass, False if any fail.
        """
        all_passed = True
        for query_name in ("rule_check", "rule_insert", "validation"):
            cypher = getattr(queries, query_name)
            errors = []

            # Check for multi-statement (semicolons inside the query body)
            stripped = cypher.strip().rstrip(';')
            if ';' in stripped:
                errors.append("Multiple statements not supported — remove semicolons")

            # Check for EXISTS { MATCH ... } subquery syntax
            import re
            if re.search(r'EXISTS\s*\{', cypher, re.IGNORECASE):
                errors.append("EXISTS { } subqueries not supported — use OPTIONAL MATCH instead")

            # Check for CALL { } subquery syntax
            if re.search(r'CALL\s*\{', cypher, re.IGNORECASE):
                errors.append("CALL { } subqueries not supported")

            # Check for UNION
            if re.search(r'\bUNION\b', cypher, re.IGNORECASE):
                errors.append("UNION not supported in single query")

            if errors:
                all_passed = False
                error_msg = f"Cypher validation failed for {query_name}: {'; '.join(errors)}"
                logger.warning(error_msg)
                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.AGENT_FAILED,
                    agent_name=self.agent_name,
                    error=error_msg,
                )
            else:
                logger.debug(f"Structural validation passed for {query_name}")

        return all_passed

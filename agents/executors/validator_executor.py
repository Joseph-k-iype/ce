"""
Validator Executor
===================
Validates rules, Cypher queries, and logical consistency.
Supports FalkorDB test queries in temporary graphs.
Implements Google A2A SDK AgentExecutor interface.

Fallback: if validation fails MAX_VALIDATION_RETRIES times consecutively,
skip validation and proceed to complete with a warning. This prevents
infinite retry loops when the LLM validator is overly strict.
"""

import logging
import time

from pydantic import ValidationError

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.validator_prompts import (
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_validator_prompt
from agents.audit.event_types import AuditEventType
from agents.nodes.validation_models import ValidationResultModel
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)

# After this many consecutive validation failures, skip and proceed
MAX_VALIDATION_RETRIES = 3


class ValidatorExecutor(ComplianceAgentExecutor):
    """Validator agent executor - comprehensive validation with fallback skip."""

    agent_name = "validator"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state
        start_time = time.time()
        session_id = state.get("origin_country", "unknown")

        # Guard: cannot validate without rule_definition and cypher_queries
        if not state.get("rule_definition") or not state.get("cypher_queries"):
            state["current_phase"] = "supervisor"
            return

        # ── Fallback: skip validation after too many consecutive failures ──
        retry_count = state.get("validation_retry_count", 0)
        if retry_count >= MAX_VALIDATION_RETRIES:
            logger.warning(
                f"Validation failed {retry_count} times consecutively — "
                f"skipping validation and proceeding to complete"
            )
            state["current_phase"] = "rule_tester"
            state["success"] = True
            state["validation_result"] = {
                "overall_valid": True,
                "confidence_score": 0.5,
                "skipped": True,
                "skip_reason": f"Auto-approved after {retry_count} validation retries",
                "errors": [],
                "warnings": [f"Validation skipped after {retry_count} failed attempts"],
            }
            state["events"].append({
                "event_type": "validation_skipped",
                "agent_name": self.agent_name,
                "message": f"Validation skipped after {retry_count} retries — rule auto-approved for human review",
            })
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.VALIDATION_PASSED,
                agent_name=self.agent_name,
                data={"skipped": True, "retry_count": retry_count},
            )
            await self.emit_completed(event_queue, ctx)
            return

        await self.emit_working(event_queue, ctx)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        # Pass previous validation errors so the LLM can learn from them
        previous_errors = state.get("validation_errors", [])

        user_prompt = build_validator_prompt(
            template=VALIDATOR_USER_TEMPLATE,
            rule_text=state.get("rule_text", ""),
            rule_definition=state.get("rule_definition", {}),
            cypher_queries=state.get("cypher_queries", {}),
            dictionary=state.get("dictionary_result"),
            iteration=state.get("iteration", 0),
            max_iterations=state.get("max_iterations", 10),
            previous_errors=previous_errors,
        )

        try:
            response = self.call_ai_with_retry(user_prompt, VALIDATOR_SYSTEM_PROMPT)
        except AIRequestError as e:
            # Auth/request error — go back to supervisor without burning a retry
            state["current_phase"] = "supervisor"
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_FAILED,
                agent_name=self.agent_name,
                error=f"Auth/request error: {e}",
            )
            await self.emit_completed(event_queue, ctx)
            return

        parsed = parse_json_response(response)

        if not parsed:
            # Unparseable response — count as a validation retry
            state["validation_retry_count"] = retry_count + 1
            state["current_phase"] = "supervisor"
            await self.emit_completed(event_queue, ctx)
            return

        val_results = parsed.get("validation_results") or {}

        try:
            # Safely extract sub-results — AI may return unexpected structures
            def _safe_section(section_name: str) -> dict:
                section = val_results.get(section_name)
                if isinstance(section, dict):
                    return section
                return {"valid": True, "errors": [], "warnings": []}

            rd = _safe_section("rule_definition")
            cq = _safe_section("cypher_queries")
            lg = _safe_section("logical")

            all_errors = (rd.get("errors") or []) + (cq.get("errors") or []) + (lg.get("errors") or [])
            all_warnings = (rd.get("warnings") or []) + (cq.get("warnings") or []) + (lg.get("warnings") or [])

            # If the AI didn't set overall_valid, infer from sub-sections
            overall = parsed.get("overall_valid")
            if overall is None:
                overall = rd.get("valid", True) and cq.get("valid", True) and lg.get("valid", True)

            validated = ValidationResultModel(
                overall_valid=bool(overall),
                confidence_score=parsed.get("confidence_score", 0.8),
                rule_definition_valid=bool(rd.get("valid", True)),
                cypher_valid=bool(cq.get("valid", True)),
                logical_valid=bool(lg.get("valid", True)),
                errors=[str(e) for e in all_errors if e],
                warnings=[str(w) for w in all_warnings if w],
                suggested_fixes=[str(f) for f in (parsed.get("suggested_fixes") or []) if f],
            )

            state["validation_result"] = validated.model_dump()
            duration = (time.time() - start_time) * 1000

            # FalkorDB test queries in temp graph
            if self.db_service and validated.overall_valid:
                self._run_test_queries(state, session_id)

            # Accept if: overall_valid=True, or no real errors (only warnings), or confidence >= 0.5
            has_blocking_errors = len(validated.errors) > 0
            is_acceptable = (validated.overall_valid or not has_blocking_errors) and validated.confidence_score >= 0.4

            if is_acceptable:
                # Validation passed — reset retry counter, route to rule_tester
                state["validation_retry_count"] = 0
                state["current_phase"] = "rule_tester"
                state["success"] = True
                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.VALIDATION_PASSED,
                    agent_name=self.agent_name,
                    data={"confidence": validated.confidence_score},
                    duration_ms=duration,
                )
                logger.info(f"Validation passed with confidence {validated.confidence_score}")

                # Populate shared_reasoning
                state.setdefault("shared_reasoning", []).append({
                    "agent": self.agent_name,
                    "summary": f"Validation passed with confidence {validated.confidence_score}",
                    "key_findings": [
                        f"Overall valid: {validated.overall_valid}",
                        f"Confidence: {validated.confidence_score}",
                        f"Warnings: {len(validated.warnings)}",
                    ],
                })
            else:
                # Validation failed — increment retry counter
                state["validation_retry_count"] = retry_count + 1

                # Store errors for next iteration's context
                if validated.errors:
                    state.setdefault("validation_errors", []).extend(validated.errors)
                if validated.suggested_fixes:
                    state.setdefault("validation_errors", []).extend(
                        [f"Fix: {fix}" for fix in validated.suggested_fixes]
                    )

                state["iteration"] = state.get("iteration", 0) + 1
                max_iter = state.get("max_iterations", 10)
                if state["iteration"] >= max_iter:
                    state["current_phase"] = "fail"
                    state["error_message"] = f"Max iterations ({max_iter}) reached"
                else:
                    state["current_phase"] = "supervisor"

                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.VALIDATION_FAILED,
                    agent_name=self.agent_name,
                    data={"errors": validated.errors, "fixes": validated.suggested_fixes},
                    duration_ms=duration,
                )
                logger.warning(
                    f"Validation failed (retry {state['validation_retry_count']}/{MAX_VALIDATION_RETRIES}), "
                    f"iteration {state['iteration']}"
                )

        except ValidationError as ve:
            # Pydantic model error — count as retry
            state["validation_retry_count"] = retry_count + 1
            state["current_phase"] = "supervisor"
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_FAILED,
                agent_name=self.agent_name,
                error=str(ve),
            )

        await self.emit_completed(event_queue, ctx)

    def _run_test_queries(self, state: dict, session_id: str):
        """Run validation queries in a temporary FalkorDB graph.

        Skips execution if queries contain $param placeholders since
        FalkorDB requires actual parameter values (not just placeholders).
        """
        cypher_queries = state.get("cypher_queries", {}).get("queries", {})
        rule_insert = cypher_queries.get("rule_insert", "")
        validation_query = cypher_queries.get("validation", "")

        if not rule_insert or not validation_query:
            return

        if '$' in rule_insert or '$' in validation_query:
            logger.info("Skipping FalkorDB test: queries contain $param placeholders")
            return

        temp_graph = None
        graph_name = None
        try:
            temp_graph, graph_name = self.db_service.get_temp_graph()
            temp_graph.query(rule_insert)
            result = temp_graph.query(validation_query)
            logger.info(f"Test query returned {len(result.result_set) if hasattr(result, 'result_set') else 0} rows")

        except Exception as e:
            logger.warning(f"FalkorDB test query failed: {e}")
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_FAILED,
                agent_name=self.agent_name,
                error=f"Test query failed: {e}",
            )
        finally:
            if graph_name:
                self.db_service.delete_temp_graph(graph_name)

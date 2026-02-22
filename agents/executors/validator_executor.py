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
from agents.executors.utils import parse_json_response, sanitize_query_params
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

# ── False-positive filter ───────────────────────────────────────────────────
# The validator LLM often "invents" errors by cross-referencing the graph
# schema shown in its system prompt against the rule_definition.  It flags
# valid OPTIONAL fields (e.g. "requires_personal_data", "authorities") as
# missing or incorrect — these are not real schema violations.
#
# Strategy: an error is a TRUE BLOCKING error only if it references a
# REQUIRED field or a Cypher/syntax issue.  Errors that merely name a
# known optional field are demoted to warnings so they don't block.
_REQUIRED_FIELDS = frozenset({
    "rule_id", "name", "rule_type", "outcome", "odrl_type",
})
_CYPHER_KEYWORDS = frozenset({
    "cypher", "syntax", "blocklist", "exists subquery", "union", "foreach",
    "delete", "semicolon", "parameter", "param", "query", "merge", "match",
    "missing cypher", "missing rule", "node type", "relationship type",
    "schema compliance",
})
# Known-valid optional fields — errors mentioning only these are false positives
_OPTIONAL_FIELDS = frozenset({
    "requires_personal_data", "requires_any_data", "requires_pii",
    "data_categories", "data_categorisation", "purposes_of_processing",
    "processes", "gdc", "regulators", "authorities", "data_subjects",
    "sensitive_data_categories", "global_business_functions",
    "suggested_linked_entities", "case_matching_module",
    "attribute_name", "attribute_keywords", "attribute_patterns",
    "valid_until", "description", "priority", "required_actions",
    "odrl_action", "odrl_target", "origin_countries", "receiving_countries",
    "origin_group", "receiving_group",
})


def _split_errors(errors: list) -> tuple[list, list]:
    """Separate truly blocking errors from false positives.

    Returns (blocking_errors, demoted_warnings).
    An error is blocking only if it references a required field or a Cypher
    syntax problem.  Errors that only reference known optional fields are
    demoted to warnings so validation does not block on them.
    """
    blocking: list = []
    demoted: list = []
    for err in errors:
        err_str = str(err).lower()

        # Always keep errors about required fields or Cypher issues
        is_required_violation = any(f in err_str for f in _REQUIRED_FIELDS)
        is_cypher_issue       = any(kw in err_str for kw in _CYPHER_KEYWORDS)

        if is_required_violation or is_cypher_issue:
            blocking.append(err)
            continue

        # Demote if the only named field is an optional one
        references_optional = any(f in err_str for f in _OPTIONAL_FIELDS)
        if references_optional:
            demoted.append(f"[auto-demoted to warning] {err}")
        else:
            blocking.append(err)

    return blocking, demoted


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
        self.record_invocation(state)

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

            # ── False-positive filtering ──────────────────────────────────
            # The validator LLM sometimes flags valid optional fields
            # (e.g. "requires_personal_data / data_categorisation") as errors
            # because it cross-references the graph schema in its prompt.
            # Demote those to warnings so they don't block the workflow.
            blocking_errors, demoted = _split_errors(validated.errors)
            if demoted:
                logger.info(
                    f"Validator: demoted {len(demoted)} false-positive error(s) "
                    f"to warnings: {demoted[:2]}"
                )
                # Rebuild the model with corrected error/warning lists.
                # After filtering: overall_valid is True iff no BLOCKING errors remain.
                # (The LLM may have set overall_valid=False solely because of the
                # false-positive errors we just demoted — recalculate from the
                # cleaned error list.)
                all_warnings = list(validated.warnings) + demoted
                validated = ValidationResultModel(
                    overall_valid=len(blocking_errors) == 0,
                    confidence_score=validated.confidence_score,
                    rule_definition_valid=validated.rule_definition_valid,
                    cypher_valid=validated.cypher_valid,
                    logical_valid=validated.logical_valid,
                    errors=blocking_errors,
                    warnings=all_warnings,
                    suggested_fixes=validated.suggested_fixes,
                )
            # ─────────────────────────────────────────────────────────────

            state["validation_result"] = validated.model_dump()
            duration = (time.time() - start_time) * 1000

            # FalkorDB test queries in temp graph
            if self.db_service and validated.overall_valid:
                self._run_test_queries(state, session_id)

            # Accept if: overall_valid=True, or no BLOCKING errors (only warnings), or confidence >= 0.5
            has_blocking_errors = len(blocking_errors) > 0
            is_acceptable = (validated.overall_valid or not has_blocking_errors) and validated.confidence_score >= 0.4

            if is_acceptable:
                # Validation passed — reset retry counter, route to rule_tester
                self.record_success(state)
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
                self.record_failure(state, f"Validation failed: {validated.errors[:3]}")
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
            self.record_failure(state, f"Pydantic error: {ve}")
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

        Binds $param placeholders using query_params from the cypher_queries
        state. Only skips if queries have $params AND no params dict is available.
        """
        cypher_data = state.get("cypher_queries", {})
        cypher_queries = cypher_data.get("queries", {})
        raw_params = cypher_data.get("params", {}) or {}
        # Sanitize param keys: strip $ prefix and embedded quotes from LLM output
        params = sanitize_query_params(raw_params)

        rule_insert = cypher_queries.get("rule_insert", "")
        validation_query = cypher_queries.get("validation", "")

        if not rule_insert or not validation_query:
            return

        # Only skip if queries have $params AND no params dict is available
        has_params_insert = '$' in rule_insert
        has_params_validation = '$' in validation_query
        if (has_params_insert or has_params_validation) and not params:
            logger.warning(
                "Skipping FalkorDB test: queries contain $param placeholders "
                "but no query_params were provided by the cypher generator"
            )
            state.setdefault("events", []).append({
                "event_type": "validation_detail",
                "agent_name": self.agent_name,
                "message": "Test queries skipped: $param placeholders present but no params dict provided",
            })
            return

        temp_graph = None
        graph_name = None
        try:
            temp_graph, graph_name = self.db_service.get_temp_graph()

            # Execute with bound params if needed, otherwise plain execution
            if has_params_insert:
                temp_graph.query(rule_insert, params)
            else:
                temp_graph.query(rule_insert)

            if has_params_validation:
                result = temp_graph.query(validation_query, params)
            else:
                result = temp_graph.query(validation_query)

            row_count = len(result.result_set) if hasattr(result, 'result_set') else 0
            logger.info(f"Test query returned {row_count} rows (params bound: {bool(params)})")

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

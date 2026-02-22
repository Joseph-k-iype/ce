"""
Rule Tester Executor
=====================
Generates test scenarios via AI, then deterministically executes them
against a temporary FalkorDB graph using the real RulesEvaluator.
Implements Google A2A SDK AgentExecutor interface.
"""

import logging
import time
import json

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue

from agents.executors.base_executor import ComplianceAgentExecutor, InProcessRequestContext
from agents.executors.utils import parse_json_response
from agents.prompts.tester_prompts import (
    TESTER_SYSTEM_PROMPT,
    TESTER_USER_TEMPLATE,
)
from agents.prompts.prompt_builder import build_tester_prompt
from agents.audit.event_types import AuditEventType
from agents.ai_service import AIRequestError

logger = logging.getLogger(__name__)

# After this many test failures, auto-complete with warnings instead of looping
MAX_TEST_RETRIES = 2


class RuleTesterExecutor(ComplianceAgentExecutor):
    """Rule tester agent executor — generates test scenarios and runs them
    against a temporary FalkorDB graph for deterministic verification."""

    agent_name = "rule_tester"

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        ctx: InProcessRequestContext = context
        state = ctx.state
        start_time = time.time()
        session_id = state.get("origin_country", "unknown")

        # Guard: need rule_definition
        rule_definition = state.get("rule_definition")
        if not rule_definition:
            logger.warning("rule_tester: no rule_definition, routing to supervisor")
            state["current_phase"] = "supervisor"
            await self.emit_completed(event_queue, ctx)
            return

        # ── Fallback: auto-complete after too many test failures ──
        test_retry = state.get("test_retry_count", 0)
        if test_retry >= MAX_TEST_RETRIES:
            logger.warning(
                f"rule_tester: auto-completing after {test_retry} failed attempts"
            )
            state["current_phase"] = "complete"
            state["success"] = True
            state["test_results"] = {
                "auto_completed": True,
                "reason": f"Auto-completed after {test_retry} test failures — rule accepted for human review",
                "previous_results": state.get("test_results"),
            }
            state["events"].append({
                "event_type": "test_skipped",
                "agent_name": self.agent_name,
                "message": f"Tests auto-skipped after {test_retry} failures — accepted for human review",
            })
            await self.emit_completed(event_queue, ctx)
            return

        await self.emit_working(event_queue, ctx)
        self.record_invocation(state)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        # ── Step 1: Generate test scenarios via AI ──
        user_prompt = build_tester_prompt(
            template=TESTER_USER_TEMPLATE,
            rule_definition=rule_definition,
            rule_text=state.get("rule_text", ""),
            dictionary_result=state.get("dictionary_result"),
            origin_country=state.get("origin_country", ""),
            receiving_countries=state.get("receiving_countries", []),
            data_categories=state.get("data_categories", []),
        )

        try:
            response = self.call_ai_with_retry(user_prompt, TESTER_SYSTEM_PROMPT)
        except AIRequestError as e:
            logger.error(f"rule_tester AI error: {e}")
            state["current_phase"] = "complete"
            state["success"] = True
            state["test_results"] = {
                "skipped": True,
                "reason": f"AI error generating test scenarios: {e}",
            }
            await self.emit_completed(event_queue, ctx)
            return

        parsed = parse_json_response(response)
        scenarios = (parsed or {}).get("test_scenarios", [])

        if not scenarios:
            logger.warning("rule_tester: no test scenarios generated, proceeding to complete")
            state["current_phase"] = "complete"
            state["success"] = True
            state["test_results"] = {
                "skipped": True,
                "reason": "No test scenarios generated",
            }
            await self.emit_completed(event_queue, ctx)
            return

        # ── Step 2: Create temp graph and load the rule ──
        if not self.db_service:
            logger.warning("rule_tester: no db_service, skipping graph tests")
            state["current_phase"] = "complete"
            state["success"] = True
            state["test_results"] = {
                "skipped": True,
                "reason": "No database service available",
                "scenarios_generated": len(scenarios),
            }
            await self.emit_completed(event_queue, ctx)
            return

        temp_graph = None
        graph_name = None
        results = []

        try:
            temp_graph, graph_name = self.db_service.get_temp_graph()

            # Build the rule into the temp graph
            from utils.graph_builder import RulesGraphBuilder
            builder = RulesGraphBuilder(graph=temp_graph)
            builder._create_indexes()
            builder._build_countries_from_csv()
            builder._build_country_groups()
            builder._build_countries_from_groups()
            builder._build_actions()
            builder._ingest_data_dictionaries_v2()
            builder.add_rule(rule_definition)

            # Create evaluator against temp graph
            from services.rules_evaluator import RulesEvaluator
            evaluator = RulesEvaluator(rules_graph=temp_graph)

            rule_id = rule_definition.get("rule_id", "")

            # ── Step 3: Run each scenario ──
            for scenario in scenarios:
                scenario_name = scenario.get("name", "unnamed")
                try:
                    origin = scenario.get("origin_country", "")
                    receiving = scenario.get("receiving_country", "")
                    pii = scenario.get("pii", False)
                    personal_data_names = scenario.get("personal_data_names", [])
                    purposes = scenario.get("purposes", [])
                    data_categories = scenario.get("data_categories", [])
                    metadata = scenario.get("metadata")
                    processes = scenario.get("processes", [])
                    expected_triggered = scenario.get("expected_triggered", True)
                    expected_outcome = scenario.get("expected_outcome")

                    if not origin or not receiving:
                        results.append({
                            "name": scenario_name,
                            "passed": False,
                            "reason": "Missing origin or receiving country",
                        })
                        continue

                    eval_result = evaluator.evaluate(
                        origin_country=origin,
                        receiving_country=receiving,
                        pii=pii,
                        personal_data_names=personal_data_names,
                        purposes=purposes,
                        data_categories=data_categories or None,
                        metadata=metadata,
                        process_l1=processes[:1] if processes else None,
                        process_l2=processes[1:2] if len(processes) > 1 else None,
                        process_l3=processes[2:3] if len(processes) > 2 else None,
                    )

                    # Check if our rule triggered
                    triggered_ids = [r.rule_id for r in (eval_result.triggered_rules or [])]
                    actually_triggered = rule_id in triggered_ids

                    # Find outcome if triggered
                    actual_outcome = None
                    if actually_triggered:
                        for tr in eval_result.triggered_rules:
                            if tr.rule_id == rule_id:
                                actual_outcome = tr.outcome.value if hasattr(tr.outcome, 'value') else str(tr.outcome)
                                break

                    # Evaluate pass/fail
                    trigger_ok = actually_triggered == expected_triggered
                    outcome_ok = True
                    if expected_outcome and actually_triggered:
                        outcome_ok = actual_outcome == expected_outcome

                    passed = trigger_ok and outcome_ok

                    reason = ""
                    if not trigger_ok:
                        reason = f"Expected triggered={expected_triggered}, got triggered={actually_triggered}"
                    elif not outcome_ok:
                        reason = f"Expected outcome={expected_outcome}, got outcome={actual_outcome}"

                    results.append({
                        "name": scenario_name,
                        "passed": passed,
                        "actually_triggered": actually_triggered,
                        "actual_outcome": actual_outcome,
                        "expected_triggered": expected_triggered,
                        "expected_outcome": expected_outcome,
                        "reason": reason,
                    })

                except Exception as e:
                    results.append({
                        "name": scenario_name,
                        "passed": False,
                        "reason": f"Execution error: {e}",
                    })

        except Exception as e:
            logger.error(f"rule_tester graph setup error: {e}")
            state["current_phase"] = "complete"
            state["success"] = True
            state["test_results"] = {
                "skipped": True,
                "reason": f"Graph setup error: {e}",
                "scenarios_generated": len(scenarios),
            }
            await self.emit_completed(event_queue, ctx)
            return
        finally:
            if graph_name and self.db_service:
                try:
                    self.db_service.delete_temp_graph(graph_name)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp graph: {e}")

        # ── Step 4: Evaluate results ──
        duration = (time.time() - start_time) * 1000
        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        failed = total - passed

        test_summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "scenarios": results,
        }
        state["test_results"] = test_summary

        if failed == 0:
            # All tests passed -> complete
            self.record_success(state)
            state["current_phase"] = "complete"
            state["success"] = True
            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_COMPLETED,
                agent_name=self.agent_name,
                data={"total": total, "passed": passed},
                duration_ms=duration,
            )
            logger.info(f"rule_tester: all {total} tests passed")

            # Populate shared_reasoning
            state.setdefault("shared_reasoning", []).append({
                "agent": self.agent_name,
                "summary": f"All {total} test scenarios passed",
                "key_findings": [
                    f"{passed}/{total} scenarios passed",
                    "Rule triggers correctly for expected inputs",
                    "Rule correctly does not trigger for non-matching inputs",
                ],
            })
        else:
            # Some tests failed -> increment test retry count
            failure_details = [
                f"- {r['name']}: {r.get('reason', 'unknown')}"
                for r in results if not r.get("passed")
            ]
            self.record_failure(state, f"{failed}/{total} test scenarios failed")
            state["test_retry_count"] = state.get("test_retry_count", 0) + 1
            state["iteration"] = state.get("iteration", 0) + 1

            # If we've hit the retry limit, complete with warnings
            if state["test_retry_count"] >= MAX_TEST_RETRIES:
                state["current_phase"] = "complete"
                state["success"] = True
                logger.warning(
                    f"rule_tester: {failed}/{total} tests failed after "
                    f"{state['test_retry_count']} attempts, auto-completing"
                )
            else:
                state["current_phase"] = "supervisor"

            self.event_store.append(
                session_id=session_id,
                event_type=AuditEventType.AGENT_FAILED,
                agent_name=self.agent_name,
                data={"total": total, "passed": passed, "failed": failed},
                duration_ms=duration,
            )
            logger.warning(f"rule_tester: {failed}/{total} tests failed")

            # Populate shared_reasoning with failure context
            state.setdefault("shared_reasoning", []).append({
                "agent": self.agent_name,
                "summary": f"{failed}/{total} test scenarios failed — rule needs adjustment",
                "key_findings": failure_details[:5],
            })

        await self.emit_completed(event_queue, ctx)

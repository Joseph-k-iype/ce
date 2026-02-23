"""
Data Dictionary Executor
=========================
Generates keyword dictionaries for ALL entity types identified by the rule analyzer.
Covers: data categories, processes, GDC, regulators, authorities, data subjects,
sensitive data categories, purposes of processing, global business functions.

IMPORTANT: This agent ALWAYS runs after rule_analyzer (sequential pipeline).
It is never skipped by design — no skip guards. The dictionary agent can infer
entity types from the rule_definition and rule_text even when explicit
data_categories are not provided.

After successful generation, all keywords are merged into rule_definition
so they are available for graph ingestion when the rule is approved.
Implements Google A2A SDK AgentExecutor interface.
"""

import json
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


def _collect_all_keywords(parsed: dict) -> tuple[list, list]:
    """Collect all keywords and patterns from the full dictionary result.

    Returns (all_keywords, all_patterns) covering every entity-type dictionary
    the LLM generated (data categories, processes, GDC, regulators, etc.).
    """
    all_keywords: list = []
    all_patterns: list = list(parsed.get("internal_patterns") or [])

    dicts = parsed.get("dictionaries") or {}
    for cat_data in dicts.values():
        if not isinstance(cat_data, dict):
            continue
        all_keywords.extend(cat_data.get("keywords") or [])
        # Sub-category keywords
        for sub_data in (cat_data.get("sub_categories") or {}).values():
            if isinstance(sub_data, list):
                all_keywords.extend(sub_data)
            elif isinstance(sub_data, dict):
                all_keywords.extend(sub_data.get("keywords") or [])

    # PII dictionary
    pii_dict = parsed.get("pii_dictionary") or {}
    if isinstance(pii_dict, dict):
        all_keywords.extend(pii_dict.get("keywords") or [])

    # Deduplicate while preserving order, filter out very short terms
    seen: set = set()
    unique_kws: list = []
    for kw in all_keywords:
        kw_clean = str(kw).strip().lower()
        if kw_clean and len(kw_clean) >= 3 and kw_clean not in seen:
            seen.add(kw_clean)
            unique_kws.append(kw_clean)

    return unique_kws, all_patterns


class DataDictionaryExecutor(ComplianceAgentExecutor):
    """Data dictionary agent executor - generates keyword dictionaries for all entity types.

    Runs sequentially AFTER rule_analyzer so it always has the full rule_definition
    context including all entity suggestions (regulators, authorities, GDC, etc.).
    Never skipped — always attempts to generate dictionaries.
    """

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

        # Resolve data categories: state first, then rule_definition fallback.
        # If still empty, proceed anyway — the LLM infers categories from rule_text
        # and rule_definition. No skip guard: dictionary always runs.
        data_categories = state.get("data_categories") or []
        rule_def = state.get("rule_definition") or {}
        if not data_categories:
            data_categories = rule_def.get("data_categories") or []

        await self.emit_working(event_queue, ctx)
        self.record_invocation(state)

        self.event_store.append(
            session_id=session_id,
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name=self.agent_name,
        )

        # Pass the full rule_definition as the "feedback" (analyzer analysis) context.
        # This gives the dictionary agent:
        # - All data categories extracted by the analyzer
        # - All entity mappings (regulators, authorities, GDC, processes, data_subjects, etc.)
        # - Rule type, outcome, and ODRL context for domain-aware keyword generation
        rule_def_str = json.dumps(rule_def, indent=2) if rule_def else "None"

        user_prompt = build_dictionary_prompt(
            template=DICTIONARY_USER_TEMPLATE,
            data_categories=data_categories,
            rule_text=state.get("rule_text", ""),
            origin_country=state.get("origin_country", ""),
            scenario_type=state.get("scenario_type", "transfer"),
            feedback=rule_def_str,
            is_pii_related=state.get("is_pii_related", False),
        )

        try:
            response = self.call_ai_with_retry(user_prompt, DICTIONARY_SYSTEM_PROMPT)
            parsed = parse_json_response(response)

            if parsed:
                state["dictionary_result"] = parsed

                # ── Merge ALL keywords into rule_definition for graph ingestion ──
                # Collect keywords from every entity-type dictionary generated
                # (data categories, processes, GDC, regulators, authorities, etc.)
                all_keywords, all_patterns = _collect_all_keywords(parsed)

                if all_keywords:
                    existing_kws = rule_def.get("attribute_keywords") or []
                    merged_kws = list(dict.fromkeys(existing_kws + all_keywords))
                    rule_def["attribute_keywords"] = merged_kws
                    logger.info(
                        f"Dictionary: merged {len(all_keywords)} keywords "
                        f"({len(merged_kws)} total after dedup) into rule_definition"
                    )

                if all_patterns:
                    existing_patterns = rule_def.get("attribute_patterns") or []
                    rule_def["attribute_patterns"] = list(
                        dict.fromkeys(existing_patterns + all_patterns)
                    )

                # Write the enriched rule_definition back to state
                state["rule_definition"] = rule_def
                # ─────────────────────────────────────────────────────────────

                self.record_success(state)
                state["current_phase"] = "cypher_generator"

                duration = (time.time() - start_time) * 1000
                categories = list(parsed.get("dictionaries", {}).keys())
                total_keywords = sum(
                    len(v.get("keywords", []))
                    for v in parsed.get("dictionaries", {}).values()
                    if isinstance(v, dict)
                )
                self.event_store.append(
                    session_id=session_id,
                    event_type=AuditEventType.DICTIONARY_GENERATED,
                    agent_name=self.agent_name,
                    data={
                        "categories": categories,
                        "total_keywords": total_keywords,
                        "attribute_keywords_merged": len(all_keywords),
                    },
                    duration_ms=duration,
                )
                logger.info(
                    f"Dictionary generated: {len(categories)} entity categories, "
                    f"~{total_keywords} raw keywords, {len(all_keywords)} merged into rule_definition"
                )

                # Populate shared_reasoning
                state.setdefault("shared_reasoning", []).append({
                    "agent": self.agent_name,
                    "summary": (
                        f"Generated dictionaries for {len(categories)} entity types "
                        f"with ~{total_keywords} keywords"
                    ),
                    "key_findings": [
                        f"Entity categories covered: {', '.join(categories[:8])}",
                        f"Total keyword entries: ~{total_keywords}",
                        f"Keywords merged into rule_definition: {len(all_keywords)}",
                    ],
                })
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
            logger.error(f"Data dictionary error: {e}")
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

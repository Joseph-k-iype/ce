"""
Evaluation Router
==================
Endpoints for rule evaluation and case search.
Supports legal entity parameters, multi-select, case-insensitive matching.
All matching rules fire — no short-circuit. Results are aggregated.
"""

import logging
import time
from fastapi import APIRouter, HTTPException, Depends

from models.schemas import (
    RulesEvaluationRequest,
    RulesEvaluationResponse,
    SearchCasesRequest,
    SearchCasesResponse,
    CaseMatch,
    TransferStatus,
    AssessmentCompliance,
)
from services.database import get_db_service
from services.rules_evaluator import get_rules_evaluator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["External - Policy Evaluation"])


def get_db():
    return get_db_service()


def get_evaluator():
    return get_rules_evaluator()


@router.post("/evaluate-rules", response_model=RulesEvaluationResponse)
async def evaluate_rules(
    request: RulesEvaluationRequest,
    evaluator=Depends(get_evaluator),
):
    """Evaluate compliance rules for a data transfer.
    Supports multi-select receiving countries - evaluates each and merges results.
    ALL matching rules fire — no short-circuit.
    If ANY rule is a prohibition, overall result is PROHIBITION.
    """
    try:
        receiving_countries = request.get_receiving_countries()

        # Resolve fields using new getter methods (backward compatible)
        purposes = request.get_purposes()
        processes = request.get_processes()
        data_categories = request.get_data_categories()
        personal_data_names = request.get_personal_data_names()

        if len(receiving_countries) <= 1:
            receiving = receiving_countries[0] if receiving_countries else ""
            result = evaluator.evaluate(
                origin_country=request.origin_country,
                receiving_country=receiving,
                pii=request.pii,
                purposes=purposes or request.purposes,
                process_l1=request.process_l1,
                process_l2=request.process_l2,
                process_l3=request.process_l3,
                personal_data_names=personal_data_names or request.personal_data_names,
                data_categories=data_categories,
                metadata=request.metadata,
                origin_legal_entity=request.origin_legal_entity,
                receiving_legal_entity=request.receiving_legal_entity[0] if request.receiving_legal_entity else None,
                data_subjects=request.get_data_subjects(),
                regulators=request.get_regulators(),
                authorities=request.get_authorities(),
            )
            return result

        # Multi-select: evaluate each receiving country
        all_results = []
        for rc in receiving_countries:
            r = evaluator.evaluate(
                origin_country=request.origin_country,
                receiving_country=rc,
                pii=request.pii,
                purposes=purposes or request.purposes,
                process_l1=request.process_l1,
                process_l2=request.process_l2,
                process_l3=request.process_l3,
                personal_data_names=personal_data_names or request.personal_data_names,
                data_categories=data_categories,
                metadata=request.metadata,
                origin_legal_entity=request.origin_legal_entity,
                data_subjects=request.get_data_subjects(),
                regulators=request.get_regulators(),
                authorities=request.get_authorities(),
            )
            all_results.append(r)

        # Merge: aggregate ALL triggered rules across countries
        # Deduplicate by rule_id, union all duties/assessments
        seen_rule_ids = set()
        merged_triggered = []
        merged_duties = set()
        merged_prohibition_reasons = []
        merged_detected_attrs = []
        merged_required_actions = set()
        has_prohibition = False

        # Merge evaluation graphs
        merged_nodes = {} # id -> node
        merged_edges = {} # id -> edge

        # Merge assessment compliance across all results
        merged_assessment = AssessmentCompliance()

        for r in all_results:
            # Deduplicate triggered rules by rule_id
            for rule in r.triggered_rules:
                if rule.rule_id not in seen_rule_ids:
                    seen_rule_ids.add(rule.rule_id)
                    merged_triggered.append(rule)

            merged_duties.update(r.consolidated_duties)
            merged_prohibition_reasons.extend(r.prohibition_reasons)
            merged_required_actions.update(r.required_actions)

            if r.detected_attributes:
                for attr in r.detected_attributes:
                    if not any(a.attribute_name == attr.attribute_name for a in merged_detected_attrs):
                        merged_detected_attrs.append(attr)

            if r.transfer_status == TransferStatus.PROHIBITED:
                has_prohibition = True

            # Merge graphs
            if r.evaluation_graph:
                for node in r.evaluation_graph.nodes:
                    merged_nodes[node.id] = node
                for edge in r.evaluation_graph.edges:
                    merged_edges[edge.id] = edge

            # Merge assessment compliance
            if r.assessment_compliance:
                if r.assessment_compliance.pia_required:
                    merged_assessment.pia_required = True
                if r.assessment_compliance.tia_required:
                    merged_assessment.tia_required = True
                if r.assessment_compliance.hrpr_required:
                    merged_assessment.hrpr_required = True
                if r.assessment_compliance.pia_compliant:
                    merged_assessment.pia_compliant = True
                if r.assessment_compliance.tia_compliant:
                    merged_assessment.tia_compliant = True
                if r.assessment_compliance.hrpr_compliant:
                    merged_assessment.hrpr_compliant = True

        from models.schemas import EvaluationGraph
        final_graph = EvaluationGraph(
            nodes=list(merged_nodes.values()),
            edges=list(merged_edges.values())
        )

        # Update all_compliant
        merged_assessment.all_compliant = (
            (not merged_assessment.pia_required or merged_assessment.pia_compliant) and
            (not merged_assessment.tia_required or merged_assessment.tia_compliant) and
            (not merged_assessment.hrpr_required or merged_assessment.hrpr_compliant)
        )
        missing = []
        if merged_assessment.pia_required and not merged_assessment.pia_compliant:
            missing.append("PIA")
        if merged_assessment.tia_required and not merged_assessment.tia_compliant:
            missing.append("TIA")
        if merged_assessment.hrpr_required and not merged_assessment.hrpr_compliant:
            missing.append("HRPR")
        merged_assessment.missing_assessments = missing

        final_status = TransferStatus.PROHIBITED if has_prohibition else (
            all_results[0].transfer_status if all_results else TransferStatus.REQUIRES_REVIEW
        )

        # Use the best precedent validation and evidence summary
        best_precedent = None
        best_evidence = None
        for r in all_results:
            if r.precedent_validation and (
                best_precedent is None or r.precedent_validation.compliant_matches > best_precedent.compliant_matches
            ):
                best_precedent = r.precedent_validation
            if r.evidence_summary and (
                best_evidence is None or (r.evidence_summary.strongest_match_score > best_evidence.strongest_match_score)
            ):
                best_evidence = r.evidence_summary

        return RulesEvaluationResponse(
            transfer_status=final_status,
            origin_country=request.origin_country,
            receiving_country=", ".join(receiving_countries),
            pii=request.pii,
            triggered_rules=merged_triggered,
            evaluation_graph=final_graph,
            precedent_validation=best_precedent,
            assessment_compliance=merged_assessment,
            detected_attributes=merged_detected_attrs,
            consolidated_duties=sorted(merged_duties),
            required_actions=sorted(merged_required_actions),
            prohibition_reasons=merged_prohibition_reasons,
            evidence_summary=best_evidence,
            message=f"Evaluated {len(receiving_countries)} receiving countries. Status: {final_status.value}",
            evaluation_time_ms=sum(r.evaluation_time_ms for r in all_results),
        )

    except Exception as e:
        logger.error(f"Error evaluating rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-rules-mock")
async def evaluate_rules_mock(
    evaluator=Depends(get_evaluator),
):
    """Mock test endpoint with sample data for attribute-level rule validation."""
    try:
        result = evaluator.evaluate(
            origin_country="United Kingdom",
            receiving_country="United States",
            pii=True,
            purposes=["Risk Management"],
            personal_data_names=["Medical Records", "Credit Card Number"],
            metadata={"test": True},
        )
        return result
    except Exception as e:
        logger.error(f"Mock evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-cases", response_model=SearchCasesResponse)
async def search_cases(
    request: SearchCasesRequest,
    db=Depends(get_db),
):
    """Search for historical precedent cases."""
    start_time = time.time()

    try:
        match_parts = ["MATCH (c:Case)"]
        where_conditions = ["c.case_status IN ['Completed', 'Complete', 'Active', 'Published']"]
        params = {}

        if request.origin_country:
            match_parts.append(
                "MATCH (c)-[:ORIGINATES_FROM]->(origin:Country {name: $origin_country})"
            )
            params["origin_country"] = request.origin_country
        if request.receiving_country:
            match_parts.append(
                "MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction {name: $receiving_country})"
            )
            params["receiving_country"] = request.receiving_country
        if request.purposes:
            match_parts.append(
                "MATCH (c)-[:HAS_PURPOSE]->(p:Purpose)"
            )
            where_conditions.append("p.name IN $purposes")
            params["purposes"] = request.purposes
        if request.pii is not None:
            where_conditions.append("c.pii = $pii")
            params["pii"] = request.pii

        base_query = "\n".join(match_parts)
        if where_conditions:
            base_query += "\nWHERE " + " AND ".join(where_conditions)

        count_query = base_query + "\nRETURN count(c) as total"
        count_result = db.execute_data_query(count_query, params=params or None)
        total_count = count_result[0].get('total', 0) if count_result else 0

        params["skip_offset"] = request.offset
        params["page_limit"] = request.limit
        data_query = base_query + "\nRETURN c SKIP $skip_offset LIMIT $page_limit"
        data_result = db.execute_data_query(data_query, params=params)

        cases = []
        for row in data_result:
            case_data = row.get('c', {})
            if case_data:
                cases.append(CaseMatch(
                    case_id=str(case_data.get('case_id', '')),
                    case_ref_id=str(case_data.get('case_ref_id', '')),
                    case_status=str(case_data.get('case_status', '')),
                    origin_country=request.origin_country or "",
                    receiving_country=request.receiving_country or "",
                    pia_status=case_data.get('pia_status'),
                    tia_status=case_data.get('tia_status'),
                    hrpr_status=case_data.get('hrpr_status'),
                    is_compliant=(
                        case_data.get('pia_status') == 'Completed' and
                        (case_data.get('tia_status') == 'Completed' or not case_data.get('tia_status')) and
                        (case_data.get('hrpr_status') == 'Completed' or not case_data.get('hrpr_status'))
                    ),
                ))

        return SearchCasesResponse(
            total_count=total_count,
            returned_count=len(cases),
            cases=cases,
            query_time_ms=(time.time() - start_time) * 1000
        )

    except Exception as e:
        logger.error(f"Error searching cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

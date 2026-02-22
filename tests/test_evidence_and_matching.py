"""
Tests for Enhanced Evidence and Precedent Matching
===================================================
Tests for the field-level matching, match scoring, evidence summaries,
and the enriched CaseMatch model.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import (
    CaseMatch,
    FieldMatch,
    EvidenceSummary,
    PrecedentValidation,
    RulesEvaluationResponse,
    TransferStatus,
    AgentActionEntry,
    AgentSessionSummary,
    ReferenceDataResult,
    AIRuleGenerationResponse,
)


class TestFieldMatch:
    """Tests for the FieldMatch model"""

    def test_exact_match(self):
        """Test exact field match"""
        fm = FieldMatch(
            field_name="origin_country",
            query_values=["United Kingdom"],
            case_values=["United Kingdom"],
            match_type="exact",
            match_percentage=100.0,
        )
        assert fm.match_type == "exact"
        assert fm.match_percentage == 100.0

    def test_partial_match(self):
        """Test partial field match"""
        fm = FieldMatch(
            field_name="purposes",
            query_values=["Marketing", "Analytics", "Research"],
            case_values=["Marketing", "Compliance"],
            match_type="partial",
            match_percentage=33.3,
        )
        assert fm.match_type == "partial"
        assert fm.match_percentage == 33.3

    def test_no_match(self):
        """Test no match"""
        fm = FieldMatch(
            field_name="process_l1",
            query_values=["Customer Management"],
            case_values=["HR Management"],
            match_type="none",
            match_percentage=0.0,
        )
        assert fm.match_type == "none"
        assert fm.match_percentage == 0.0


class TestCaseMatchEnhancements:
    """Tests for the enhanced CaseMatch model"""

    def test_case_match_with_field_matches(self):
        """Test CaseMatch with field-level match data"""
        case = CaseMatch(
            case_id="123",
            case_ref_id="REF-001",
            case_status="Completed",
            origin_country="United Kingdom",
            receiving_country="India",
            pia_status="Completed",
            tia_status="Completed",
            is_compliant=True,
            purposes=["Marketing"],
            match_score=0.85,
            field_matches=[
                FieldMatch(
                    field_name="origin_country",
                    query_values=["United Kingdom"],
                    case_values=["United Kingdom"],
                    match_type="exact",
                    match_percentage=100.0,
                ),
                FieldMatch(
                    field_name="purposes",
                    query_values=["Marketing", "Analytics"],
                    case_values=["Marketing"],
                    match_type="partial",
                    match_percentage=50.0,
                ),
            ],
            relevance_explanation="Case REF-001 is a precedent with completed PIA and TIA assessments.",
        )
        assert len(case.field_matches) == 2
        assert case.relevance_explanation is not None
        assert case.match_score == 0.85

    def test_case_match_serialization(self):
        """Test that enhanced CaseMatch serializes correctly"""
        case = CaseMatch(
            case_id="456",
            case_ref_id="REF-002",
            case_status="Active",
            origin_country="Germany",
            receiving_country="United States",
            is_compliant=True,
            match_score=0.95,
            field_matches=[
                FieldMatch(
                    field_name="receiving_country",
                    query_values=["United States"],
                    case_values=["United States"],
                    match_type="exact",
                    match_percentage=100.0,
                ),
            ],
            relevance_explanation="Strong match.",
        )
        data = case.model_dump()
        assert "field_matches" in data
        assert "relevance_explanation" in data
        assert len(data["field_matches"]) == 1


class TestEvidenceSummary:
    """Tests for the EvidenceSummary model"""

    def test_evidence_summary_creation(self):
        """Test creating an evidence summary"""
        summary = EvidenceSummary(
            total_cases_searched=100,
            compliant_cases_found=5,
            strongest_match_score=0.92,
            strongest_match_case_id="REF-001",
            common_purposes=["Marketing", "Analytics"],
            common_data_categories=["Personal Data"],
            assessment_coverage={"PIA": "5/5 cases completed", "TIA": "3/5 cases completed"},
            confidence_level="high",
            evidence_narrative="Found 5 compliant precedent cases.",
        )
        assert summary.confidence_level == "high"
        assert summary.strongest_match_score == 0.92
        assert len(summary.common_purposes) == 2

    def test_empty_evidence_summary(self):
        """Test evidence summary with no matches"""
        summary = EvidenceSummary(
            total_cases_searched=50,
            compliant_cases_found=0,
            confidence_level="low",
            evidence_narrative="No compliant precedent cases found.",
        )
        assert summary.compliant_cases_found == 0
        assert summary.confidence_level == "low"
        assert summary.strongest_match_score == 0.0


class TestPrecedentValidationEnhancements:
    """Tests for the enhanced PrecedentValidation model"""

    def test_precedent_with_evidence_summary(self):
        """Test PrecedentValidation includes evidence summary"""
        pv = PrecedentValidation(
            total_matches=10,
            compliant_matches=3,
            has_valid_precedent=True,
            matching_cases=[
                CaseMatch(
                    case_id="1",
                    case_ref_id="REF-001",
                    case_status="Completed",
                    origin_country="UK",
                    receiving_country="India",
                    is_compliant=True,
                    match_score=0.9,
                ),
            ],
            evidence_summary=EvidenceSummary(
                total_cases_searched=10,
                compliant_cases_found=3,
                strongest_match_score=0.9,
                strongest_match_case_id="REF-001",
                confidence_level="high",
                evidence_narrative="Strong precedent found.",
            ),
            message="Found 3 compliant cases",
        )
        assert pv.evidence_summary is not None
        assert pv.evidence_summary.confidence_level == "high"


class TestEvaluationResponseEnhancements:
    """Tests for the enhanced RulesEvaluationResponse"""

    def test_response_with_evidence_summary(self):
        """Test that evaluation response includes evidence summary"""
        response = RulesEvaluationResponse(
            transfer_status=TransferStatus.ALLOWED,
            origin_country="United Kingdom",
            receiving_country="Germany",
            pii=False,
            message="Transfer ALLOWED",
            evidence_summary=EvidenceSummary(
                total_cases_searched=50,
                compliant_cases_found=5,
                confidence_level="high",
                evidence_narrative="Strong precedent exists.",
            ),
        )
        assert response.evidence_summary is not None
        assert response.evidence_summary.confidence_level == "high"

    def test_response_without_evidence(self):
        """Test response without evidence summary (backward compatible)"""
        response = RulesEvaluationResponse(
            transfer_status=TransferStatus.PROHIBITED,
            origin_country="US",
            receiving_country="China",
            pii=True,
            message="Transfer PROHIBITED",
        )
        assert response.evidence_summary is None


class TestAgentModels:
    """Tests for agent tracking models"""

    def test_agent_action_entry(self):
        """Test AgentActionEntry model"""
        entry = AgentActionEntry(
            entry_id="abc123",
            action_type="rule_analysis",
            agent_name="RuleAnalyzer",
            status="completed",
            input_summary="Analyzing rule...",
            output_summary="Rule analyzed successfully",
            duration_ms=150.5,
            timestamp="2025-01-01T00:00:00",
        )
        assert entry.entry_id == "abc123"
        assert entry.duration_ms == 150.5

    def test_agent_session_summary(self):
        """Test AgentSessionSummary model"""
        session = AgentSessionSummary(
            session_id="sess-001",
            correlation_id="COR-ABC123",
            session_type="rule_generation",
            status="completed",
            total_actions=4,
            successful_actions=3,
            failed_actions=1,
            pending_approvals=0,
            agentic_mode=True,
            actions=[
                AgentActionEntry(
                    entry_id="e1",
                    action_type="rule_analysis",
                    agent_name="Analyzer",
                    status="completed",
                ),
            ],
        )
        assert session.agentic_mode is True
        assert session.total_actions == 4
        assert len(session.actions) == 1

    def test_reference_data_result(self):
        """Test ReferenceDataResult model"""
        result = ReferenceDataResult(
            created=True,
            data_type="country_group",
            name="ASEAN_COUNTRIES",
            details={"countries": ["Singapore", "Malaysia", "Thailand"]},
            requires_approval=True,
            approval_status="pending",
        )
        assert result.created is True
        assert result.data_type == "country_group"
        assert len(result.details["countries"]) == 3

    def test_ai_generation_response_with_agentic(self):
        """Test AIRuleGenerationResponse with agentic mode outputs"""
        response = AIRuleGenerationResponse(
            success=True,
            rule_id="RULE_AUTO_TEST",
            rule_type="attribute",
            message="Generated with agentic mode",
            agentic_mode=True,
            reference_data_created=[
                ReferenceDataResult(
                    created=True,
                    data_type="attribute_config",
                    name="test_data",
                    details={"keywords_count": 30},
                    requires_approval=True,
                ),
            ],
            agent_session=AgentSessionSummary(
                session_id="s1",
                correlation_id="COR-001",
                session_type="rule_generation",
                status="completed",
                total_actions=3,
                agentic_mode=True,
            ),
        )
        assert response.agentic_mode is True
        assert len(response.reference_data_created) == 1
        assert response.agent_session is not None
        assert response.agent_session.agentic_mode is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

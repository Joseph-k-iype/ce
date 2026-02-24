"""
Test Rule Spec Validation + Evaluator Integration
=================================================
Tests that:
1. RuleSpec rejects malformed rules at ingestion time
2. Evaluator entity-gating logic works end-to-end
3. AND-across-dimensions enforcement is correct
4. Keyword matching can't bypass entity requirements
"""

import unittest
from unittest.mock import MagicMock
from models.rule_spec import RuleSpec, RuleType, RuleMatchingMode
from services.rules_evaluator import RulesEvaluator, EvaluationContext


class TestRuleSpecValidation(unittest.TestCase):
    """Test RuleSpec ingestion-time validation."""

    def test_valid_attribute_rule_with_entities(self):
        """Attribute rule with entity dimensions → valid."""
        spec = RuleSpec(
            rule_id='R1', name='GDPR Health Data',
            rule_type=RuleType.ATTRIBUTE,
            required_data_categories=['Health Data'],
            required_regulators=['ICO'],
        )
        self.assertEqual(spec.entity_dimension_count, 2)
        self.assertTrue(spec.has_entity_dimensions)
        self.assertEqual(spec.matching_mode, RuleMatchingMode.ALL_DIMENSIONS)

    def test_valid_attribute_rule_with_keywords_only(self):
        """Attribute rule with keywords (no entities) → valid."""
        spec = RuleSpec(
            rule_id='R2', name='PII Keyword Rule',
            rule_type=RuleType.ATTRIBUTE,
            keywords=['social security', 'passport'],
        )
        self.assertFalse(spec.has_entity_dimensions)

    def test_invalid_attribute_rule_empty(self):
        """Attribute rule with NO entities AND NO keywords → REJECTED."""
        with self.assertRaises(ValueError) as ctx:
            RuleSpec(
                rule_id='BAD', name='Empty Rule',
                rule_type=RuleType.ATTRIBUTE,
            )
        self.assertIn('entity dimension', str(ctx.exception))

    def test_case_matching_rule_no_entities_ok(self):
        """Case_matching rules don't need entities → valid."""
        spec = RuleSpec(
            rule_id='R3', name='TIA Rule',
            rule_type=RuleType.CASE_MATCHING,
        )
        self.assertFalse(spec.has_entity_dimensions)

    def test_specific_origin_requires_countries(self):
        """origin_match_type='specific' without countries → REJECTED."""
        with self.assertRaises(ValueError) as ctx:
            RuleSpec(
                rule_id='BAD2', name='No Countries',
                rule_type=RuleType.CASE_MATCHING,
                origin_match_type='specific',
                origin_countries=[],  # empty!
            )
        self.assertIn('origin country', str(ctx.exception))

    def test_not_in_receiving_requires_countries(self):
        """receiving_match_type='not_in' without countries → REJECTED."""
        with self.assertRaises(ValueError):
            RuleSpec(
                rule_id='BAD3', name='No Receiving',
                rule_type=RuleType.CASE_MATCHING,
                receiving_match_type='not_in',
                receiving_countries=[],
            )

    def test_entity_dimension_count(self):
        """Count tracks how many entity types are specified."""
        spec = RuleSpec(
            rule_id='R4', name='Multi-dim',
            rule_type=RuleType.ATTRIBUTE,
            required_data_categories=['A'],
            required_regulators=['B'],
            required_purposes=['C'],
        )
        self.assertEqual(spec.entity_dimension_count, 3)


class TestEvaluatorEntityGating(unittest.TestCase):
    """Test that the evaluator's Phase 1 filter correctly gates rules
    by entity dimensions before allowing keyword matches."""

    def setUp(self):
        self.evaluator = RulesEvaluator.__new__(RulesEvaluator)
        self.evaluator.db = MagicMock()
        self.evaluator.cache = MagicMock()
        self.evaluator.attribute_detector = MagicMock()
        self.evaluator._rules_graph = MagicMock()
        self.evaluator._graph_query = MagicMock(return_value=[])

    def _ctx(self, **kw):
        defaults = dict(
            origin_country='UK', receiving_country='India',
            purposes=[], process_l1=[], process_l2=[], process_l3=[],
            personal_data_names=[], data_categories=[], metadata={},
            detected_attributes=[], data_subjects=[], regulators=[],
            authorities=[], triggered_node_mappings={},
        )
        defaults.update(kw)
        return EvaluationContext(**defaults)

    # ── Single dimension: correct entity → match ───────────────────
    def test_regulator_match(self):
        ctx = self._ctx(regulators=['ICO'])
        rule = {
            'rule_id': 'R10', 'linked_attributes': [],
            'linked_data_categories': [], 'linked_purposes': [],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': [], 'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        self.assertTrue(self.evaluator._match_graph_linked_attributes(ctx, rule))

    # ── Single dimension: wrong entity → no match ─────────────────
    def test_regulator_wrong(self):
        ctx = self._ctx(regulators=['CNIL'])
        rule = {
            'rule_id': 'R11', 'linked_attributes': [],
            'linked_data_categories': [], 'linked_purposes': [],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': [], 'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        self.assertFalse(self.evaluator._match_graph_linked_attributes(ctx, rule))

    # ── AND-across: 2 dims, both match → fire ──────────────────────
    def test_two_dims_both_match(self):
        ctx = self._ctx(data_categories=['Health'], regulators=['ICO'])
        rule = {
            'rule_id': 'R12', 'linked_attributes': [],
            'linked_data_categories': ['Health'], 'linked_purposes': [],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': [], 'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        self.assertTrue(self.evaluator._match_graph_linked_attributes(ctx, rule))
        self.assertIn('DataCategory', ctx.triggered_node_mappings.get('R12', {}))
        self.assertIn('Regulator', ctx.triggered_node_mappings.get('R12', {}))

    # ── AND-across: 2 dims, only one matches → skip ────────────────
    def test_two_dims_one_wrong(self):
        ctx = self._ctx(data_categories=['Health'], regulators=['CNIL'])
        rule = {
            'rule_id': 'R13', 'linked_attributes': [],
            'linked_data_categories': ['Health'], 'linked_purposes': [],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': [], 'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        self.assertFalse(self.evaluator._match_graph_linked_attributes(ctx, rule))

    # ── 4 dimensions: all correct → fire ───────────────────────────
    def test_four_dims_all_correct(self):
        ctx = self._ctx(
            data_categories=['Financial'],
            regulators=['FCA'],
            purposes=['Anti-Money Laundering'],
            data_subjects=['Customers'],
        )
        rule = {
            'rule_id': 'R14', 'linked_attributes': [],
            'linked_data_categories': ['Financial'],
            'linked_purposes': ['Anti-Money Laundering'],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': ['Customers'],
            'linked_regulators': ['FCA'],
            'linked_authorities': [],
        }
        self.assertTrue(self.evaluator._match_graph_linked_attributes(ctx, rule))
        mappings = ctx.triggered_node_mappings['R14']
        self.assertEqual(len(mappings), 4)

    # ── 4 dimensions: 3 correct, 1 wrong → skip ───────────────────
    def test_four_dims_one_wrong(self):
        ctx = self._ctx(
            data_categories=['Financial'],
            regulators=['FCA'],
            purposes=['Marketing'],  # WRONG
            data_subjects=['Customers'],
        )
        rule = {
            'rule_id': 'R15', 'linked_attributes': [],
            'linked_data_categories': ['Financial'],
            'linked_purposes': ['Anti-Money Laundering'],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': ['Customers'],
            'linked_regulators': ['FCA'],
            'linked_authorities': [],
        }
        self.assertFalse(self.evaluator._match_graph_linked_attributes(ctx, rule))

    # ── OR-within-dimension: multiple values in one dim ────────────
    def test_or_within_dimension(self):
        """Rule linked to DataCategory:[Health, Financial], user provides Financial → match."""
        ctx = self._ctx(data_categories=['Financial Data'])
        rule = {
            'rule_id': 'R16', 'linked_attributes': [],
            'linked_data_categories': ['Health Data', 'Financial Data'],
            'linked_purposes': [],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': [], 'linked_regulators': [],
            'linked_authorities': [],
        }
        self.assertTrue(self.evaluator._match_graph_linked_attributes(ctx, rule))

    # ── Empty context for a required dimension → skip ──────────────
    def test_empty_context_for_required_dim(self):
        """Rule requires DataCategory but user provides none → skip."""
        ctx = self._ctx(data_categories=[])
        rule = {
            'rule_id': 'R17', 'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': [],
            'linked_processes': [], 'linked_gdcs': [],
            'linked_data_subjects': [], 'linked_regulators': [],
            'linked_authorities': [],
        }
        self.assertFalse(self.evaluator._match_graph_linked_attributes(ctx, rule))


if __name__ == '__main__':
    unittest.main()

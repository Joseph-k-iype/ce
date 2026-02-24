"""
Test Rule Triggering Logic
==========================
Verifies that:
1. AND-across-dimensions: Rules linked to multiple entity dimensions
   only fire when ALL dimensions match (not just ANY).
2. Entity gating: Keywords alone can't bypass entity dimension checks.
3. Wrong entity selection: A rule does NOT fire when the user selects
   entities that don't match the rule's linked entities.
"""

import unittest
from unittest.mock import MagicMock, patch
from dataclasses import field
from services.rules_evaluator import RulesEvaluator, EvaluationContext, _normalize_text


class TestMatchGraphLinkedAttributes(unittest.TestCase):
    """Test _match_graph_linked_attributes for rule triggering correctness."""

    def setUp(self):
        """Create evaluator with mocked graph."""
        self.evaluator = RulesEvaluator.__new__(RulesEvaluator)
        self.evaluator.db = MagicMock()
        self.evaluator.cache = MagicMock()
        self.evaluator.attribute_detector = MagicMock()
        self.evaluator._rules_graph = MagicMock()
        # Mock _graph_query to return empty for process ancestors
        self.evaluator._graph_query = MagicMock(return_value=[])

    def _make_context(self, **kwargs):
        """Create EvaluationContext with given fields."""
        defaults = {
            'origin_country': 'United Kingdom',
            'receiving_country': 'India',
            'pii': False,
            'purposes': [],
            'process_l1': [],
            'process_l2': [],
            'process_l3': [],
            'personal_data_names': [],
            'data_categories': [],
            'metadata': {},
            'detected_attributes': [],
            'data_subjects': [],
            'regulators': [],
            'authorities': [],
            'triggered_node_mappings': {},
        }
        defaults.update(kwargs)
        return EvaluationContext(**defaults)

    # ───────────────────────────────────────────────────────────────────
    # Scenario 1: Single dimension match → should fire
    # ───────────────────────────────────────────────────────────────────
    def test_single_data_category_match(self):
        """Rule linked to DataCategory:HealthData, context has HealthData → match."""
        ctx = self._make_context(data_categories=['Health Data'])
        rule_row = {
            'rule_id': 'R1',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': [],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertTrue(result, "Should match when DataCategory overlaps")
        self.assertIn('DataCategory', ctx.triggered_node_mappings.get('R1', {}))

    # ───────────────────────────────────────────────────────────────────
    # Scenario 2: Single dimension WRONG entity → should NOT fire
    # ───────────────────────────────────────────────────────────────────
    def test_single_data_category_wrong_entity(self):
        """Rule linked to DataCategory:HealthData, context has 'Financial Data' → NO match."""
        ctx = self._make_context(data_categories=['Financial Data'])
        rule_row = {
            'rule_id': 'R2',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': [],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertFalse(result, "Should NOT match when DataCategory doesn't overlap")

    # ───────────────────────────────────────────────────────────────────
    # Scenario 3: Multi-dimension AND — both match → should fire
    # ───────────────────────────────────────────────────────────────────
    def test_multi_dimension_all_match(self):
        """Rule linked to DataCategory:HealthData AND Regulator:ICO,
        context has both → should match."""
        ctx = self._make_context(
            data_categories=['Health Data'],
            regulators=['ICO'],
        )
        rule_row = {
            'rule_id': 'R3',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertTrue(result, "Should match when ALL dimensions overlap")
        mappings = ctx.triggered_node_mappings.get('R3', {})
        self.assertIn('DataCategory', mappings)
        self.assertIn('Regulator', mappings)

    # ───────────────────────────────────────────────────────────────────
    # Scenario 4: Multi-dimension AND — only ONE matches → should NOT fire
    # ───────────────────────────────────────────────────────────────────
    def test_multi_dimension_partial_match_fails(self):
        """Rule linked to DataCategory:HealthData AND Regulator:ICO,
        context has HealthData but wrong regulator → should NOT match."""
        ctx = self._make_context(
            data_categories=['Health Data'],
            regulators=['CNIL'],  # Wrong regulator
        )
        rule_row = {
            'rule_id': 'R4',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertFalse(result, "Should NOT match when only ONE dimension overlaps (AND logic)")

    # ───────────────────────────────────────────────────────────────────
    # Scenario 5: Multi-dimension AND — one dimension has NO input → should NOT fire
    # ───────────────────────────────────────────────────────────────────
    def test_multi_dimension_missing_dimension_fails(self):
        """Rule linked to DataCategory:HealthData AND Regulator:ICO,
        context has HealthData but NO regulators at all → should NOT match."""
        ctx = self._make_context(
            data_categories=['Health Data'],
            regulators=[],  # No regulators provided
        )
        rule_row = {
            'rule_id': 'R5',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertFalse(result, "Should NOT match when one dimension is empty")

    # ───────────────────────────────────────────────────────────────────
    # Scenario 6: Three dimensions — all match → should fire
    # ───────────────────────────────────────────────────────────────────
    def test_three_dimensions_all_match(self):
        """Rule linked to DataCategory + Regulator + Purpose, all present → match."""
        ctx = self._make_context(
            data_categories=['Health Data'],
            regulators=['ICO'],
            purposes=['Risk Management'],
        )
        rule_row = {
            'rule_id': 'R6',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': ['Risk Management'],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertTrue(result, "Should match when all 3 dimensions overlap")

    # ───────────────────────────────────────────────────────────────────
    # Scenario 7: Three dimensions — two match, one wrong → should NOT fire
    # ───────────────────────────────────────────────────────────────────
    def test_three_dimensions_one_wrong(self):
        """Rule linked to DataCategory + Regulator + Purpose,
        context has wrong purpose → should NOT match."""
        ctx = self._make_context(
            data_categories=['Health Data'],
            regulators=['ICO'],
            purposes=['Marketing'],  # Wrong purpose
        )
        rule_row = {
            'rule_id': 'R7',
            'linked_attributes': [],
            'linked_data_categories': ['Health Data'],
            'linked_purposes': ['Risk Management'],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': ['ICO'],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertFalse(result, "Should NOT match when 1 of 3 dimensions is wrong")

    # ───────────────────────────────────────────────────────────────────
    # Scenario 8: No linked entities → should NOT fire
    # ───────────────────────────────────────────────────────────────────
    def test_no_linked_entities_returns_false(self):
        """Rule with no linked entities at all → returns False."""
        ctx = self._make_context(data_categories=['Health Data'])
        rule_row = {
            'rule_id': 'R8',
            'linked_attributes': [],
            'linked_data_categories': [],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': [],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertFalse(result, "No linked entities → should NOT match")

    # ───────────────────────────────────────────────────────────────────
    # Scenario 9: Case-insensitive matching
    # ───────────────────────────────────────────────────────────────────
    def test_case_insensitive_match(self):
        """Entity matching should be case-insensitive."""
        ctx = self._make_context(data_categories=['HEALTH DATA'])
        rule_row = {
            'rule_id': 'R9',
            'linked_attributes': [],
            'linked_data_categories': ['health data'],
            'linked_purposes': [],
            'linked_processes': [],
            'linked_gdcs': [],
            'linked_data_subjects': [],
            'linked_regulators': [],
            'linked_authorities': [],
        }
        result = self.evaluator._match_graph_linked_attributes(ctx, rule_row)
        self.assertTrue(result, "Case-insensitive matching should work")


if __name__ == '__main__':
    unittest.main()

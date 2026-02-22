"""
Tests for the Policy Editor API endpoints.
Tests lane configuration, country expansion, and CSV validation.
"""

import csv
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import asyncio
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.schema_manager import get_all_lanes, get_protected_relationships

# Helpers to match previous constants
def _get_primary_lanes():
    return [l for l in get_all_lanes() if l.get("primary")]

def _get_extra_lanes():
    return [l for l in get_all_lanes() if not l.get("primary")]

_PRIMARY_LANES = _get_primary_lanes()
_EXTRA_LANES = _get_extra_lanes()
PROTECTED_RELATIONSHIPS = get_protected_relationships()


class TestLaneConfiguration:
    """Verify lane definitions are correct after the GDC→Processes remap."""

    def test_primary_lanes_has_7_entries(self):
        assert len(_PRIMARY_LANES) == 7

    def test_processes_lane_is_primary(self):
        processes = [l for l in _PRIMARY_LANES if l["id"] == "processes"]
        assert len(processes) == 1
        assert processes[0]["label"] == "Processes"
        assert processes[0]["order"] == 5
        assert processes[0]["primary"] is True

    def test_gdc_is_extra_lane(self):
        gdc = [l for l in _EXTRA_LANES if l["id"] == "gdc"]
        assert len(gdc) == 1
        assert gdc[0]["primary"] is False

    def test_all_primary_lane_ids(self):
        ids = {l["id"] for l in _PRIMARY_LANES}
        expected = {"originCountry", "receivingCountry", "rule", "dataCategory", "purpose", "processes", "caseModule"}
        assert ids == expected

    def test_lane_orders_are_unique(self):
        all_lanes = _PRIMARY_LANES + _EXTRA_LANES
        orders = [l["order"] for l in all_lanes]
        assert len(orders) == len(set(orders)), "Duplicate order values found"

    def test_lane_orders_are_sequential(self):
        all_lanes = sorted(_PRIMARY_LANES + _EXTRA_LANES, key=lambda l: l["order"])
        for i, lane in enumerate(all_lanes):
            assert lane["order"] == i, f"Gap in lane order at index {i}"


class TestCSVValidation:
    """Test CSV validation helper."""

    def test_csv_validation_missing_required_col(self):
        from utils.graph_builder import validate_csv_schema

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['category'])
            writer.writerow(['Test'])
            f.flush()

            errors = validate_csv_schema(Path(f.name), required_cols=['name'])
            assert len(errors) == 1
            assert "name" in errors[0]

    def test_csv_validation_all_cols_present(self):
        from utils.graph_builder import validate_csv_schema

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'category'])
            writer.writerow(['test_1', 'Test', 'Cat'])
            f.flush()

            errors = validate_csv_schema(Path(f.name), required_cols=['name'], optional_cols=['id', 'category'])
            assert len(errors) == 0

    def test_csv_validation_with_id_column(self):
        from utils.graph_builder import validate_csv_schema

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'category'])
            writer.writerow(['proc_1', 'Payment Processing', 'Financial Operations'])
            f.flush()

            errors = validate_csv_schema(Path(f.name), required_cols=['name', 'id'])
            assert len(errors) == 0


class TestEditorNetworkResponse:
    """Test the editor-network endpoint response structure (mocked DB)."""

    def _make_mock_db(self, query_results=None):
        """Create a mock DB service.
        Keys are matched against query strings with substring check.
        More specific keys should be listed first in the dict to avoid false matches.
        """
        mock_db = MagicMock()
        if query_results is None:
            query_results = {}

        def mock_execute(query, params=None):
            # Match most specific key first (longest match)
            best_key = None
            best_len = 0
            for key in query_results:
                if key in query and len(key) > best_len:
                    best_key = key
                    best_len = len(key)
            if best_key is not None:
                return query_results[best_key]
            return []

        mock_db.execute_rules_query = mock_execute
        return mock_db

    def test_editor_network_returns_lanes(self):
        """Verify the response includes all lane definitions."""
        from api.routers.graph_data import get_editor_network

        mock_db = self._make_mock_db()
        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            result = asyncio.run(get_editor_network(expand_countries=True, db=mock_db))
            assert "lanes" in result
            lane_ids = {l["id"] for l in result["lanes"]}
            for primary in _PRIMARY_LANES:
                assert primary["id"] in lane_ids

    def test_editor_network_process_lane(self):
        """Verify Process nodes get lane='processes' and type='processNode'."""
        from api.routers.graph_data import get_editor_network

        mock_db = self._make_mock_db({
            "MATCH (r:Rule)": [
                {"rule_id": "R1", "name": "Test Rule", "description": "", "priority": "high",
                 "odrl_type": "Permission", "has_pii_required": False,
                 "origin_match_type": "any", "receiving_match_type": "any"}
            ],
            "HAS_PROCESS]->(n:Process)": [
                {"rule_id": "R1", "name": "Payment Processing"}
            ],
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            result = asyncio.run(get_editor_network(expand_countries=True, db=mock_db))
            process_nodes = [n for n in result["nodes"]
                            if n["type"] == "processNode" and n["data"].get("nodeType") == "Process"]
            assert len(process_nodes) == 1
            assert process_nodes[0]["data"]["lane"] == "processes"

    def test_editor_network_expands_countries(self):
        """Verify CountryGroup expansion creates countryNode (not countryGroupNode)."""
        from api.routers.graph_data import get_editor_network

        mock_db = self._make_mock_db({
            "MATCH (r:Rule)": [
                {"rule_id": "R1", "name": "Test Rule", "description": "", "priority": "high",
                 "odrl_type": "Permission", "has_pii_required": False,
                 "origin_match_type": "group", "receiving_match_type": "any"}
            ],
            "OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)": [
                {"group_name": "EU_EEA", "countries": ["France", "Germany", "Italy"]}
            ],
            "TRIGGERED_BY_ORIGIN]->(cg:CountryGroup)": [
                {"rule_id": "R1", "group_name": "EU_EEA"}
            ],
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            result = asyncio.run(get_editor_network(expand_countries=True, db=mock_db))
            country_nodes = [n for n in result["nodes"] if n["type"] == "countryNode"]
            country_group_nodes = [n for n in result["nodes"] if n["type"] == "countryGroupNode"]

            assert len(country_group_nodes) == 0, "Should not have countryGroupNode when expanded"
            assert len(country_nodes) == 3, f"Expected 3 country nodes, got {len(country_nodes)}"

            country_names = {n["data"]["label"] for n in country_nodes}
            assert country_names == {"France", "Germany", "Italy"}

    def test_editor_network_country_dedup(self):
        """Same country should appear once per lane even if in multiple groups."""
        from api.routers.graph_data import get_editor_network

        mock_db = self._make_mock_db({
            "MATCH (r:Rule)": [
                {"rule_id": "R1", "name": "Rule 1", "description": "", "priority": "high",
                 "odrl_type": "Permission", "has_pii_required": False,
                 "origin_match_type": "group", "receiving_match_type": "any"},
                {"rule_id": "R2", "name": "Rule 2", "description": "", "priority": "high",
                 "odrl_type": "Permission", "has_pii_required": False,
                 "origin_match_type": "group", "receiving_match_type": "any"},
            ],
            "OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)": [
                {"group_name": "GROUP_A", "countries": ["France", "Germany"]},
                {"group_name": "GROUP_B", "countries": ["France", "Italy"]},
            ],
            "TRIGGERED_BY_ORIGIN]->(cg:CountryGroup)": [
                {"rule_id": "R1", "group_name": "GROUP_A"},
                {"rule_id": "R2", "group_name": "GROUP_B"},
            ],
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            result = asyncio.run(get_editor_network(expand_countries=True, db=mock_db))
            origin_country_nodes = [
                n for n in result["nodes"]
                if n["type"] == "countryNode" and n["data"]["lane"] == "originCountry"
            ]
            names = [n["data"]["label"] for n in origin_country_nodes]
            assert names.count("France") == 1
            assert len(origin_country_nodes) == 3  # France, Germany, Italy

    def test_editor_network_action_goes_to_processes(self):
        """Verify Action nodes get lane='processes' not 'caseModule'."""
        from api.routers.graph_data import get_editor_network

        mock_db = self._make_mock_db({
            "MATCH (r:Rule)": [
                {"rule_id": "R1", "name": "Test Rule", "description": "", "priority": "high",
                 "odrl_type": "Permission", "has_pii_required": False,
                 "origin_match_type": "any", "receiving_match_type": "any"}
            ],
            "HAS_ACTION": [
                {"rule_id": "R1", "name": "Transfer Data"}
            ],
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            result = asyncio.run(get_editor_network(expand_countries=True, db=mock_db))
            action_nodes = [n for n in result["nodes"] if n["data"].get("nodeType") == "Action"]
            for node in action_nodes:
                assert node["data"]["lane"] == "processes", "Action nodes should be in processes lane"
                assert node["type"] == "processNode", "Action nodes should use processNode type"

    def test_editor_network_duty_goes_to_case_module(self):
        """Verify Duty nodes get lane='caseModule'."""
        from api.routers.graph_data import get_editor_network

        mock_db = self._make_mock_db({
            "MATCH (r:Rule)": [
                {"rule_id": "R1", "name": "Test Rule", "description": "", "priority": "high",
                 "odrl_type": "Permission", "has_pii_required": False,
                 "origin_match_type": "any", "receiving_match_type": "any"}
            ],
            "HAS_DUTY": [
                {"rule_id": "R1", "name": "TIA"}
            ],
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            result = asyncio.run(get_editor_network(expand_countries=True, db=mock_db))
            duty_nodes = [n for n in result["nodes"] if n["data"].get("nodeType") == "Duty"]
            assert len(duty_nodes) == 1
            assert duty_nodes[0]["data"]["lane"] == "caseModule"


class TestCRUDEndpoints:
    """Test CRUD endpoint logic for the policy editor."""

    def _make_mock_db(self, query_results=None):
        mock_db = MagicMock()
        if query_results is None:
            query_results = {}

        def mock_execute(query, params=None):
            for key in query_results:
                if key in query:
                    return query_results[key]
            return []

        mock_db.execute_rules_query = mock_execute
        return mock_db

    def test_update_node_endpoint(self):
        """PUT updates node properties."""
        from api.routers.graph_data import update_editor_node, UpdateNodeRequest

        mock_db = self._make_mock_db({"SET": [{"n": {"name": "Test"}}]})

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            request = UpdateNodeRequest(properties={"description": "Updated"})
            result = asyncio.run(update_editor_node("rule_R1", request, db=mock_db))
            assert result["status"] == "ok"

    def test_delete_node_with_protected_rels(self):
        """DELETE returns 400 for nodes with protected edges."""
        from api.routers.graph_data import delete_editor_node

        mock_db = self._make_mock_db({
            "type(r)": [{"rel_type": "TRIGGERED_BY_ORIGIN"}]
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            with pytest.raises(Exception) as exc_info:
                asyncio.run(delete_editor_node("rule_R1", db=mock_db))
            # Should raise HTTPException with 400
            assert "400" in str(exc_info.value) or "protected" in str(exc_info.value).lower()

    def test_create_edge_protected_type(self):
        """POST returns 400 for protected relationship types."""
        from api.routers.graph_data import create_editor_edge, CreateEdgeRequest

        mock_db = self._make_mock_db()

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            request = CreateEdgeRequest(
                source_id="rule_R1",
                target_id="country_France_origin",
                relationship_type="TRIGGERED_BY_ORIGIN"
            )
            with pytest.raises(Exception) as exc_info:
                asyncio.run(create_editor_edge(request, db=mock_db))
            assert "400" in str(exc_info.value) or "protected" in str(exc_info.value).lower()

    def test_create_edge_allowed_type(self):
        """POST succeeds for non-protected relationship types."""
        from api.routers.graph_data import create_editor_edge, CreateEdgeRequest

        mock_db = self._make_mock_db({
            "CREATE": [{"r": {}}]
        })

        with patch('api.routers.graph_data.get_cache_service') as mock_cache:
            mock_cache.return_value.get.return_value = None

            request = CreateEdgeRequest(
                source_id="rule_R1",
                target_id="process_Payment",
                relationship_type="HAS_PROCESS"
            )
            result = asyncio.run(create_editor_edge(request, db=mock_db))
            assert result["status"] == "ok"

    def test_protected_relationships_set(self):
        """Verify the protected relationships constant."""
        assert "TRIGGERED_BY_ORIGIN" in PROTECTED_RELATIONSHIPS
        assert "TRIGGERED_BY_RECEIVING" in PROTECTED_RELATIONSHIPS
        assert "BELONGS_TO" in PROTECTED_RELATIONSHIPS
        assert "EXCLUDES_RECEIVING" in PROTECTED_RELATIONSHIPS
        assert "HAS_PROCESS" not in PROTECTED_RELATIONSHIPS

"""
Graph Relevance Service
=======================
Analyzes rule text and extracted entities to detect relevant external graphs for precedent search.

Scoring Algorithm:
- Entity Match (40%): Graph data matches extracted entities
- Keyword Match (30%): Rule text contains terms from graph data
- Schema Compatibility (20%): Graph node labels align with rule dimensions
- Data Freshness (10%): Recently imported graphs preferred
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import re
from collections import Counter

from services.graph_registry import get_graph_registry, GraphMetadata
from services.multi_graph_query import MultiGraphQuery

logger = logging.getLogger(__name__)


@dataclass
class GraphSuggestion:
    """Suggestion for a relevant graph with scoring details."""
    graph_name: str
    relevance_score: float  # 0.0 to 1.0
    reasoning: str
    matched_entities: Dict[str, List[str]]
    sample_data: List[Dict[str, Any]]
    node_count: int


class GraphRelevanceService:
    """Service to analyze and score graph relevance for rule precedent search."""

    # Dimension mapping from rule entities to expected graph node labels
    DIMENSION_TO_NODE_LABELS = {
        "data_categories": ["DataCategory", "Category", "Data"],
        "purposes": ["Purpose", "ProcessingPurpose"],
        "processes": ["Process", "ProcessingActivity", "Activity"],
        "regulators": ["Regulator", "RegulatoryBody"],
        "authorities": ["Authority", "SupervisoryAuthority"],
        "data_subjects": ["DataSubject", "Subject"],
        "gdc": ["GDC", "GroupDataCategory"],
        "sensitive_data_categories": ["SensitiveDataCategory", "SpecialCategory"],
    }

    # Minimum relevance score to be included in suggestions
    MIN_RELEVANCE_SCORE = 0.3

    # Maximum number of suggestions to return
    MAX_SUGGESTIONS = 5

    def __init__(self):
        """Initialize the graph relevance service."""
        self.registry = get_graph_registry()
        self.multi_query = MultiGraphQuery()
        self._cached_graph_data: Dict[str, Any] = {}

    def analyze_graph_relevance(
        self,
        rule_text: str,
        extracted_entities: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Analyze all external graphs and return relevance-ranked suggestions.

        Args:
            rule_text: The rule text entered by the user
            extracted_entities: Entities extracted by AI (data_categories, purposes, etc.)

        Returns:
            Dictionary with:
                - relevant_graphs: List[GraphSuggestion]
                - confidence: Overall confidence in suggestions (0.0-1.0)
                - recommendation: "high" | "medium" | "low" | "none"
        """
        # Get all external graphs
        external_graphs = [
            g for g in self.registry.list_graphs()
            if g.graph_type == "external" and g.enabled
        ]

        if not external_graphs:
            logger.info("No external graphs available for relevance analysis")
            return {
                "relevant_graphs": [],
                "confidence": 0.0,
                "recommendation": "none"
            }

        logger.info(f"Analyzing relevance for {len(external_graphs)} external graphs")

        # Score each graph
        scored_graphs: List[GraphSuggestion] = []
        for graph_meta in external_graphs:
            try:
                suggestion = self._score_graph(graph_meta, rule_text, extracted_entities)
                if suggestion and suggestion.relevance_score >= self.MIN_RELEVANCE_SCORE:
                    scored_graphs.append(suggestion)
            except Exception as e:
                logger.warning(f"Failed to score graph {graph_meta.name}: {e}")
                continue

        # Sort by relevance score descending
        scored_graphs.sort(key=lambda x: x.relevance_score, reverse=True)

        # Limit to top suggestions
        top_suggestions = scored_graphs[:self.MAX_SUGGESTIONS]

        # Calculate overall confidence
        if not top_suggestions:
            confidence = 0.0
            recommendation = "none"
        else:
            # Average of top 2 scores (or just top 1 if only one suggestion)
            top_scores = [s.relevance_score for s in top_suggestions[:2]]
            confidence = sum(top_scores) / len(top_scores)

            if confidence >= 0.7:
                recommendation = "high"
            elif confidence >= 0.4:
                recommendation = "medium"
            else:
                recommendation = "low"

        logger.info(
            f"Graph relevance analysis complete: {len(top_suggestions)} suggestions, "
            f"confidence={confidence:.2f}, recommendation={recommendation}"
        )

        return {
            "relevant_graphs": [
                {
                    "graph_name": s.graph_name,
                    "relevance_score": s.relevance_score,
                    "reasoning": s.reasoning,
                    "matched_entities": s.matched_entities,
                    "sample_data": s.sample_data,
                    "node_count": s.node_count
                }
                for s in top_suggestions
            ],
            "confidence": confidence,
            "recommendation": recommendation
        }

    def _score_graph(
        self,
        graph_meta: GraphMetadata,
        rule_text: str,
        extracted_entities: Dict[str, List[str]]
    ) -> Optional[GraphSuggestion]:
        """
        Score a single graph's relevance.

        Returns:
            GraphSuggestion or None if graph couldn't be scored
        """
        # Get graph data (with caching)
        graph_data = self._get_graph_data(graph_meta.name)
        if not graph_data:
            return None

        # Calculate component scores
        entity_score, matched_entities = self._calculate_entity_match_score(
            graph_data, extracted_entities, graph_meta.node_labels
        )
        keyword_score, matched_keywords = self._calculate_keyword_match_score(
            graph_data, rule_text
        )
        schema_score = self._calculate_schema_compatibility_score(
            graph_meta.node_labels, extracted_entities
        )
        freshness_score = self._calculate_freshness_score(graph_meta)

        # Weighted combination
        total_score = (
            entity_score * 0.4 +
            keyword_score * 0.3 +
            schema_score * 0.2 +
            freshness_score * 0.1
        )

        # Generate reasoning
        reasoning_parts = []
        if entity_score > 0.5:
            entity_count = sum(len(v) for v in matched_entities.values())
            reasoning_parts.append(f"Matches {entity_count} entities")
        if keyword_score > 0.5:
            keyword_count = len(matched_keywords)
            reasoning_parts.append(f"{keyword_count} keyword matches")
        if schema_score > 0.7:
            reasoning_parts.append("Schema compatible")

        node_count = graph_meta.metadata.get("row_count", 0)
        if node_count > 0:
            reasoning_parts.append(f"{node_count} nodes")

        reasoning = f"Contains {', '.join(reasoning_parts) if reasoning_parts else 'some relevant data'}"

        return GraphSuggestion(
            graph_name=graph_meta.name,
            relevance_score=round(total_score, 3),
            reasoning=reasoning,
            matched_entities=matched_entities,
            sample_data=graph_data.get("sample_nodes", [])[:3],  # Top 3 samples
            node_count=node_count
        )

    def _get_graph_data(self, graph_name: str) -> Optional[Dict[str, Any]]:
        """
        Get graph data with caching.

        Returns:
            Dictionary with:
                - sample_nodes: List of sample node properties
                - all_properties: Set of all property names across nodes
        """
        if graph_name in self._cached_graph_data:
            return self._cached_graph_data[graph_name]

        try:
            # Query for sample nodes
            result = self.multi_query.query(
                graph_name,
                "MATCH (n) RETURN n LIMIT 10",
                {}
            )

            if not result:
                return None

            sample_nodes = result
            all_properties: Set[str] = set()

            # Extract all property names from sample nodes
            for node in sample_nodes:
                if isinstance(node, dict):
                    all_properties.update(node.keys())

            graph_data = {
                "sample_nodes": sample_nodes,
                "all_properties": all_properties
            }

            self._cached_graph_data[graph_name] = graph_data
            return graph_data

        except Exception as e:
            logger.warning(f"Failed to get graph data for {graph_name}: {e}")
            return None

    def _calculate_entity_match_score(
        self,
        graph_data: Dict[str, Any],
        extracted_entities: Dict[str, List[str]],
        node_labels: Set[str]
    ) -> tuple[float, Dict[str, List[str]]]:
        """
        Calculate score based on how well graph data matches extracted entities.

        Returns:
            (score, matched_entities_dict)
        """
        matched_entities: Dict[str, List[str]] = {}
        total_matches = 0
        total_entities = sum(len(v) for v in extracted_entities.values() if v)

        if total_entities == 0:
            return 0.0, {}

        sample_nodes = graph_data.get("sample_nodes", [])
        if not sample_nodes:
            return 0.0, {}

        # Collect all values from graph nodes
        graph_values: Set[str] = set()
        for node in sample_nodes:
            if isinstance(node, dict):
                for value in node.values():
                    if isinstance(value, str):
                        graph_values.add(value.lower())

        # Check each entity dimension
        for dimension, entity_values in extracted_entities.items():
            if not entity_values:
                continue

            dimension_matches = []
            for entity_value in entity_values:
                entity_lower = entity_value.lower()
                # Check if entity value appears in graph data
                if entity_lower in graph_values or any(entity_lower in gv for gv in graph_values):
                    dimension_matches.append(entity_value)
                    total_matches += 1

            if dimension_matches:
                matched_entities[dimension] = dimension_matches

        score = total_matches / total_entities if total_entities > 0 else 0.0
        return score, matched_entities

    def _calculate_keyword_match_score(
        self,
        graph_data: Dict[str, Any],
        rule_text: str
    ) -> tuple[float, List[str]]:
        """
        Calculate score based on keyword overlap between rule text and graph data.

        Returns:
            (score, matched_keywords)
        """
        if not rule_text:
            return 0.0, []

        # Tokenize rule text (lowercase, remove punctuation)
        rule_tokens = set(re.findall(r'\b[a-z]{3,}\b', rule_text.lower()))

        # Get all text values from graph sample nodes
        graph_text_values: List[str] = []
        for node in graph_data.get("sample_nodes", []):
            if isinstance(node, dict):
                for value in node.values():
                    if isinstance(value, str):
                        graph_text_values.append(value.lower())

        graph_text = " ".join(graph_text_values)
        graph_tokens = set(re.findall(r'\b[a-z]{3,}\b', graph_text))

        # Find common tokens
        common_tokens = rule_tokens & graph_tokens

        # Score based on percentage of rule tokens found in graph
        if not rule_tokens:
            return 0.0, []

        score = len(common_tokens) / len(rule_tokens)
        matched_keywords = list(common_tokens)[:10]  # Top 10 keywords

        return score, matched_keywords

    def _calculate_schema_compatibility_score(
        self,
        graph_node_labels: Set[str],
        extracted_entities: Dict[str, List[str]]
    ) -> float:
        """
        Calculate score based on how well graph schema aligns with rule dimensions.

        Checks if graph node labels match expected labels for each entity dimension.
        """
        if not extracted_entities:
            return 0.0

        compatible_dimensions = 0
        total_dimensions = len([v for v in extracted_entities.values() if v])

        if total_dimensions == 0:
            return 0.0

        # Check each dimension
        for dimension, entities in extracted_entities.items():
            if not entities:
                continue

            expected_labels = self.DIMENSION_TO_NODE_LABELS.get(dimension, [])
            if not expected_labels:
                continue

            # Check if any expected label exists in graph
            if any(label in graph_node_labels for label in expected_labels):
                compatible_dimensions += 1

        score = compatible_dimensions / total_dimensions if total_dimensions > 0 else 0.0
        return score

    def _calculate_freshness_score(self, graph_meta: GraphMetadata) -> float:
        """
        Calculate score based on how recently the graph was created/updated.

        More recent graphs get higher scores.
        """
        if not graph_meta.created_at:
            return 0.5  # Neutral score for unknown age

        now = datetime.now()
        age_days = (now - graph_meta.created_at).days

        # Scoring curve:
        # 0-7 days: 1.0
        # 8-30 days: 0.8
        # 31-90 days: 0.6
        # 91-180 days: 0.4
        # 180+ days: 0.2

        if age_days <= 7:
            return 1.0
        elif age_days <= 30:
            return 0.8
        elif age_days <= 90:
            return 0.6
        elif age_days <= 180:
            return 0.4
        else:
            return 0.2


# Singleton instance
_graph_relevance_service: Optional[GraphRelevanceService] = None


def get_graph_relevance_service() -> GraphRelevanceService:
    """Get or create the singleton GraphRelevanceService instance."""
    global _graph_relevance_service
    if _graph_relevance_service is None:
        _graph_relevance_service = GraphRelevanceService()
    return _graph_relevance_service

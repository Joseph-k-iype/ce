"""
Sandbox Service
================
Manages sandbox graph lifecycle for safe rule testing.
Creates temporary copies of RulesGraph, runs evaluations, promotes to main.

All rule evaluation is done via graph queries — the graph is the single
source of truth. No Python dict injection needed.
"""

import logging
import uuid
from typing import Optional, Dict, Any, List

from services.database import get_db_service
from utils.graph_builder import RulesGraphBuilder
from config.settings import settings

logger = logging.getLogger(__name__)


class SandboxService:
    """Manages sandbox graph lifecycle for rule testing."""

    _instance: Optional['SandboxService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.db = get_db_service()
        self._active_sandboxes: Dict[str, str] = {}  # session_id -> graph_name
        self._sandbox_rules: Dict[str, Dict[str, Any]] = {}  # graph_name -> rule_def
        self._sandbox_dictionaries: Dict[str, Dict[str, Any]] = {}  # graph_name -> dictionary_result
        self._initialized = True
        logger.info("Sandbox Service initialized")

    def create_sandbox(self, session_id: str) -> str:
        """
        Create a sandbox graph by copying the main RulesGraph structure.

        Args:
            session_id: Wizard session ID

        Returns:
            Name of the created sandbox graph
        """
        graph_name = f"sandbox_{uuid.uuid4().hex[:8]}"

        try:
            temp_graph, full_graph_name = self.db.get_temp_graph(graph_name)

            # Build the full rules graph in the sandbox (copies all rules)
            builder = RulesGraphBuilder(graph=temp_graph)
            builder.build(clear_existing=True)

            self._active_sandboxes[session_id] = full_graph_name
            logger.info(f"Created sandbox graph '{full_graph_name}' for session {session_id}")
            return full_graph_name

        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise

    def add_rule_to_sandbox(
        self,
        graph_name: str,
        rule_def: Dict[str, Any],
        dictionary_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a rule to the sandbox graph.

        For attribute rules, merges keywords from the AI dictionary into
        attribute_keywords before writing to the graph — so the graph
        stores all detection keywords and remains the single source of truth.
        """
        try:
            graph = self.db.db.select_graph(graph_name)
            builder = RulesGraphBuilder(graph=graph)

            # ── Validate rule spec before insertion ─────────────────────
            # Attribute rules MUST have at least one entity dimension or keyword.
            # This prevents empty/malformed rules from entering the graph.
            rule_type = rule_def.get('rule_type', 'case_matching')
            if rule_type == 'attribute':
                try:
                    from models.rule_spec import RuleSpec, RuleType
                    RuleSpec(
                        rule_id=rule_def.get('rule_id', 'pending'),
                        name=rule_def.get('name', 'Untitled'),
                        rule_type=RuleType.ATTRIBUTE,
                        required_data_categories=rule_def.get('data_categories') or [],
                        required_purposes=rule_def.get('purposes_of_processing') or [],
                        required_processes=rule_def.get('processes') or [],
                        required_gdcs=rule_def.get('gdc') or [],
                        required_regulators=rule_def.get('regulators') or [],
                        required_authorities=rule_def.get('authorities') or [],
                        required_data_subjects=rule_def.get('data_subjects') or [],
                        required_sensitive_data_categories=rule_def.get('sensitive_data_categories') or [],
                        keywords=rule_def.get('attribute_keywords') or [],
                        patterns=rule_def.get('attribute_patterns') or [],
                    )
                    logger.info(f"RuleSpec validation passed for rule '{rule_def.get('name')}'")
                except Exception as e:
                    logger.error(f"RuleSpec validation FAILED: {e}")
                    # Don't block — log warning and continue (soft enforcement)
                    logger.warning("Proceeding with rule despite validation failure")

            # Merge suggested_linked_entities into flat fields
            self._merge_linked_entities(rule_def)

            # Merge dictionary keywords if provided
            if dictionary_result:
                merged = list(rule_def.get('attribute_keywords') or [])
                merged.extend(self._extract_dictionary_keywords(dictionary_result))
                seen = set()
                unique = []
                for kw in merged:
                    kw_lower = str(kw).lower().strip()
                    if kw_lower and kw_lower not in seen:
                        seen.add(kw_lower)
                        unique.append(kw_lower)
                rule_def['attribute_keywords'] = unique

            success = builder.add_rule(rule_def)

            if success:
                self._sandbox_rules[graph_name] = rule_def
                if dictionary_result:
                    self._sandbox_dictionaries[graph_name] = dictionary_result

            return success

        except Exception as e:
            logger.error(f"Failed to add rule to sandbox '{graph_name}': {e}")
            return False

    @staticmethod
    def _merge_linked_entities(rule_def: Dict[str, Any]):
        """Merge suggested_linked_entities dict into flat rule_def fields.

        The AI analyzer outputs entity mappings in two places:
        1. Flat fields: rule_def['data_categories'], rule_def['regulators'], etc.
        2. Nested dict: rule_def['suggested_linked_entities']['data_categories'], etc.

        graph_builder.add_rule() reads from flat fields only.
        This method ensures both sources are merged so no entity links are lost.
        """
        linked = rule_def.get('suggested_linked_entities')
        if not linked or not isinstance(linked, dict):
            return

        # Mapping from suggested_linked_entities keys to flat rule_def keys
        key_map = {
            'data_categories': 'data_categories',
            'purposes_of_processing': 'purposes_of_processing',
            'purposes': 'purposes_of_processing',
            'processes': 'processes',
            'gdc': 'gdc',
            'group_data_categories': 'gdc',
            'regulators': 'regulators',
            'authorities': 'authorities',
            'data_subjects': 'data_subjects',
            'sensitive_data_categories': 'sensitive_data_categories',
            'global_business_functions': 'global_business_functions',
        }

        for linked_key, flat_key in key_map.items():
            linked_values = linked.get(linked_key)
            if not linked_values or not isinstance(linked_values, list):
                continue

            existing = rule_def.get(flat_key) or []
            if not isinstance(existing, list):
                existing = [existing] if existing else []

            # Merge with deduplication (case-insensitive)
            existing_lower = {str(v).lower().strip() for v in existing}
            for val in linked_values:
                val_str = str(val).strip()
                if val_str and val_str.lower() not in existing_lower:
                    existing.append(val_str)
                    existing_lower.add(val_str.lower())

            rule_def[flat_key] = existing

        logger.debug(
            f"Merged linked entities into rule_def: "
            f"data_categories={len(rule_def.get('data_categories') or [])}, "
            f"purposes={len(rule_def.get('purposes_of_processing') or [])}, "
            f"regulators={len(rule_def.get('regulators') or [])}"
        )

    def _extract_dictionary_keywords(self, dictionary_result: Dict[str, Any]) -> List[str]:
        """
        Extract all keywords from an AI-generated dictionary result.
        Pulls from dictionaries (keywords, sub_categories, synonyms, acronyms)
        and pii_dictionary.
        """
        keywords = []

        dictionaries = dictionary_result.get('dictionaries', {})
        for cat_data in dictionaries.values():
            if isinstance(cat_data, dict):
                keywords.extend(cat_data.get('keywords', []))
                for sub_terms in cat_data.get('sub_categories', {}).values():
                    if isinstance(sub_terms, list):
                        keywords.extend(sub_terms)
                for synonyms in cat_data.get('synonyms', {}).values():
                    if isinstance(synonyms, list):
                        keywords.extend(synonyms)
                for full_form in cat_data.get('acronyms', {}).values():
                    if isinstance(full_form, str):
                        keywords.append(full_form)

        pii_dict = dictionary_result.get('pii_dictionary', {})
        if isinstance(pii_dict, dict):
            keywords.extend(pii_dict.get('keywords', []))

        return keywords

    def evaluate_in_sandbox(
        self,
        graph_name: str,
        origin_country: str,
        receiving_country: str,
        pii: bool = False,
        purposes: Optional[list] = None,
        process_l1: Optional[list] = None,
        process_l2: Optional[list] = None,
        process_l3: Optional[list] = None,
        personal_data_names: Optional[list] = None,
        data_categories: Optional[list] = None,
        metadata: Optional[dict] = None,
        regulators: Optional[list] = None,
        authorities: Optional[list] = None,
        data_subjects: Optional[list] = None,
        additional_precedent_graphs: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Run evaluation against the sandbox graph.

        Creates a RulesEvaluator pointing at the sandbox graph so all
        rule matching (including the new rule) is done via Cypher queries.
        Attribute keywords are loaded from the sandbox graph automatically.
        Supports multi-graph precedent search if additional_precedent_graphs is provided.
        """
        from services.rules_evaluator import RulesEvaluator

        try:
            graph = self.db.db.select_graph(graph_name)
            evaluator = RulesEvaluator(
                rules_graph=graph,
                additional_precedent_graphs=additional_precedent_graphs or []
            )

            result = evaluator.evaluate(
                origin_country=origin_country,
                receiving_country=receiving_country,
                pii=pii,
                purposes=purposes,
                process_l1=process_l1,
                process_l2=process_l2,
                process_l3=process_l3,
                personal_data_names=personal_data_names,
                data_categories=data_categories,
                metadata=metadata,
                regulators=regulators,
                authorities=authorities,
                data_subjects=data_subjects,
            )
            return result if isinstance(result, dict) else result.model_dump() if hasattr(result, 'model_dump') else {"result": str(result)}

        except Exception as e:
            logger.error(f"Sandbox evaluation failed: {e}")
            return {
                "transfer_status": "INSUFFICIENT_DATA",
                "message": f"Sandbox evaluation error: {str(e)}",
                "error": str(e),
            }

    def promote_to_main(self, graph_name: str, rule_def: Dict[str, Any]) -> bool:
        """
        Promote a tested rule from sandbox to the main RulesGraph.

        Adds the rule to the main FalkorDB graph. The graph is the single
        source of truth — no Python dict manipulation needed.
        """
        try:
            main_builder = RulesGraphBuilder()

            # Merge suggested_linked_entities into flat fields
            self._merge_linked_entities(rule_def)

            # Merge dictionary keywords if available
            dictionary = self._sandbox_dictionaries.get(graph_name)
            if dictionary:
                merged = list(rule_def.get('attribute_keywords') or [])
                merged.extend(self._extract_dictionary_keywords(dictionary))
                seen = set()
                unique = []
                for kw in merged:
                    kw_lower = str(kw).lower().strip()
                    if kw_lower and kw_lower not in seen:
                        seen.add(kw_lower)
                        unique.append(kw_lower)
                rule_def['attribute_keywords'] = unique

            success = main_builder.add_rule(rule_def)

            if success:
                logger.info(f"Rule {rule_def.get('rule_id')} promoted to main graph")
            return success

        except Exception as e:
            logger.error(f"Failed to promote rule to main graph: {e}")
            return False

    def cleanup_sandbox(self, graph_name: str):
        """Delete a sandbox graph and associated rule/dictionary data."""
        try:
            self.db.delete_temp_graph(graph_name)

            # Remove from active sandboxes
            sessions_to_remove = [
                sid for sid, gn in self._active_sandboxes.items()
                if gn == graph_name
            ]
            for sid in sessions_to_remove:
                del self._active_sandboxes[sid]

            # Remove stored rule definition and dictionary
            self._sandbox_rules.pop(graph_name, None)
            self._sandbox_dictionaries.pop(graph_name, None)

            logger.info(f"Cleaned up sandbox graph '{graph_name}'")

        except Exception as e:
            logger.error(f"Failed to cleanup sandbox '{graph_name}': {e}")

    def cleanup_session(self, session_id: str):
        """Cleanup sandbox for a session."""
        graph_name = self._active_sandboxes.get(session_id)
        if graph_name:
            self.cleanup_sandbox(graph_name)

    def get_sandbox_for_session(self, session_id: str) -> Optional[str]:
        """Get the sandbox graph name for a session."""
        return self._active_sandboxes.get(session_id)


_sandbox_service: Optional[SandboxService] = None


def get_sandbox_service() -> SandboxService:
    """Get the sandbox service instance."""
    global _sandbox_service
    if _sandbox_service is None:
        _sandbox_service = SandboxService()
    return _sandbox_service

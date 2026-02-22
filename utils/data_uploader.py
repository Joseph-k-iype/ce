"""
Data Uploader
=============
Uploads sample data to the DataTransferGraph.
Supports batch operations and deduplication.
"""

import json
import logging
from typing import Dict, Any, List, Set, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.database import get_db_service
from config.settings import settings

logger = logging.getLogger(__name__)


class DataUploader:
    """
    Uploads case data to the DataTransferGraph.

    Features:
    - Batch processing for large datasets
    - Deduplication of nodes
    - Progress tracking
    - Error handling
    """

    def __init__(self, batch_size: int = 500):
        self.db = get_db_service()
        self.graph = self.db.get_data_graph()
        self.batch_size = batch_size
        self._node_cache: Dict[str, Set[str]] = {
            'Country': set(),
            'Jurisdiction': set(),
            'Purpose': set(),
            'ProcessL1': set(),
            'ProcessL2': set(),
            'ProcessL3': set(),
            'PersonalData': set(),
            'PersonalDataCategory': set(),
        }

    def upload_from_file(self, file_path: str, clear_existing: bool = False):
        """
        Upload data from a JSON file.

        Args:
            file_path: Path to JSON file containing case data
            clear_existing: Whether to clear existing data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        logger.info(f"Loading data from {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cases = data if isinstance(data, list) else data.get('cases', [])
        logger.info(f"Found {len(cases)} cases to upload")

        self.upload_cases(cases, clear_existing)

    def upload_cases(self, cases: List[Dict[str, Any]], clear_existing: bool = False):
        """
        Upload case data.

        Args:
            cases: List of case dictionaries
            clear_existing: Whether to clear existing data
        """
        if clear_existing:
            self._clear_graph()

        # Create indexes first
        self._create_indexes()

        # Process in batches
        total = len(cases)
        processed = 0
        errors = 0

        for i in range(0, total, self.batch_size):
            batch = cases[i:i + self.batch_size]
            batch_errors = self._process_batch(batch)
            errors += batch_errors
            processed += len(batch)

            progress = (processed / total) * 100
            logger.info(f"Progress: {processed}/{total} ({progress:.1f}%) - Errors: {errors}")

        logger.info(f"Upload complete: {processed} cases, {errors} errors")
        self._print_stats()

    def _clear_graph(self):
        """Clear existing data"""
        logger.info("Clearing existing data...")
        try:
            self.graph.query("MATCH (n) DETACH DELETE n")
        except Exception as e:
            logger.warning(f"Error clearing graph: {e}")

    def _create_indexes(self):
        """Create indexes for efficient operations"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.case_ref_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.case_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.case_status)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.pia_status)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.tia_status)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.hrpr_status)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Country) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Jurisdiction) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Purpose) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ProcessL1) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ProcessL2) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ProcessL3) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:PersonalData) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:PersonalDataCategory) ON (n.name)",
        ]
        for index in indexes:
            try:
                self.graph.query(index)
            except Exception as e:
                logger.debug(f"Index note: {e}")

    def _process_batch(self, cases: List[Dict[str, Any]]) -> int:
        """Process a batch of cases, return error count"""
        errors = 0

        for case in cases:
            try:
                self._create_case(case)
            except Exception as e:
                logger.error(f"Error creating case {case.get('case_ref_id', 'unknown')}: {e}")
                errors += 1

        return errors

    def _create_case(self, case: Dict[str, Any]):
        """Create a single case with all relationships"""
        case_ref_id = case.get('case_ref_id', '')

        # Create Case node
        self.graph.query("""
        CREATE (c:Case {
            case_id: $case_id,
            case_ref_id: $case_ref_id,
            eim_id: $eim_id,
            app_id: $app_id,
            case_status: $case_status,
            pia_status: $pia_status,
            tia_status: $tia_status,
            hrpr_status: $hrpr_status,
            pii: $pii
        })
        """, {
            "case_id": case.get('case_id', case_ref_id),
            "case_ref_id": case_ref_id,
            "eim_id": case.get('eim_id', ''),
            "app_id": case.get('app_id', ''),
            "case_status": case.get('case_status', ''),
            "pia_status": case.get('pia_status', ''),
            "tia_status": case.get('tia_status', ''),
            "hrpr_status": case.get('hrpr_status', ''),
            "pii": case.get('pii', False),
        })

        # Create and link Country (origin)
        origin_country = case.get('origin_country') or case.get('country')
        if origin_country:
            self._create_and_link_node(
                'Country', origin_country, case_ref_id, 'ORIGINATES_FROM'
            )

        # Create and link Jurisdiction (receiving)
        receiving = case.get('receiving_country') or case.get('jurisdiction')
        if receiving:
            self._create_and_link_node(
                'Jurisdiction', receiving, case_ref_id, 'TRANSFERS_TO'
            )

        # Create and link Purposes
        purposes = self._parse_list(case.get('purpose') or case.get('purposes'))
        for purpose in purposes:
            self._create_and_link_node(
                'Purpose', purpose, case_ref_id, 'HAS_PURPOSE'
            )

        # Create and link Processes
        for level, key, rel in [
            ('ProcessL1', 'process_l1', 'HAS_PROCESS_L1'),
            ('ProcessL2', 'process_l2', 'HAS_PROCESS_L2'),
            ('ProcessL3', 'process_l3', 'HAS_PROCESS_L3'),
        ]:
            processes = self._parse_list(case.get(key) or case.get(key.replace('_', '')))
            for process in processes:
                self._create_and_link_node(
                    level, process, case_ref_id, rel
                )

        # Create and link Personal Data
        personal_data = self._parse_list(case.get('personal_data_names') or case.get('personal_data'))
        for pd in personal_data:
            self._create_and_link_node(
                'PersonalData', pd, case_ref_id, 'HAS_PERSONAL_DATA'
            )

        # Create and link Personal Data Categories
        categories = self._parse_list(case.get('personal_data_category') or case.get('data_category'))
        for cat in categories:
            self._create_and_link_node(
                'PersonalDataCategory', cat, case_ref_id, 'HAS_PERSONAL_DATA_CATEGORY'
            )

    def _create_and_link_node(self, label: str, name: str, case_ref_id: str, relationship: str):
        """Create a node if not exists and link to case"""
        if not name or not name.strip():
            return

        name = name.strip()

        # Check cache to avoid duplicate MERGE operations
        if name not in self._node_cache[label]:
            self.graph.query(
                f"MERGE (n:{label} {{name: $name}})",
                {"name": name}
            )
            self._node_cache[label].add(name)

        # Create relationship
        self.graph.query(f"""
        MATCH (c:Case {{case_ref_id: $case_ref_id}})
        MATCH (n:{label} {{name: $name}})
        CREATE (c)-[:{relationship}]->(n)
        """, {"case_ref_id": case_ref_id, "name": name})

    def _parse_list(self, value: Any) -> List[str]:
        """Parse a value that might be a list, pipe-separated string, or single value"""
        if value is None:
            return []

        if isinstance(value, list):
            return [str(v).strip() for v in value if v]

        if isinstance(value, str):
            # Handle pipe-separated values
            if '|' in value:
                return [v.strip() for v in value.split('|') if v.strip()]
            # Handle comma-separated values
            if ',' in value:
                return [v.strip() for v in value.split(',') if v.strip()]
            return [value.strip()] if value.strip() else []

        return [str(value).strip()] if value else []

    def _print_stats(self):
        """Print upload statistics"""
        stats = self.db.get_graph_stats(settings.database.data_graph_name)
        logger.info(f"DataTransferGraph stats: {stats['node_count']} nodes, {stats['edge_count']} edges")

        # Print node counts by type
        for label in self._node_cache.keys():
            count = len(self._node_cache[label])
            logger.info(f"  {label}: {count} unique nodes")


def upload_data(file_path: str, clear_existing: bool = False, batch_size: int = 500):
    """Upload data from file (convenience function)"""
    uploader = DataUploader(batch_size=batch_size)
    uploader.upload_from_file(file_path, clear_existing)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Upload data to DataTransferGraph")
    parser.add_argument("file", help="Path to JSON data file")
    parser.add_argument("--clear", action="store_true", help="Clear existing data")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size")

    args = parser.parse_args()
    upload_data(args.file, args.clear, args.batch_size)

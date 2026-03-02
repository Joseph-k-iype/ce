#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FalkorDB Data Upload - OPTIMIZED for Large Scale
Load JSON data into DataTransferGraph with batch operations and deduplication

Optimized for 35K+ nodes and 10M+ edges with:
- Batch MERGE operations for efficiency
- Deduplication during load
- Progress tracking
- Memory-efficient processing

Usage:
    python falkor_upload_json.py [json_file] [--clear] [--batch-size N]

Arguments:
    json_file: Path to JSON file (default: sample_data.json)
    --clear: Clear existing graph before loading (optional)
    --batch-size N: Number of cases per batch (default: 500)

JSON Format:
[
    {
        "caseRefId": "CASE_12345",
        "caseStatus": "Completed",
        "appId": "APP_67890",
        "originatingCountry": "United States",
        "receivingCountry": "Germany|France|United Kingdom",
        "tiaStatus": "Completed",
        "piaStatus": "N/A",
        "hrprStatus": "WITHDRAWN",
        "purposeOfProcessing": "Office Support|Customer Service",
        "processess": "Channels - Mobile - |Channels - Mail/eMail - ",
        "personalDataCategory": "PII|Financial Data"
    }
]
"""

import json
import sys
from pathlib import Path
from falkordb import FalkorDB
import logging
from collections import defaultdict
import time

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def parse_pipe_separated(value: str) -> list:
    """
    Parse pipe-separated OR comma-separated string into list of unique values
    with deduplication
    """
    if not value:
        return []

    # Replace pipes with commas for unified splitting
    normalized = value.replace('|', ',')

    # Split, strip, and filter empty
    items = [item.strip() for item in normalized.split(',') if item.strip()]

    # Deduplicate while preserving order
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)

    return unique_items


def parse_process_hierarchy(process_string: str) -> list:
    """
    Parse process hierarchy string into (L1, L2, L3) tuples
    with deduplication
    """
    if not process_string:
        return []

    hierarchies = []
    seen = set()

    # Split by pipe to get individual process paths
    processes = parse_pipe_separated(process_string)

    for process in processes:
        # Split by dash to get hierarchy levels
        parts = [p.strip() for p in process.split('-')]

        # Extract L1, L2, L3 (pad with None if not enough parts)
        l1 = parts[0] if len(parts) > 0 and parts[0] else None
        l2 = parts[1] if len(parts) > 1 and parts[1] else None
        l3 = parts[2] if len(parts) > 2 and parts[2] else None

        # Only add if at least L1 exists and not duplicate
        if l1:
            key = (l1, l2, l3)
            if key not in seen:
                seen.add(key)
                hierarchies.append((l1, l2, l3))

    return hierarchies


def create_optimized_indexes(graph):
    """Create comprehensive indexes for performance on large graphs"""
    logger.info("Creating optimized indexes...")

    indexes = [
        # Primary indexes for lookups
        "CREATE INDEX FOR (c:Case) ON (c.case_ref_id)",
        "CREATE INDEX FOR (c:Case) ON (c.case_status)",
        "CREATE INDEX FOR (ct:Country) ON (ct.name)",
        "CREATE INDEX FOR (j:Jurisdiction) ON (j.name)",
        "CREATE INDEX FOR (p:Purpose) ON (p.name)",
        "CREATE INDEX FOR (p1:ProcessL1) ON (p1.name)",
        "CREATE INDEX FOR (p2:ProcessL2) ON (p2.name)",
        "CREATE INDEX FOR (p3:ProcessL3) ON (p3.name)",
        "CREATE INDEX FOR (pd:PersonalData) ON (pd.name)",
        "CREATE INDEX FOR (pdc:PersonalDataCategory) ON (pdc.name)",
        # Composite indexes for common queries
        "CREATE INDEX FOR (c:Case) ON (c.pia_status)",
        "CREATE INDEX FOR (c:Case) ON (c.tia_status)",
        "CREATE INDEX FOR (c:Case) ON (c.hrpr_status)",
    ]

    created_count = 0
    for idx_query in indexes:
        try:
            graph.query(idx_query)
            created_count += 1
        except Exception as e:
            if 'already indexed' not in str(e).lower() and 'equivalent index' not in str(e).lower():
                logger.warning(f"Index warning: {e}")

    logger.info(f"   Indexes configured: {created_count}/{len(indexes)}")


def collect_unique_entities(cases):
    """
    Pre-process all cases to collect unique entities for batch creation
    """
    logger.info("Collecting unique entities for deduplication...")

    countries = set()
    jurisdictions = set()
    purposes = set()
    process_l1 = set()
    process_l2 = set()
    process_l3 = set()
    personal_data_categories = set()
    personal_data = set()

    for case in cases:
        # Origin countries
        origin_str = case.get('originatingCountry', case.get('origin_country', ''))
        if isinstance(origin_str, str):
            for c in parse_pipe_separated(origin_str):
                countries.add(c)
        elif isinstance(origin_str, list):
            countries.update(origin_str)

        # Receiving countries (as jurisdictions)
        receiving_str = case.get('receivingCountry', case.get('receiving_countries', ''))
        if isinstance(receiving_str, str):
            for j in parse_pipe_separated(receiving_str):
                jurisdictions.add(j)
        elif isinstance(receiving_str, list):
            jurisdictions.update(receiving_str)

        # Purposes
        purpose_str = case.get('purposeOfProcessing', case.get('purposes', ''))
        if isinstance(purpose_str, str):
            for p in parse_pipe_separated(purpose_str):
                purposes.add(p)
        elif isinstance(purpose_str, list):
            purposes.update(purpose_str)

        # Process hierarchies
        process_str = case.get('processess', case.get('processes', ''))
        if isinstance(process_str, str):
            for l1, l2, l3 in parse_process_hierarchy(process_str):
                if l1:
                    process_l1.add(l1)
                if l2:
                    process_l2.add(l2)
                if l3:
                    process_l3.add(l3)

        # Personal data categories
        pdc_str = case.get('personalDataCategory', case.get('personal_data_categories', ''))
        if isinstance(pdc_str, str):
            for pdc in parse_pipe_separated(pdc_str):
                personal_data_categories.add(pdc)
        elif isinstance(pdc_str, list):
            personal_data_categories.update(pdc_str)

        # Personal data
        pd_str = case.get('personalData', case.get('personal_data', ''))
        if isinstance(pd_str, str):
            for pd in parse_pipe_separated(pd_str):
                personal_data.add(pd)
        elif isinstance(pd_str, list):
            personal_data.update(pd_str)

    logger.info(f"   Countries: {len(countries)}, Jurisdictions: {len(jurisdictions)}")
    logger.info(f"   Purposes: {len(purposes)}")
    logger.info(f"   Process L1/L2/L3: {len(process_l1)}/{len(process_l2)}/{len(process_l3)}")
    logger.info(f"   Personal Data Categories: {len(personal_data_categories)}")

    return {
        'countries': countries,
        'jurisdictions': jurisdictions,
        'purposes': purposes,
        'process_l1': process_l1,
        'process_l2': process_l2,
        'process_l3': process_l3,
        'personal_data_categories': personal_data_categories,
        'personal_data': personal_data
    }


def create_reference_nodes(graph, entities):
    """Create all reference nodes in batch (not cases)"""
    logger.info("Creating reference nodes in batch...")

    # Create countries
    for country in entities['countries']:
        try:
            graph.query("MERGE (c:Country {name: $name})", params={'name': country})
        except Exception as e:
            logger.warning(f"Error creating country {country}: {e}")

    # Create jurisdictions
    for jurisdiction in entities['jurisdictions']:
        try:
            graph.query("MERGE (j:Jurisdiction {name: $name})", params={'name': jurisdiction})
        except Exception as e:
            logger.warning(f"Error creating jurisdiction {jurisdiction}: {e}")

    # Create purposes
    for purpose in entities['purposes']:
        try:
            graph.query("MERGE (p:Purpose {name: $name})", params={'name': purpose})
        except Exception as e:
            logger.warning(f"Error creating purpose {purpose}: {e}")

    # Create process levels
    for p1 in entities['process_l1']:
        try:
            graph.query("MERGE (p:ProcessL1 {name: $name})", params={'name': p1})
        except Exception as e:
            logger.warning(f"Error creating ProcessL1 {p1}: {e}")

    for p2 in entities['process_l2']:
        try:
            graph.query("MERGE (p:ProcessL2 {name: $name})", params={'name': p2})
        except Exception as e:
            logger.warning(f"Error creating ProcessL2 {p2}: {e}")

    for p3 in entities['process_l3']:
        try:
            graph.query("MERGE (p:ProcessL3 {name: $name})", params={'name': p3})
        except Exception as e:
            logger.warning(f"Error creating ProcessL3 {p3}: {e}")

    # Create personal data categories
    for pdc in entities['personal_data_categories']:
        try:
            graph.query("MERGE (pdc:PersonalDataCategory {name: $name})", params={'name': pdc})
        except Exception as e:
            logger.warning(f"Error creating PersonalDataCategory {pdc}: {e}")

    # Create personal data
    for pd in entities['personal_data']:
        try:
            graph.query("MERGE (pd:PersonalData {name: $name})", params={'name': pd})
        except Exception as e:
            logger.warning(f"Error creating PersonalData {pd}: {e}")

    total_nodes = (len(entities['countries']) + len(entities['jurisdictions']) +
                   len(entities['purposes']) + len(entities['process_l1']) +
                   len(entities['process_l2']) + len(entities['process_l3']) +
                   len(entities['personal_data_categories']) + len(entities['personal_data']))

    logger.info(f"   Created {total_nodes} reference nodes")


def load_case_batch(graph, cases, batch_start_num, total_cases):
    """Load a batch of cases with relationships"""
    success_count = 0
    error_count = 0

    for i, case in enumerate(cases):
        case_num = batch_start_num + i
        case_ref_id = case.get('caseRefId', case.get('case_ref_id', f'CASE-{case_num:06d}'))

        try:
            # Create Case node
            case_query = """
            CREATE (c:Case {
                case_ref_id: $case_ref_id,
                app_id: $app_id,
                case_status: $case_status,
                pia_status: $pia_status,
                tia_status: $tia_status,
                hrpr_status: $hrpr_status
            })
            """

            graph.query(case_query, params={
                'case_ref_id': case_ref_id,
                'app_id': case.get('appId', case.get('app_id', '')),
                'case_status': case.get('caseStatus', case.get('case_status', 'Active')),
                'pia_status': case.get('piaStatus', case.get('pia_status', 'N/A')),
                'tia_status': case.get('tiaStatus', case.get('tia_status', 'N/A')),
                'hrpr_status': case.get('hrprStatus', case.get('hrpr_status', 'N/A'))
            })

            # Create relationships - use optimized single query per relationship type

            # Origin country relationships
            origin_str = case.get('originatingCountry', case.get('origin_country', ''))
            if isinstance(origin_str, str):
                origin_countries = parse_pipe_separated(origin_str)
            elif isinstance(origin_str, list):
                origin_countries = origin_str
            else:
                origin_countries = []

            for origin in origin_countries:
                graph.query("""
                    MATCH (c:Case {case_ref_id: $case_ref_id})
                    MATCH (origin:Country {name: $origin_country})
                    MERGE (c)-[:ORIGINATES_FROM]->(origin)
                """, params={'case_ref_id': case_ref_id, 'origin_country': origin.strip()})

            # Receiving jurisdiction relationships
            receiving_str = case.get('receivingCountry', case.get('receiving_countries', ''))
            if isinstance(receiving_str, str):
                receiving_countries = parse_pipe_separated(receiving_str)
            elif isinstance(receiving_str, list):
                receiving_countries = receiving_str
            else:
                receiving_countries = []

            for receiving in receiving_countries:
                graph.query("""
                    MATCH (c:Case {case_ref_id: $case_ref_id})
                    MATCH (j:Jurisdiction {name: $receiving})
                    MERGE (c)-[:TRANSFERS_TO]->(j)
                """, params={'case_ref_id': case_ref_id, 'receiving': receiving.strip()})

            # Purpose relationships
            purpose_str = case.get('purposeOfProcessing', case.get('purposes', ''))
            if isinstance(purpose_str, str):
                purposes = parse_pipe_separated(purpose_str)
            elif isinstance(purpose_str, list):
                purposes = purpose_str
            else:
                purposes = []

            for purpose in purposes:
                graph.query("""
                    MATCH (c:Case {case_ref_id: $case_ref_id})
                    MATCH (p:Purpose {name: $purpose})
                    MERGE (c)-[:HAS_PURPOSE]->(p)
                """, params={'case_ref_id': case_ref_id, 'purpose': purpose.strip()})

            # Process hierarchy relationships
            process_str = case.get('processess', case.get('processes', ''))
            if isinstance(process_str, str):
                process_hierarchies = parse_process_hierarchy(process_str)
            else:
                process_hierarchies = []
                l1 = case.get('process_l1')
                l2 = case.get('process_l2')
                l3 = case.get('process_l3')
                if l1:
                    process_hierarchies.append((l1, l2, l3))

            for l1, l2, l3 in process_hierarchies:
                if l1:
                    graph.query("""
                        MATCH (c:Case {case_ref_id: $case_ref_id})
                        MATCH (p:ProcessL1 {name: $process_l1})
                        MERGE (c)-[:HAS_PROCESS_L1]->(p)
                    """, params={'case_ref_id': case_ref_id, 'process_l1': l1.strip()})

                if l2:
                    graph.query("""
                        MATCH (c:Case {case_ref_id: $case_ref_id})
                        MATCH (p:ProcessL2 {name: $process_l2})
                        MERGE (c)-[:HAS_PROCESS_L2]->(p)
                    """, params={'case_ref_id': case_ref_id, 'process_l2': l2.strip()})

                if l3:
                    graph.query("""
                        MATCH (c:Case {case_ref_id: $case_ref_id})
                        MATCH (p:ProcessL3 {name: $process_l3})
                        MERGE (c)-[:HAS_PROCESS_L3]->(p)
                    """, params={'case_ref_id': case_ref_id, 'process_l3': l3.strip()})

            # Personal data category relationships
            pdc_str = case.get('personalDataCategory', case.get('personal_data_categories', ''))
            if isinstance(pdc_str, str):
                pdc_list = parse_pipe_separated(pdc_str)
            elif isinstance(pdc_str, list):
                pdc_list = pdc_str
            else:
                pdc_list = []

            for pdc in pdc_list:
                graph.query("""
                    MATCH (c:Case {case_ref_id: $case_ref_id})
                    MATCH (pdc:PersonalDataCategory {name: $pdc_name})
                    MERGE (c)-[:HAS_PERSONAL_DATA_CATEGORY]->(pdc)
                """, params={'case_ref_id': case_ref_id, 'pdc_name': pdc.strip()})

            # Personal data relationships
            pd_str = case.get('personalData', case.get('personal_data', ''))
            if isinstance(pd_str, str):
                pd_list = parse_pipe_separated(pd_str)
            elif isinstance(pd_str, list):
                pd_list = pd_str
            else:
                pd_list = []

            for pd in pd_list:
                graph.query("""
                    MATCH (c:Case {case_ref_id: $case_ref_id})
                    MATCH (pd:PersonalData {name: $pd_name})
                    MERGE (c)-[:HAS_PERSONAL_DATA]->(pd)
                """, params={'case_ref_id': case_ref_id, 'pd_name': pd.strip()})

            success_count += 1

        except Exception as e:
            error_count += 1
            logger.error(f"   Error loading {case_ref_id}: {e}")

    return success_count, error_count


def load_json_to_graph(json_file: str, clear_graph: bool = False, batch_size: int = 500):
    """
    Load case data from JSON file into DataTransferGraph with optimizations

    Args:
        json_file: Path to JSON file
        clear_graph: If True, clear existing graph before loading
        batch_size: Number of cases to process per batch
    """
    start_time = time.time()

    # Validate file exists
    json_path = Path(json_file)
    if not json_path.exists():
        logger.error(f"File not found: {json_file}")
        return False

    # Load JSON with UTF-8 encoding
    try:
        logger.info(f"Loading JSON file: {json_file}")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return False

    # Handle both array format and object with 'cases' key
    if isinstance(data, list):
        cases = data
    elif isinstance(data, dict) and 'cases' in data:
        cases = data['cases']
    else:
        logger.error("JSON must be an array or have 'cases' array at root level")
        return False

    logger.info(f"Loaded {len(cases):,} cases from {json_file}")

    # Connect to FalkorDB
    try:
        db = FalkorDB(host='localhost', port=6379)
        graph = db.select_graph('DataTransferGraph')
    except Exception as e:
        logger.error(f"Cannot connect to FalkorDB: {e}")
        logger.info("Make sure FalkorDB is running: docker run -p 6379:6379 falkordb/falkordb:latest")
        return False

    # Clear graph if requested
    if clear_graph:
        logger.info("Clearing existing DataTransferGraph...")
        try:
            graph.query("MATCH (n) DETACH DELETE n")
            logger.info("   Graph cleared")
        except Exception as e:
            logger.warning(f"Error clearing graph: {e}")

    # Create optimized indexes
    create_optimized_indexes(graph)

    # Collect and deduplicate entities
    entities = collect_unique_entities(cases)

    # Create reference nodes first (batch)
    create_reference_nodes(graph, entities)

    # Load cases in batches
    logger.info(f"Loading cases in batches of {batch_size}...")

    total_success = 0
    total_errors = 0
    total_batches = (len(cases) + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, len(cases))
        batch_cases = cases[batch_start:batch_end]

        logger.info(f"   Batch {batch_num + 1}/{total_batches}: cases {batch_start + 1:,} to {batch_end:,}")

        success, errors = load_case_batch(graph, batch_cases, batch_start + 1, len(cases))
        total_success += success
        total_errors += errors

        # Progress update
        progress = (batch_end / len(cases)) * 100
        elapsed = time.time() - start_time
        rate = batch_end / elapsed if elapsed > 0 else 0
        remaining = (len(cases) - batch_end) / rate if rate > 0 else 0

        logger.info(f"      Progress: {progress:.1f}% | Rate: {rate:.0f} cases/sec | ETA: {remaining:.0f}s")

    # Summary
    elapsed_time = time.time() - start_time
    logger.info("")
    logger.info("=" * 70)
    logger.info("UPLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info(f"   Success: {total_success:,}/{len(cases):,} cases")
    if total_errors > 0:
        logger.info(f"   Errors:  {total_errors:,}/{len(cases):,} cases")
    logger.info(f"   Time: {elapsed_time:.1f} seconds ({total_success/elapsed_time:.0f} cases/sec)")

    # Verify counts
    try:
        count_query = "MATCH (c:Case) RETURN count(c) as count"
        result = graph.query(count_query)
        total_cases_in_graph = result.result_set[0][0] if result.result_set else 0

        edge_query = "MATCH ()-[r]->() RETURN count(r) as count"
        edge_result = graph.query(edge_query)
        total_edges = edge_result.result_set[0][0] if edge_result.result_set else 0

        node_query = "MATCH (n) RETURN count(n) as count"
        node_result = graph.query(node_query)
        total_nodes = node_result.result_set[0][0] if node_result.result_set else 0

        logger.info("")
        logger.info("Graph Statistics:")
        logger.info(f"   Total nodes: {total_nodes:,}")
        logger.info(f"   Total edges: {total_edges:,}")
        logger.info(f"   Total cases: {total_cases_in_graph:,}")
    except Exception as e:
        logger.warning(f"Could not verify counts: {e}")

    return total_success == len(cases)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Load JSON data into DataTransferGraph (Optimized for Large Scale)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('json_file', nargs='?', default='large_sample_data.json',
                       help='Path to JSON file (default: large_sample_data.json)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing graph before loading')
    parser.add_argument('--batch-size', type=int, default=500,
                       help='Number of cases per batch (default: 500)')

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("FALKORDB JSON DATA UPLOAD - OPTIMIZED")
    logger.info("=" * 70)
    logger.info(f"File: {args.json_file}")
    logger.info(f"Clear graph: {args.clear}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("")

    success = load_json_to_graph(args.json_file, args.clear, args.batch_size)

    if success:
        logger.info("")
        logger.info("All cases loaded successfully!")
        sys.exit(0)
    else:
        logger.info("")
        logger.info("Some cases failed to load. Check errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()

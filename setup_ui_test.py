import sys
import logging
from pathlib import Path

# Provide exact path explicitly
sys.path.insert(0, "/Users/josephkiype/Desktop/development/code/deterministic policy/compliance_engine")

try:
    from services.database import get_db_service

    logging.basicConfig(level=logging.INFO)
    db = get_db_service()

    print("Setting up test rule for Nordic Council (Persistent for UI test)...")
    # 1. Create a dummy rule linked to Nordic Council
    query = """
    MERGE (r:Rule {rule_id: 'R_NORDIC_UI_TEST', name: 'UI Browser Test Rule', criticality: 'High', enabled: true, origin_match_type: 'any', receiving_match_type: 'in', rule_type: 'Transfer'})
    MERGE (g:CountryGroup {name: 'Nordic Council'})
    MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(g)
    """
    db.execute_rules_query(query)

    # 2. Add an action and precedent for this rule so it's a valid rule
    db.execute_rules_query("""
    MATCH (r:Rule {rule_id: 'R_NORDIC_UI_TEST'})
    MERGE (a:RequiredAction {name: 'Conduct UI Browser Assessment'})
    MERGE (r)-[:REQUIRES_ACTION]->(a)
    """)
    print("Rule created successfully in FalkorDB.")

except Exception as e:
    import traceback
    traceback.print_exc()

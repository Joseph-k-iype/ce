import sys
import logging
from pathlib import Path

# Provide exact path explicitly
sys.path.insert(0, "/Users/josephkiype/Desktop/development/code/deterministic policy/compliance_engine")

try:
    from services.database import get_db_service

    logging.basicConfig(level=logging.INFO)
    db = get_db_service()

    print("Cleaning up Persistent UI test rule from FalkorDB...")
    query = """
    MATCH (r:Rule {rule_id: 'R_NORDIC_UI_TEST'})
    OPTIONAL MATCH (r)-[]->(a:RequiredAction)
    DETACH DELETE r, a
    """
    db.execute_rules_query(query)
    
    # Optional: We'll leave Nordic Council and the Denmark binding as requested by the initial mapping to prove it persists for the user.
    print("Cleanup successful.")

except Exception as e:
    import traceback
    traceback.print_exc()

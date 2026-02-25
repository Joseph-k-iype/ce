from services.database import get_db_service
import sys
db = get_db_service()
try:
    res = db.execute_rules_query("""
    MATCH (r:Rule)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(oc)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rc)
    RETURN r.rule_id AS rule_id, collect(oc.name) AS origins, collect(rc.name) AS receivings
    """)
    for r in res:
        print(r)
except Exception as e:
    print("ERROR:", e)

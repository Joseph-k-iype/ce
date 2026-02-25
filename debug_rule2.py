from services.database import get_db_service
db = get_db_service()
res = db.execute_rules_query("""
MATCH (r:Rule {rule_id: 'RULE_2'})
OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(oc)
OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rc)
RETURN r.rule_id, r.enabled, r.valid_until, r.has_pii_required, r.logic_tree, collect(oc.name) as origins, collect(rc.name) as receivings
""")
for x in res: print(x)

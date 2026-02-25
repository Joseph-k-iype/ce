from services.database import get_db_service
db = get_db_service()
res = db.execute_rules_query("MATCH (r:Rule) OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(c) RETURN r.rule_id, collect(c.name)")
for x in res: print(x)

from services.database import get_db_service
db = get_db_service()
res = db.execute_rules_query("MATCH (r:Rule)-[rel:TRIGGERED_BY_ORIGIN]->(c:Country) RETURN r.rule_id, c.name LIMIT 5")
print("R-[:TRIGGERED_BY_ORIGIN]->C:", res)

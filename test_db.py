from services.database import get_db_service
db = get_db_service()
res = db.execute_rules_query("MATCH (r:Rule {rule_id: 'RULE_2'}) OPTIONAL MATCH (r)-[rel:TRIGGERED_BY_ORIGIN]->(c) RETURN type(rel), c.name")
for x in res: print(x)

from services.database import get_db_service
db = get_db_service()
res = db.execute_rules_query("MATCH (r:Rule) RETURN r.rule_id")
print([x['r.rule_id'] for x in res])

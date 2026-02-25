from services.database import get_db_service
res = get_db_service().execute_rules_query("MATCH (r:Rule {rule_id: 'RULE_2'})-[rel]->(n) RETURN type(rel), labels(n), n.name")
for x in res: print(x)

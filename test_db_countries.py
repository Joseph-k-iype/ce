from services.database import get_db_service
db = get_db_service()
print("All Country nodes:", db.execute_rules_query("MATCH (c:Country) RETURN c LIMIT 2"))
print("All relationships:", db.execute_rules_query("MATCH ()-[r:TRIGGERED_BY_ORIGIN]->() RETURN type(r) LIMIT 2"))

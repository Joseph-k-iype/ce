from services.database import get_db_service
db = get_db_service()
print("Rules:", db.execute_rules_query("MATCH (r:Rule) RETURN count(r) AS cnt"))
print("All nodes:", db.execute_rules_query("MATCH (n) RETURN count(n) AS cnt"))

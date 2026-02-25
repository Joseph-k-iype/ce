from services.database import get_db_service
db = get_db_service()
res = db.execute_rules_query("MATCH (r:Rule) RETURN r LIMIT 2")
import json
print(json.dumps(res, default=str))

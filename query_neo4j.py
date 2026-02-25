from services.database import get_db_service
import json

db = get_db_service()
res = db.execute_rules_query("MATCH (r:Rule {rule_id: 'RULE_2'}) RETURN r.has_pii_required AS pii, r.logic_tree AS lt")
print(res)

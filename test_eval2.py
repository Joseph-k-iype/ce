import sys
from pathlib import Path

# Provide exact path explicitly
sys.path.insert(0, "/Users/josephkiype/Desktop/development/code/deterministic policy/compliance_engine")

try:
    from services.database import get_db_service
    db = get_db_service()
    
    # Check if the rule is correctly linked to the group and the group to the country
    res1 = db.execute_rules_query("MATCH (r:Rule {name: 'Nordic Data Processing Rule'})-[:TRIGGERED_BY_RECEIVING]->(g:CountryGroup)<-[:BELONGS_TO]-(c:Country {name: 'Denmark'}) RETURN r.name, g.name, c.name")
    print("Direct match query:", res1)
    
except Exception as e:
    print(e)

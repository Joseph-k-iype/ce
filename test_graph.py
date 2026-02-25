import sys
import logging
logging.basicConfig(level=logging.INFO)
from services.database import get_db_service

db = get_db_service()
try:
    res = db.execute_rules_query("MATCH (c:Country)-[:BELONGS_TO]->(g:CountryGroup {name: 'Nordic Council'}) RETURN c.name as country, g.name as group")
    print("\n\nRESULTS:", res)
except Exception as e:
    print("ERROR:", e)

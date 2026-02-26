import sys
import logging
from pathlib import Path

# Provide exact path explicitly
sys.path.insert(0, "/Users/josephkiype/Desktop/development/code/deterministic policy/compliance_engine")

try:
    from services.database import get_db_service
    from services.rules_evaluator import get_rules_evaluator

    logging.basicConfig(level=logging.INFO)
    db = get_db_service()

    print("Setting up test rule for Nordic Council...")
    # 1. Create a dummy rule linked to Nordic Council
    query = """
    MERGE (r:Rule {rule_id: 'R_NORDIC_01', name: 'Nordic Data Processing Rule', rule_type: 'Transfer', criticality: 'High', enabled: true, origin_match_type: 'any', receiving_match_type: 'in'})
    MERGE (g:CountryGroup {name: 'Nordic Council'})
    MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(g)
    """
    db.execute_rules_query(query)

    # 2. Add an action and precedent for this rule so it's a valid rule
    db.execute_rules_query("""
    MATCH (r:Rule {rule_id: 'R_NORDIC_01'})
    MERGE (a:RequiredAction {name: 'Conduct Nordic Privacy Assessment'})
    MERGE (r)-[:REQUIRES_ACTION]->(a)
    """)

    # 3. Evaluate transfer from US to Denmark (Denmark is in Nordic Council)
    evaluator = get_rules_evaluator()
    
    result = evaluator.evaluate(
        origin_country="United States",
        receiving_country="Denmark",
    )

    print("\n--- EVALUATION RESULTS FOR US -> DENMARK ---")
    print(f"Transfer Status: {result.transfer_status}")
    for rule in result.triggered_rules:
        print(f"- Triggered Rule: {rule.rule_name} ({rule.rule_id})")
        
    if result.evaluation_graph:
        print(f"\nGenerated Graph: {len(result.evaluation_graph.nodes)} nodes, {len(result.evaluation_graph.edges)} edges")
    else:
        print("\nGenerated Graph: None")

except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    try:
        print("\nCleaning up test rule...")
        db.execute_rules_query("MATCH (r:Rule {rule_id: 'R_NORDIC_01'}) OPTIONAL MATCH (r)-[]->(a:RequiredAction {name: 'Conduct Nordic Privacy Assessment'}) DETACH DELETE r, a")
    except:
        pass

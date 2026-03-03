import sys
import json
import logging
logging.basicConfig(level=logging.INFO)

from services.sandbox_service import get_sandbox_service

def main():
    try:
        sandbox = get_sandbox_service()
        
        # 1. Create sandbox
        session_id = "test-session-123"
        graph_name = sandbox.create_sandbox(session_id)
        
        # 2. Add rule
        import uuid
        rule_def = {
            "rule_id": str(uuid.uuid4()),
            "origin_countries": ["United Kingdom"],
            "receiving_countries": ["United States"],
            "requires_pii": True,
            "processes": ["Payroll"],
            "description": "Test rule via selected_graphs",
            "name": "Test Rule",
            "priority": "high",
            "rule_type": "attribute", # forces content match
            "linked_processes": ["Payroll"]
        }
        success = sandbox.add_rule_to_sandbox(graph_name, rule_def, None)
        print(f"Rule added: {success}")
        
        # 3. Evaluate with selected graph 'DataTransferGraph'
        eval_result = sandbox.evaluate_in_sandbox(
            graph_name=graph_name,
            origin_country="United Kingdom",
            receiving_country="United States",
            pii=True,
            process_l1=["Payroll"],
            additional_precedent_graphs=["DataTransferGraph"]
        )
        
        print(f"Triggered Rules: {len(eval_result.get('triggered_rules', []))}")
        for r in eval_result.get('triggered_rules', []):
            print(f" - {r.get('rule_name')} (priority: {r.get('priority')})")
            
        precedent_val = eval_result.get('precedent_validation', {})
        print(f"Precedent Validation: {precedent_val.get('has_valid_precedent')}")
        print(f"Compliant Matches: {precedent_val.get('compliant_matches')} / {precedent_val.get('total_matches')}")
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == '__main__':
    main()

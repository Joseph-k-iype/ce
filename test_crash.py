import asyncio
import os
import sys
# Ensure the backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.workflows.rule_ingestion_workflow import run_rule_ingestion

def test():
    try:
        res = run_rule_ingestion(
            session_id="wiz_test123",
            origin_country="United States",
            scenario_type="attribute",
            receiving_countries=["Spain"],
            rule_text="Transfers to Spain require a comprehensive TIA and PIA",
            agentic_mode=True,
            processing_mode="autonomous"
        )
        print("Success:", res.success)
        print("Error:", res.error_message)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()

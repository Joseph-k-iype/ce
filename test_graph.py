import sys
import logging
logging.basicConfig(level=logging.INFO)

from services.multi_graph_query import MultiGraphQuery

def main():
    q = MultiGraphQuery()
    try:
        nodes = q.query("DataTransferGraph", "MATCH (n) RETURN n LIMIT 5", {})
        import json
        print(json.dumps(nodes, indent=2))
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == '__main__':
    main()

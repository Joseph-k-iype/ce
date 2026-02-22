import pandas as pd
from falkordb import FalkorDB

# Configuration
HOST = 'localhost'
PORT = 6379
GRAPH_NAME = 'RulesGraph'  # Replace with your graph name
OUTPUT_FILE = 'falkordb_schema.xlsx'

def extract_schema_to_excel():
    # 1. Connect to FalkorDB
    db = FalkorDB(host=HOST, port=PORT)
    g = db.select_graph(GRAPH_NAME)

    print(f"Connected to graph: {GRAPH_NAME}")

    # ---------------------------------------------------------
    # PART A: Extract Node Labels & Properties
    # ---------------------------------------------------------
    print("Extracting Node Schema...")
    node_query = """
    MATCH (n)
    UNWIND labels(n) AS Label
    UNWIND keys(n) AS Attribute
    RETURN Label, collect(DISTINCT Attribute) AS Properties
    ORDER BY Label
    """
    
    node_data = []
    result = g.query(node_query)
    
    # Iterate through the result set
    for row in result.result_set:
        # row[0] is Label, row[1] is the list of properties
        node_data.append({
            "Node Label": row[0],
            "Attributes": ", ".join(row[1]) # Join list into a single string
        })
        
    df_nodes = pd.DataFrame(node_data)

    # ---------------------------------------------------------
    # PART B: Extract Relationships (Source -> Rel -> Target)
    # ---------------------------------------------------------
    print("Extracting Relationship Topology...")
    rel_topo_query = """
    MATCH (a)-[r]->(b)
    UNWIND labels(a) AS SourceLabel
    UNWIND labels(b) AS TargetLabel
    RETURN 
        SourceLabel, 
        type(r) AS RelationshipType, 
        TargetLabel, 
        count(*) AS ConnectionCount
    ORDER BY SourceLabel, RelationshipType
    """
    
    rel_topo_data = []
    result = g.query(rel_topo_query)
    
    for row in result.result_set:
        rel_topo_data.append({
            "Source Node": row[0],
            "Relationship Type": row[1],
            "Target Node": row[2],
            "Count": row[3]
        })

    df_rels = pd.DataFrame(rel_topo_data)

    # ---------------------------------------------------------
    # PART C: Extract Relationship Attributes
    # ---------------------------------------------------------
    print("Extracting Relationship Attributes...")
    rel_prop_query = """
    MATCH ()-[r]->()
    UNWIND keys(r) AS Attribute
    RETURN 
        type(r) AS RelationshipType, 
        collect(DISTINCT Attribute) AS Properties
    ORDER BY RelationshipType
    """
    
    rel_prop_data = []
    result = g.query(rel_prop_query)
    
    for row in result.result_set:
        rel_prop_data.append({
            "Relationship Type": row[0],
            "Attributes": ", ".join(row[1])
        })

    df_rel_props = pd.DataFrame(rel_prop_data)

    # ---------------------------------------------------------
    # PART D: Save to Excel
    # ---------------------------------------------------------
    print(f"Writing to {OUTPUT_FILE}...")
    
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        # Sheet 1: Nodes and their attributes
        df_nodes.to_excel(writer, sheet_name='Node Attributes', index=False)
        
        # Sheet 2: The Graph Structure (Meta-Graph)
        df_rels.to_excel(writer, sheet_name='Graph Topology', index=False)
        
        # Sheet 3: Relationship Attributes
        df_rel_props.to_excel(writer, sheet_name='Rel Attributes', index=False)
        
        # Auto-adjust column widths (optional formatting)
        for sheet in writer.sheets.values():
            for column in sheet.columns:
                length = max(len(str(cell.value)) for cell in column)
                sheet.column_dimensions[column[0].column_letter].width = length + 2

    print("Done! Schema extraction complete.")

if __name__ == "__main__":
    try:
        extract_schema_to_excel()
    except Exception as e:
        print(f"Error: {e}")
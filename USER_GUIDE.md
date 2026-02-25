# User Guide: Privacy Policy Engine

Welcome to the Privacy Policy Engine, an advanced, deterministic compliance and rule evaluation platform. This guide explains how to use the web interfaces across the dashboard.

## Overview
The application enables policy administrators and legal teams to transform complex privacy laws (like GDPR or specialized internal rules) into strict technical rules. A business user or automated system can then "evaluate" a proposed data transfer or processing activity to see if it is **Permitted** or **Prohibited**, and what subsequent mandatory **Assessments** (TIA, PIA) are required.

## Key Features

### 1. The Rules Administration Dashboard
Found under the **"Dashboard"** link in the header, this view allows you to:
- **Build Complex Triggers**: Define logical IF/AND/OR relationships. E.g., "IF Origin Country IN [Germany, France] AND Data Category IN [Health Data] THEN...".
- **Dynamic Entities**: If an entity (e.g., a specific Regulator or Legal Entity) does not exist in the dropdown, you can simply type its name to create it instantly. It will automatically synchronize across the graph database.
- **Rule Configurations**: Choose whether a matched rule contributes a **Permission** (allow data flow if conditions met) or **Prohibition** (block data flow).

### 2. Bulk Excel Uploads
For massive compliance regimes (hundreds of rules mapping geographies to data actions), click **"Excel Upload"** on the dashboard.
- The Engine automatically parses the CSV/Excel sheet.
- The engine deterministically translates the spreadsheet columns into hierarchical graph clusters.
- You can preview all permutations in a detailed Review Table before "pushing" the data live into the Engine.

### 3. The Sandbox Evaluator
Found under **"Policy Evaluator"** (or in Step 5 of the Sandbox interface).
- Provide a hypothetical payload representing a data action (e.g., Transferring PII from UK to US).
- The Engine rapidly calculates all overlapping, competing, and hierarchical rules.
- Results are displayed in a clean table showing exactly which rules triggered, whether they are Permits or Prohibitions, and what residual tasks (like a Transfer Impact Assessment) remain before the activity can legally proceed.

## Best Practices
1. **Rule Consolidation**: Instead of creating 10 rules for 10 European countries, use the Logic Builder's implicit AND/OR groups to create ONE rule representing all `[EU/EEA]` conditions.
2. **Tag Attributes**: In the Logic Builder sidebar, you can define arbitrary markers on rules (e.g. `High Risk`, `Beta Software`). These tags are tracked whenever the rule fires, useful for downstream reporting.

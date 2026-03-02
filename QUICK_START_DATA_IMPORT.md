# Quick Start: Data Import Testing 🚀

## Ready-to-Use Sample Files

Three sample datasets are already loaded in the backend container at `/app/sample_data/`:

| File | Type | Records | Description |
|------|------|---------|-------------|
| `customers.csv` | CSV | 15 | Customer data with consent tracking (UK, France, Germany, Spain, etc.) |
| `data_processing_activities.json` | JSON | 10 | Data processing activities (Marketing, HR, Research, etc.) |
| `compliance_policies.db` | SQLite | 24 | Compliance policies, regulatory authorities, transfer mechanisms |

---

## 🎯 Test 1: Import Customer Data (CSV) - 2 minutes

### Step-by-Step in UI

1. **Open**: http://localhost:3001
2. **Login** as admin
3. **Click**: "Data Sources" tab in navigation
4. **Click**: "New Data Source" button

### Create CSV Source

5. **Select**: "CSV File" card
6. **Fill** form:
   ```
   Name: Customer Data
   Description: Customer consent and profile data
   File Path: /app/sample_data/customers.csv
   ```
7. **Click**: "Continue"
8. **Click**: "Test Connection"
   - ✅ **Expect**: "CSV file validated successfully - found 15 rows"
9. **Click**: "Create"

### Import to Graph

10. **Click**: "Import to Graph" button on the Customer Data card
11. **Step 1 - Preview**:
    - ✅ **Verify**: Table shows 15 rows with columns: customer_id, full_name, email, country, age, etc.
    - **Click**: "Continue"

12. **Step 2 - Configure**:
    ```
    Graph Name: CustomerGraph
    Node Label: Customer
    ID Field: customer_id (select from dropdown)
    ```
    - **Check boxes** for fields to import:
      - ☑ customer_id
      - ☑ full_name
      - ☑ email
      - ☑ country
      - ☑ consent_marketing
      - ☑ consent_analytics
    - **Click**: "Continue"

13. **Step 3 - Review**:
    - ✅ **Verify**: "Estimated Nodes: 15"
    - **Click**: "Start Import"

14. **Step 4 - Success**:
    - ✅ **Expect**: "Nodes Created: 15"
    - ✅ **Expect**: Duration < 2000ms
    - **Click**: "Done"

### Verify Import

Open terminal and run:
```bash
curl -s http://localhost:5001/graphs/list | jq '.graphs[] | select(.name == "CustomerGraph")'
```

**Expected Output**:
```json
{
  "name": "CustomerGraph",
  "graph_type": "external",
  "node_labels": ["Customer"],
  "enabled": true,
  "metadata": {
    "source_type": "csv",
    "row_count": 15
  }
}
```

### Query Customer Data

```bash
# Get all UK customers
curl -s -X POST http://localhost:5001/graphs/CustomerGraph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (c:Customer {country: \"United Kingdom\"}) RETURN c.full_name, c.email LIMIT 5"}' | jq '.'
```

**Expected**: Returns customers like "John Smith", "Lars Petersen", etc.

---

## 🎯 Test 2: Import Processing Activities (JSON) - 2 minutes

### Create JSON Source

1. **Click**: "New Data Source"
2. **Select**: "JSON File" card
3. **Fill**:
   ```
   Name: Processing Activities
   Description: Data processing activities across jurisdictions
   File Path: /app/sample_data/data_processing_activities.json
   ```
4. **Test** → **Create**

### Import to Graph

5. **Click**: "Import to Graph"
6. **Step 1**: ✅ Verify 10 rows with activity_id, purpose, requires_pia, etc.
7. **Step 2**:
   ```
   Graph Name: ProcessingGraph
   Node Label: ProcessingActivity
   ID Field: activity_id
   ```
   - Select fields: activity_id, activity_name, purpose, processing_type, requires_pia, requires_tia
8. **Import** → ✅ **Expect**: "Nodes Created: 10"

### Query Processing Activities

```bash
# Find activities requiring PIA
curl -s -X POST http://localhost:5001/graphs/ProcessingGraph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (p:ProcessingActivity) WHERE p.requires_pia = \"True\" OR p.requires_pia = true RETURN p.activity_name, p.purpose LIMIT 5"}' | jq '.'
```

**Expected**: Returns activities like "Customer Marketing Analytics", "Health Data Research", etc.

---

## 🎯 Test 3: Multi-Graph Search - 1 minute

### Search Across All Imported Graphs

```bash
# Search for any node with "United Kingdom"
curl -s -X POST http://localhost:5001/graphs/search \
  -H "Content-Type: application/json" \
  -d '{
    "node_label": "Customer",
    "filters": {"country": "United Kingdom"},
    "graph_types": ["external"],
    "limit": 10
  }' | jq '.'
```

**Expected**:
```json
{
  "status": "success",
  "node_label": "Customer",
  "graphs_searched": 1,
  "total_results": 4,
  "results": {
    "CustomerGraph": [
      {
        "customer_id": "CUST_001",
        "full_name": "John Smith",
        "country": "United Kingdom",
        "consent_marketing": "true"
      },
      ...
    ]
  }
}
```

---

## 🎯 Test 4: Use in Policy Generator - 3 minutes

### Create Rule Using Imported Data

1. Navigate to **"Policy Editor"**
2. Click **"Create New Rule"**
3. **Basic Info**:
   ```
   Name: Marketing Consent Required
   Description: Require marketing consent for UK customers
   Outcome: Permission
   Priority: high
   ```

4. **Trigger Logic** (use LogicTreeBuilder):
   - Add **OR** group
   - Add CONDITION: `OriginCountry = United Kingdom`
   - Add CONDITION: `Purpose = Marketing`

5. **Entity Mapping**:
   - Select Data Categories: Personal Data
   - Select Purposes: Marketing
   - Select Origin Countries: United Kingdom

6. **Duties**:
   - Check: ☑ Requires PII
   - Required Actions: Add "Verify marketing consent"

7. **Test** (optional):
   - Test Scenario:
     ```
     Origin Country: United Kingdom
     Data Categories: Personal Data
     Purpose: Marketing
     ```
   - ✅ **Expect**: Rule matches

8. **Save Rule**

### Verify Rule Can Query Customer Graph

The rule can now potentially query the CustomerGraph to check consent status when evaluating real scenarios.

---

## 🎯 Test 5: Dashboard Visualization (if available)

1. Navigate to **"Dashboard"**
2. If dashboard has graph selector:
   - Select **"CustomerGraph"** from dropdown
   - ✅ Verify: Visualization shows Customer nodes
   - ✅ Verify: Can explore node properties

---

## 📊 Validation Queries

### List All Imported Graphs
```bash
curl -s http://localhost:5001/graphs/list | jq '.graphs[] | select(.graph_type == "external") | {name, node_labels, row_count: .metadata.row_count}'
```

### Count Nodes in Each Graph
```bash
# CustomerGraph
curl -s -X POST http://localhost:5001/graphs/CustomerGraph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (n) RETURN count(n) as node_count"}' | jq '.'

# ProcessingGraph
curl -s -X POST http://localhost:5001/graphs/ProcessingGraph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (n) RETURN count(n) as node_count"}' | jq '.'
```

### Get Sample Node Properties
```bash
curl -s -X POST http://localhost:5001/graphs/CustomerGraph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (c:Customer) RETURN c LIMIT 1"}' | jq '.'
```

---

## 🎯 Success Criteria

After completing all tests, verify:

- [x] ✅ CustomerGraph created with 15 nodes
- [x] ✅ ProcessingGraph created with 10 nodes
- [x] ✅ Both graphs appear in `/graphs/list`
- [x] ✅ Multi-graph search returns correct results
- [x] ✅ Can create rules referencing imported data
- [x] ✅ Logic builder works with imported dimensions
- [x] ✅ Dashboard can visualize imported graphs (if implemented)

---

## 🐛 Quick Troubleshooting

### Issue: "File not found"
```bash
# Verify files exist in container
docker exec compliance-engine-backend ls -lh /app/sample_data/
```

### Issue: Import shows 0 nodes
- Check Step 1 preview shows data
- Verify ID field selected in Step 2
- Check at least one property checkbox is selected
- Look at browser console for errors

### Issue: Graph not in registry
```bash
# Check backend logs
docker logs compliance-engine-backend --tail 30 | grep -i error
```

---

## 🎉 What You Just Accomplished

1. ✅ **Imported 15 customer records** from CSV to graph
2. ✅ **Imported 10 data processing activities** from JSON to graph
3. ✅ **Created queryable knowledge graphs** accessible via API
4. ✅ **Integrated external data** with policy rules system
5. ✅ **Enabled cross-graph search** across multiple data sources

**Your imported graphs can now be used in**:
- Policy Generator (wizard graph selection)
- Policy Editor (rule creation with logic builder)
- Dashboard (visualization and analytics)
- Multi-graph queries (cross-source search)
- Precedent search (AI-powered rule generation)

---

## 🚀 Next Steps

1. **Import More Data**: Try REST API sources, larger CSV files
2. **Create Relationships**: Link customers to processing activities
3. **Advanced Queries**: Join data across multiple imported graphs
4. **Automation**: Schedule periodic imports for real-time data sync
5. **Production**: Connect to real databases (PostgreSQL, MySQL)

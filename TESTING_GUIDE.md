# Data Source Import - Complete Testing Guide

## 📁 Sample Data Files Created

Three realistic sample datasets for testing the complete data import workflow:

### 1. **customers.csv** (15 customers)
- **Purpose**: Customer data with consent tracking
- **Columns**: customer_id, full_name, email, country, age, account_type, consent_marketing, consent_analytics, data_category, created_at
- **Use Case**: Test data subject requirements, GDPR consent tracking
- **Location**: `/app/sample_data/customers.csv` (in container)

### 2. **data_processing_activities.json** (10 activities)
- **Purpose**: Data processing activities across jurisdictions
- **Fields**: activity_id, purpose, data_categories, processing_type, origin_country, receiving_countries, requires_pia, requires_tia
- **Use Case**: Test purpose/process mapping, cross-border transfers, impact assessments
- **Location**: `/app/sample_data/data_processing_activities.json` (in container)

### 3. **compliance_policies.db** (SQLite - 3 tables)
- **Purpose**: Compliance policies and regulatory authorities
- **Tables**:
  - `compliance_policies` (12 policies: GDPR, CCPA, HIPAA, LGPD, etc.)
  - `regulatory_authorities` (7 authorities: ICO, CNIL, FTC, etc.)
  - `data_transfer_mechanisms` (5 mechanisms: SCC, BCR, DPF, etc.)
- **Use Case**: Test JDBC connector, regulatory requirement mapping
- **Location**: `/app/sample_data/compliance_policies.db` (in container)

---

## 🧪 Test Workflow: CSV Import (Customers)

### Step 1: Navigate to Data Sources
1. Open browser: http://localhost:3001
2. Login as admin
3. Click **"Data Sources"** in navigation bar

### Step 2: Create CSV Data Source
1. Click **"New Data Source"**
2. Select **"CSV File"** card
3. Fill in configuration:
   - **Name**: `Customer Data CSV`
   - **Description**: `Customer consent and profile data`
   - **File Path**: `/app/sample_data/customers.csv`
4. Click **"Continue"**
5. Click **"Test Connection"**
   - ✅ Should show: "CSV file validated successfully - found 15 rows"
6. Click **"Create"**
   - ✅ Card appears in grid with green CSV icon

### Step 3: Import to Graph
1. Click **"Import to Graph"** on the "Customer Data CSV" card
2. **Preview Data** (Step 1):
   - ✅ Verify table shows 15 customer rows
   - ✅ Verify columns: customer_id, full_name, email, country, age, etc.
3. Click **"Continue"**
4. **Configure Mapping** (Step 2):
   - **Graph Name**: `CustomerDataGraph`
   - **Node Label**: `Customer`
   - **ID Field**: Select `customer_id` from dropdown
   - **Field Mapping**: Check boxes for:
     - ☑ customer_id → customer_id
     - ☑ full_name → full_name
     - ☑ email → email
     - ☑ country → country
     - ☑ consent_marketing → consent_marketing
     - ☑ consent_analytics → consent_analytics
     - ☑ data_category → data_category
   - **Clear Existing Data**: Leave unchecked
5. Click **"Continue"**
6. **Review** (Step 3):
   - ✅ Verify: Graph Name = CustomerDataGraph
   - ✅ Verify: Node Label = Customer
   - ✅ Verify: Mapped Properties = 7
   - ✅ Verify: Estimated Nodes = 15
7. Click **"Start Import"**
8. **Success** (Step 4):
   - ✅ Wait for completion (should be ~1-2 seconds)
   - ✅ Verify statistics: "Nodes Created: 15"
   - ✅ Note the duration

### Step 4: Verify Graph in Registry
```bash
curl http://localhost:5001/graphs/list | jq '.graphs[] | select(.name == "CustomerDataGraph")'
```

**Expected Output**:
```json
{
  "name": "CustomerDataGraph",
  "graph_type": "external",
  "description": "Imported from Customer Data CSV",
  "node_labels": ["Customer"],
  "relationship_types": [],
  "enabled": true,
  "metadata": {
    "source_id": "...",
    "source_type": "csv",
    "imported_at": "2026-03-01T...",
    "row_count": 15
  }
}
```

---

## 🧪 Test Workflow: JSON Import (Data Processing Activities)

### Step 1: Create JSON Data Source
1. In Data Sources page, click **"New Data Source"**
2. Select **"JSON File"** card
3. Fill in configuration:
   - **Name**: `Processing Activities JSON`
   - **Description**: `Data processing activities across jurisdictions`
   - **File Path**: `/app/sample_data/data_processing_activities.json`
4. Click **"Continue"**
5. Click **"Test Connection"**
   - ✅ Should show: "JSON file validated successfully - found 10 records"
6. Click **"Create"**

### Step 2: Import to Graph
1. Click **"Import to Graph"** on the JSON source
2. **Preview Data** (Step 1):
   - ✅ Verify 10 rows with activity_id, activity_name, purpose, etc.
3. Click **"Continue"**
4. **Configure Mapping** (Step 2):
   - **Graph Name**: `ProcessingActivitiesGraph`
   - **Node Label**: `DataProcessingActivity`
   - **ID Field**: `activity_id`
   - **Field Mapping**: Select all fields:
     - activity_id, activity_name, purpose, processing_type
     - legal_basis, origin_country, processor
     - requires_pia, requires_tia
     - (Rename as needed, e.g., `requires_pia` → `requiresPIA`)
5. Click **"Continue"** → **"Start Import"**
6. **Success**:
   - ✅ Verify: "Nodes Created: 10"

### Step 3: Verify Graph
```bash
curl http://localhost:5001/graphs/list | jq '.graphs[] | select(.name == "ProcessingActivitiesGraph")'
```

---

## 🧪 Test Workflow: SQLite Import (Compliance Policies)

### Step 1: Create JDBC Data Source (SQLite)
1. Click **"New Data Source"**
2. Select **"JDBC Database"** card
3. Fill in configuration:
   - **Name**: `Compliance Policies DB`
   - **Description**: `Regulatory requirements and authorities`
   - **Driver**: Select `PostgreSQL` (we'll use SQLite via file path workaround)

   **Note**: SQLite doesn't use host/port. For testing, we can:
   - **Option A**: Use the CSV connector for each table exported to CSV
   - **Option B**: Connect to a real PostgreSQL/MySQL database

**Let's use Option A for now** - Export SQLite tables to CSV for import:

```bash
# Export compliance_policies table
docker exec compliance-engine-backend sh -c "sqlite3 /app/sample_data/compliance_policies.db '.mode csv' '.headers on' 'SELECT * FROM compliance_policies' > /app/sample_data/compliance_policies_table.csv"

# Export regulatory_authorities table
docker exec compliance-engine-backend sh -c "sqlite3 /app/sample_data/compliance_policies.db '.mode csv' '.headers on' 'SELECT * FROM regulatory_authorities' > /app/sample_data/regulatory_authorities.csv"

# Export data_transfer_mechanisms table
docker exec compliance-engine-backend sh -c "sqlite3 /app/sample_data/compliance_policies.db '.mode csv' '.headers on' 'SELECT * FROM data_transfer_mechanisms' > /app/sample_data/data_transfer_mechanisms.csv"
```

### Step 2: Import Each Table as CSV
Repeat the CSV import workflow for each table:

1. **compliance_policies_table.csv**:
   - Graph Name: `CompliancePoliciesGraph`
   - Node Label: `CompliancePolicy`
   - ID Field: `policy_id`

2. **regulatory_authorities.csv**:
   - Graph Name: `RegulatoryAuthoritiesGraph`
   - Node Label: `RegulatoryAuthority`
   - ID Field: `authority_id`

3. **data_transfer_mechanisms.csv**:
   - Graph Name: `TransferMechanismsGraph`
   - Node Label: `TransferMechanism`
   - ID Field: `mechanism_id`

---

## 🧪 Testing Integration with Policy Components

### Test 1: Use Imported Graph in Policy Generator (Wizard)

**Goal**: Select imported graphs for precedent search during rule generation

1. Navigate to **"Policy Generator"**
2. Complete Steps 1-2 (policy text, analysis)
3. **Step 2.5: Graph Selection** (if implemented):
   - ✅ Verify imported graphs appear in list:
     - CustomerDataGraph
     - ProcessingActivitiesGraph
     - CompliancePoliciesGraph
   - ☑ Check boxes to include in precedent search
4. Continue wizard
5. **Verify**: Rule evaluation queries selected graphs

**API Test**:
```bash
# Get available graphs for wizard
curl http://localhost:5001/api/wizard/session/SESSION_ID/available-graphs

# Expected: List includes imported external graphs
```

---

### Test 2: Use Imported Graph in Multi-Graph Search

**Goal**: Query across multiple graphs including imported data

1. **Search for Customers from UK**:
```bash
curl -X POST http://localhost:5001/graphs/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "node_label": "Customer",
    "filters": {"country": "United Kingdom"},
    "graph_types": ["external"],
    "limit": 100
  }'
```

**Expected Output**:
```json
{
  "status": "success",
  "node_label": "Customer",
  "graphs_searched": 1,
  "total_results": 4,
  "results": {
    "CustomerDataGraph": [
      {"customer_id": "CUST_001", "full_name": "John Smith", "country": "United Kingdom", ...},
      {"customer_id": "CUST_011", "full_name": "Lars Petersen", "country": "Denmark", ...},
      ...
    ]
  }
}
```

2. **Search for Processing Activities Requiring PIA**:
```bash
curl -X POST http://localhost:5001/graphs/search \
  -H "Content-Type: application/json" \
  -d '{
    "node_label": "DataProcessingActivity",
    "filters": {"requires_pia": true},
    "limit": 100
  }'
```

---

### Test 3: Use Imported Data in Logic Builder

**Goal**: Reference imported graph data in rule logic trees

**Scenario**: Create a rule that triggers when processing activities require PIA

1. Navigate to **"Policy Editor"** → **"Create New Rule"**
2. **Basic Info Tab**:
   - Name: "PIA Required for High-Risk Processing"
   - Outcome: Permission
3. **Trigger Logic Tab**:
   - Use LogicTreeBuilder to create:
   ```
   OR
   ├─ CONDITION: DataCategory = "Health Data"
   ├─ CONDITION: Process = "Automated Decision Making"
   └─ CONDITION: Purpose = "Research"
   ```
4. **Entity Mapping Tab**:
   - Link to data categories, purposes, processes
5. **Test Tab**:
   - Create test scenario:
     - Data Categories: ["Health Data"]
     - Purpose: "Research"
   - ✅ Verify rule matches
   - ✅ Verify required duties include "PIA"

---

### Test 4: Cross-Graph Query in Dashboard

**Goal**: Visualize data from imported graphs in dashboard analytics

1. Navigate to **"Dashboard"**
2. If dashboard has graph visualization:
   - ✅ Verify imported graphs appear in graph selector
   - ✅ Switch to CustomerDataGraph
   - ✅ View customer nodes in visualization

**API Test**:
```bash
# Query customer graph directly
curl -X POST http://localhost:5001/graphs/CustomerDataGraph/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "cypher": "MATCH (c:Customer) RETURN c LIMIT 5",
    "params": {}
  }'
```

---

## 📊 Validation Checklist

### Data Import Validation
- [ ] CSV import creates 15 Customer nodes
- [ ] JSON import creates 10 DataProcessingActivity nodes
- [ ] All imported graphs appear in `/graphs/list`
- [ ] Graph metadata shows correct source_type, row_count
- [ ] Node properties match source data

### Integration Validation
- [ ] Imported graphs selectable in wizard graph selection
- [ ] Multi-graph search queries imported graphs
- [ ] Logic builder can reference imported data
- [ ] Dashboard can visualize imported graphs
- [ ] Query performance acceptable (<500ms for small datasets)

### UI/UX Validation
- [ ] Data source cards display correctly
- [ ] Wizards handle errors gracefully
- [ ] Import progress shows real-time feedback
- [ ] Success messages show accurate statistics
- [ ] Empty states guide user to create sources

---

## 🐛 Troubleshooting

### Issue: "File not found" error
**Solution**: Verify file path is absolute and accessible in container
```bash
docker exec compliance-engine-backend ls -lh /app/sample_data/
```

### Issue: Import shows 0 nodes created
**Check**:
- Preview shows data correctly (Step 1)
- ID field selected (Step 2)
- At least one property selected (Step 2)
- Check backend logs for errors

### Issue: Imported graph not in registry
**Solution**:
```bash
# Check backend logs
docker logs compliance-engine-backend --tail 50

# Verify graph exists in FalkorDB
docker exec compliance-engine-falkordb falkordb-cli
> GRAPH.LIST
```

---

## 🎯 Success Criteria

✅ **All 3 data sources created and tested successfully**
✅ **All 3 graphs imported with correct node counts**
✅ **Graphs visible in multi-graph registry**
✅ **Cross-graph search returns expected results**
✅ **Logic builder can reference imported data**
✅ **Wizard can select imported graphs**
✅ **No errors in browser console or backend logs**

---

## 📚 Next Steps

After successful testing:

1. **Performance Testing**:
   - Import larger datasets (1000+ rows)
   - Measure import duration
   - Test concurrent imports

2. **Advanced Features**:
   - Create relationships between imported graphs
   - Test incremental imports (upsert)
   - Schedule periodic imports

3. **Integration Testing**:
   - Create rules that span multiple graphs
   - Test precedent search across all graphs
   - Verify cache invalidation after imports

4. **Production Deployment**:
   - Document production import procedures
   - Set up monitoring for import failures
   - Create backup strategy for imported graphs

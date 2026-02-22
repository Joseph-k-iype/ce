# Compliance Engine v7.0 - Developer Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Graph-Native Design](#graph-native-design)
4. [CSV Data Dictionaries](#csv-data-dictionaries)
5. [Rule System](#rule-system)
6. [Multi-Rule Evaluation](#multi-rule-evaluation)
7. [Creating New Rules](#creating-new-rules)
8. [Multi-Agent Workflow](#multi-agent-workflow)
9. [Google A2A SDK Integration](#google-a2a-sdk-integration)
10. [Agent Prompts & Entity Linking](#agent-prompts--entity-linking)
11. [Graph Schemas](#graph-schemas)
12. [Frontend Architecture](#frontend-architecture)
13. [Non-Blocking Architecture & Jobs](#non-blocking-architecture--jobs)
14. [API Reference](#api-reference)
15. [Docker Compose](#docker-compose)
16. [Testing](#testing)
17. [Configuration](#configuration)
18. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The Compliance Engine is built on a graph-native, two-graph architecture using FalkorDB, with a React+TypeScript frontend and a LangGraph-based multi-agent backend. Agent-to-agent communication uses the Google A2A SDK (`a2a-sdk>=0.3.22`). All runtime data is served from the graph — no CSV/JSON file reads after build.

### System Components

```
+---------------------------------------------------------------------------+
|                     React 19 + TypeScript Frontend                        |
|  +----------------+  +----------------+  +-----------------------------+  |
|  | Policy Overview|  | Policy         |  | Policy Generator            |  |
|  | (Data Table)   |  | Evaluator      |  | (6-Step Wizard + SSE)       |  |
|  +----------------+  +----------------+  +-----------------------------+  |
|  +----------------+  +-----------------------------------------------+   |
|  | Policy Editor  |  | Rule Editor (/editor/:ruleId) React Flow      |   |
|  | (Rules Table)  |  | Entity Linking via LINKED_TO                  |   |
|  +----------------+  +-----------------------------------------------+   |
|  Login (admin/admin, user/user) | Role-Based Access | Tailwind v4        |
+-------------------------------------------+-------------------------------+
|         FastAPI Server (Routers) — Port 5001                              |
|  evaluation | metadata | wizard | sandbox | agent_events | health        |
|  rule_links | jobs | rules_overview | graph_data | admin                 |
+-------------------------------------------+-------------------------------+
|  Services Layer            |  Multi-Agent Layer (LangGraph + A2A SDK)     |
|  - RulesEvaluator          |  - Supervisor -> Analyzer -> Dictionary      |
|  - SandboxService          |  - -> CypherGen -> Validator -> Tester       |
|  - SessionStore            |  - Google A2A SDK AgentExecutors             |
|  - CacheService            |  - Event-sourced audit trail                 |
|  - JobManager              |  - Non-blocking via asyncio.create_task()    |
|  - SSEManager              |  - Real-time SSE progress streaming          |
+-------------------------------------------+-------------------------------+
|                      FalkorDB (Graph Database)                            |
|  +------------------------------+  +----------------------------------+  |
|  |    RulesGraph                 |  |     DataTransferGraph             |  |
|  |  Rules, permissions, duties,  |  |  Historical cases, assessments,   |  |
|  |  legal entities, regulators,  |  |  purposes, processes,             |  |
|  |  authorities, GBGF, data     |  |  personal data categories          |  |
|  |  categories, processes, GDC,  |  |                                   |  |
|  |  data subjects, country groups|  |                                   |  |
|  +------------------------------+  +----------------------------------+  |
+---------------------------------------------------------------------------+
```

### Key Directories

```
compliance_engine/
├── api/
│   ├── main.py              # App entrypoint, router registration
│   ├── dependencies.py      # Pagination, search filter dependencies
│   └── routers/             # 12 FastAPI router modules
├── agents/
│   ├── executors/           # A2A SDK AgentExecutor implementations
│   ├── nodes/               # Thin LangGraph node shims
│   ├── prompts/             # 7 prompt files + builder (with entity linking)
│   ├── workflows/           # LangGraph StateGraph
│   ├── protocol/            # A2A agent registry
│   ├── audit/               # Event store & event types
│   └── state/               # WizardAgentState TypedDict
├── services/
│   ├── rules_evaluator.py   # Multi-rule evaluation engine
│   ├── job_manager.py       # Background job execution
│   ├── sse_manager.py       # SSE connection manager
│   └── ...                  # database, cache, sandbox, session store
├── rules/
│   ├── dictionaries/        # Country groups & rule definitions
│   └── data_dictionaries/
│       └── csv/             # 11 CSV data dictionaries
├── models/                  # Pydantic models
├── frontend/                # Vite + React 19 + TypeScript
│   └── src/
│       ├── pages/           # 5 pages + rule editor
│       ├── components/      # evaluator/, wizard/, editor/, layout/, common/
│       ├── stores/          # Zustand stores
│       └── ...
├── nginx/                   # Nginx reverse proxy config
├── docker-compose.yml       # Full stack deployment
└── tests/                   # Test suite
```

---

## Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- FalkorDB (via Docker or native)

### 1. Start FalkorDB

```bash
docker run -p 6379:6379 falkordb/falkordb:latest
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AI service credentials
```

### 4. Build the Graph

```bash
python main.py --build-graph
```

Ingests all 11 CSVs and rule definitions into FalkorDB. After this, CSV files are not needed at runtime.

### 5. Run Backend & Frontend

```bash
# Terminal 1: Backend
python main.py

# Terminal 2: Frontend (dev mode with HMR)
cd frontend && npm run dev
```

- Backend: http://localhost:5001
- Frontend: http://localhost:3001
- API Docs: http://localhost:5001/docs

---

## Graph-Native Design

After `--build-graph`, ALL data is served from FalkorDB. No runtime CSV/JSON reads.

### Startup Validation

`api/main.py` validates the graph on startup:
```python
rules_count = db.execute_rules_query("MATCH (r:Rule) RETURN count(r) as cnt")
country_count = db.execute_rules_query("MATCH (c:Country) RETURN count(c) as cnt")
# Warns if counts are 0
```

### Metadata Endpoints

All metadata endpoints in `api/routers/metadata.py` are pure Cypher queries:
```python
@router.get("/countries")
async def get_countries(db=Depends(get_db)):
    return _rules_query(db, "MATCH (c:Country) RETURN c.name as name ORDER BY c.name")
```

### Design Rules
1. Never read CSV/JSON files at runtime
2. All entity data lives in the graph
3. Adding new data = update CSV → rebuild graph → restart
4. Cache invalidation happens automatically after graph writes

---

## CSV Data Dictionaries

All 11 CSV files live in `rules/data_dictionaries/csv/`:

| # | CSV File | Graph Node Type | Key Fields |
|---|----------|----------------|------------|
| 1 | `countries.csv` | Country | Name, ISO 2, ISO 3, Legal Entity ID, RTN Code |
| 2 | `legal_entities.csv` | LegalEntity | Name |
| 3 | `regulators.csv` | Regulator | Country Code, Region, Type, Definition, Notification/Approval flags |
| 4 | `authorities.csv` | Authority | Name, Country Code ISO 2 |
| 5 | `purpose_of_processing.csv` | PurposeOfProcessing | Name, Description |
| 6 | `data_categories.csv` | DataCategory | Name, Definition, GDPR Category Name |
| 7 | `sensitive_data_categories.csv` | SensitiveDataCategory | Name, Definition, Country Code |
| 8 | `processes.csv` | Process | Name, Definition, L1/L2/L3 Names, Global Business Function |
| 9 | `global_business_functions.csv` | GlobalBusinessFunction | Name, RTN Code, GBGF L1/L2, Privacy Notice |
| 10 | `gdc.csv` | GDC | Name, Definition, Data Domain, Privacy Indicator, L2/L3 |
| 11 | `data_subjects.csv` | DataSubject | Name, Definition |

### Adding a New CSV

1. Create CSV in `rules/data_dictionaries/csv/`
2. Add ingestion method in `utils/graph_builder.py`
3. Call it from `build()` orchestration
4. Add metadata endpoint in `api/routers/metadata.py`
5. Update `get_all_dropdown_values()` to include new data
6. Add TypeScript types in `frontend/src/types/api.ts`
7. Rebuild: `python main.py --build-graph`

---

## Rule System

### Three Rule Sets

**SET 1: Case-Matching Rules** — Search historical cases in DataTransferGraph
**SET 2A: Transfer Rules** — Country-to-country permissions/prohibitions
**SET 2B: Attribute Rules** — Rules based on data attributes

### Key Evaluation Logic
- **Multi-rule**: ALL matching rules fire — no short-circuit
- **Case-insensitive CONTAINS** matching on country names
- **Rule expiration**: `valid_until` date checked against today
- **Prohibition override**: If ANY triggered rule is a prohibition → PROHIBITED
- **Prohibition-duty separation**: Prohibitions do NOT have duties

---

## Multi-Rule Evaluation

The evaluator (`services/rules_evaluator.py`) is the core of the engine:

### Evaluation Flow

1. **Phase 0**: Retrieve all candidate rules from graph (country/group/LE matching)
2. **Phase 1**: For each rule, check structured field matches (data_categories, purposes, processes)
3. **Phase 2**: For each rule, check fuzzy keyword matches (personal_data_names, metadata)
4. **Phase 3**: Check LINKED_TO entity matches
5. **Aggregation**: Deduplicate by rule_id, union duties/assessments

### Key Methods
- `_match_attribute_keywords()` — processes ALL rules independently (no early exit)
- `_match_graph_linked_attributes()` — matches user input against LINKED_TO entities
- Result aggregation deduplicates by `rule_id` and unions all duties/assessments

---

## Creating New Rules

### Method 1: Manual Addition

```python
# rules/dictionaries/rules_definitions.py
TRANSFER_RULES["RULE_UK_CHINA_TECH"] = TransferRule(
    rule_id="RULE_UK_CHINA_TECH",
    name="UK to China Technology Transfer",
    description="Prohibit transfer of technology data from UK to China",
    priority=15,
    origin_countries=frozenset(["United Kingdom"]),
    receiving_countries=frozenset(["China"]),
    outcome=RuleOutcome.PROHIBITION,
    odrl_type="Prohibition",
)
```

Then rebuild: `python main.py --build-graph`

### Method 2: 6-Step Wizard

| Step | Action |
|------|--------|
| 1. Rule Input | Enter rule text, select origin country, toggle PII flag |
| 2. AI Analysis | Watch AI agents analyze (real-time SSE progress) |
| 3. Metadata | Pre-filled from AI suggestions, editable with graph dropdowns |
| 4. Review | Edit generated rule definition |
| 5. Sandbox Test | Load into temp graph and test |
| 6. Approve | Promote to main RulesGraph |

### Method 3: CLI Tool

```bash
python -m cli.rule_generator_cli --interactive
python -m cli.rule_generator_cli --rule "Prohibit transfers from UK to China"
```

---

## Multi-Agent Workflow

### LangGraph Architecture

```
Entry -> Supervisor -> {rule_analyzer | data_dictionary | cypher_generator |
                        validator | reference_data | rule_tester | human_review}
          ^              |
          +-- Supervisor <-- (retry on validation failure, max 3 iterations)
                             |
                     complete / fail -> END
```

### Agent Executors

| Agent | Executor | Technique | FalkorDB |
|-------|----------|-----------|----------|
| **Supervisor** | `SupervisorExecutor` | Dynamic prompt with state | No |
| **Rule Analyzer** | `RuleAnalyzerExecutor` | CoT + ToT + MoE | No |
| **Data Dictionary** | `DataDictionaryExecutor` | Category-specific prompts | No |
| **Cypher Generator** | `CypherGeneratorExecutor` | MoE reasoning | `EXPLAIN` validation |
| **Validator** | `ValidatorExecutor` | Schema-aware checklist | Temp graph test |
| **Reference Data** | `ReferenceDataExecutor` | Gap analysis | Country group lookup |
| **Rule Tester** | `TesterExecutor` | Scenario generation | Sandbox evaluation |

---

## Google A2A SDK Integration

Each agent is a Google A2A SDK `AgentExecutor`, bridged to LangGraph:

```
LangGraph calls:  node_fn(state) -> state       [agents/nodes/*.py]
                       |
                  wrap_executor_as_node()         [agents/executors/base_executor.py]
                       |
                  InProcessRequestContext(state)
                  EventQueue()
                       |
                  executor.execute(ctx, queue)    [agents/executors/*_executor.py]
                       |
                  _drain_event_queue_to_sse()     [A2A events -> SSE AgentEvent]
                       |
                  return state
```

### Adding a New Agent

1. Create `agents/executors/my_agent_executor.py`
2. Create `agents/nodes/my_agent.py` with `wrap_executor_as_node()`
3. Register agent card in `agents/protocol/__init__.py`
4. Add node to workflow in `agents/workflows/rule_ingestion_workflow.py`

---

## Agent Prompts & Entity Linking

All prompts are in `agents/prompts/`. The prompts reference the full graph schema.

### Entity Types in Prompts

The analyzer now produces `suggested_linked_entities` with these entity types:
- **Regulators**: ICO, CNIL, BaFin, etc.
- **Authorities**: Data protection authorities
- **PurposeOfProcessing**: Standardized processing purposes
- **DataCategory**: With GDPR classification
- **SensitiveDataCategory**: Country-specific sensitive data
- **Process**: 3-level hierarchy (L1/L2/L3)
- **GDC**: Group Data Categories
- **DataSubject**: Data subject types
- **LegalEntity**: Legal entities
- **GlobalBusinessFunction**: Business functions with RTN codes

### Cypher Generator

The Cypher generator now produces 4 queries:
1. `rule_check` — Check for matching historical cases
2. `rule_insert` — Insert rule with ORIGINATES_FROM/RECEIVED_IN relationships
3. `rule_links` — Create LINKED_TO edges to entities
4. `validation` — Validate the rule works

### Prompt Builder

`agents/prompts/prompt_builder.py` assembles prompts with dynamic context injection. Each agent has a dedicated `build_*_prompt()` function.

---

## Graph Schemas

### RulesGraph

**Nodes:**
- Country (name, iso2, iso3, rtn_code)
- CountryGroup (name)
- LegalEntity (name, country)
- Regulator (name, country_code, region, regulator_type, regulator_definition, ...)
- Authority (name, country_code)
- GlobalBusinessFunction (name, rtn_code, gbgf_level_1, gbgf_level_2)
- Rule (rule_id, name, description, rule_type, priority, outcome, ...)
- Action, Permission, Prohibition, Duty
- PurposeOfProcessing (name, description)
- DataCategory (name, definition, gdpr_category_name)
- SensitiveDataCategory (name, definition, country_code)
- Process (name, definition, level_1_name, level_2_name, level_3_name)
- GDC (name, definition, data_domain, data_privacy_indicator, gdc_level_2, gdc_level_3)
- DataSubject (name, definition)
- Attribute (name)

**Key Relationships:**
```
Country -[:BELONGS_TO]-> CountryGroup
Country -[:HAS_LEGAL_ENTITY]-> LegalEntity
Country -[:HAS_REGULATOR]-> Regulator
Country -[:HAS_AUTHORITY]-> Authority
Country -[:HAS_GBGF]-> GlobalBusinessFunction
Country -[:HAS_SENSITIVE_DATA_CATEGORY]-> SensitiveDataCategory
Rule -[:TRIGGERED_BY_ORIGIN]-> CountryGroup | Country | LegalEntity
Rule -[:TRIGGERED_BY_RECEIVING]-> CountryGroup | Country | LegalEntity
Rule -[:ORIGINATES_FROM]-> Country
Rule -[:RECEIVED_IN]-> Country
Rule -[:HAS_PERMISSION]-> Permission
Rule -[:HAS_PROHIBITION]-> Prohibition
Rule -[:LINKED_TO]-> Regulator | Authority | PurposeOfProcessing | DataCategory |
                     SensitiveDataCategory | Process | GDC | DataSubject |
                     LegalEntity | GlobalBusinessFunction
Permission -[:CAN_HAVE_DUTY]-> Duty  (Prohibitions do NOT have duties)
Process -[:HAS_SUBPROCESS]-> Process
Process -[:BELONGS_TO_GBGF]-> GlobalBusinessFunction
```

### DataTransferGraph

```
Case -[:ORIGINATES_FROM]-> Country
Case -[:TRANSFERS_TO]-> Jurisdiction
Case -[:HAS_PURPOSE]-> Purpose
Case -[:HAS_PROCESS_L1/L2/L3]-> ProcessL1/L2/L3
Case -[:HAS_PERSONAL_DATA]-> PersonalData
Case -[:HAS_PERSONAL_DATA_CATEGORY]-> PersonalDataCategory
```

---

## Frontend Architecture

### Tech Stack
- React 19 + TypeScript + Vite (port 3001)
- Zustand for state management
- TanStack React Query for API data
- React Flow (@xyflow/react) for graph visualization
- Tailwind CSS v4
- React Router v7

### Pages

| Page | Route | Component |
|------|-------|-----------|
| Login | `/login` | LoginPage |
| Policy Overview | `/` | HomePage |
| Policy Evaluator | `/evaluator` | EvaluatorPage |
| Policy Generator | `/generator` | WizardPage |
| Policy Editor | `/editor` | EditorPage (table + graph toggle) |
| Rule Editor | `/editor/:ruleId` | RuleEditorPage (React Flow + entity linking) |

### Wizard Steps (New Order)

1. **Step1RuleInput** — Rule text + origin country + PII toggle
2. **Step2AIAnalysis** — Read-only AI progress (SSE streaming, auto-advances)
3. **Step3Metadata** — Pre-filled from AI, editable with graph dropdowns
4. **Step4Review** — Edit generated rule definition
5. **Step5SandboxTest** — Test in temporary graph
6. **Step6Approve** — Promote to main graph

### Policy Editor

Two views:
1. **RulesOverviewTable** — Searchable/filterable table. Click row → per-rule editor.
2. **RuleEditorPage** — Per-rule React Flow canvas with LINKED_TO management sidebar.

---

## Non-Blocking Architecture & Jobs

### Background AI Execution

The wizard uses non-blocking execution:
```python
async def _run_workflow_background(session, session_id):
    result = await asyncio.to_thread(run_rule_ingestion, ...)
    session.workflow_result = result

# In step handler:
asyncio.create_task(_run_workflow_background(session, session_id))
```

### Job Manager

`services/job_manager.py` provides generic background job management:
```python
job_mgr = get_job_manager()
job_id = job_mgr.submit("rule_generation", func, kwargs)
status = job_mgr.get_job(job_id)
```

### Job API

- `POST /api/jobs/submit` — Submit background job
- `GET /api/jobs/{job_id}/status` — Poll status
- `GET /api/jobs/{job_id}/stream` — SSE progress stream
- `GET /api/jobs` — List recent jobs
- `POST /api/jobs/{job_id}/cancel` — Cancel running job

---

## API Reference

### Evaluation
- `POST /api/evaluate-rules` — Multi-rule evaluation (graph-native)
- `POST /api/search-cases` — Search historical cases

### Metadata (Graph-Native)
- `GET /api/countries` — Countries from graph
- `GET /api/purposes` — Purposes of processing
- `GET /api/processes` — Processes (L1/L2/L3)
- `GET /api/all-dropdown-values` — All dropdown values
- `GET /api/legal-entities` / `GET /api/legal-entities/{country}`
- `GET /api/purpose-of-processing`
- `GET /api/group-data-categories`
- `GET /api/regulators` / `GET /api/regulators/{country_iso2}`
- `GET /api/authorities` / `GET /api/authorities/{country_iso2}`
- `GET /api/global-business-functions`
- `GET /api/sensitive-data-categories`
- `GET /api/data-categories`

### Rule Links (LINKED_TO CRUD)
- `GET /api/rules/{rule_id}/links`
- `POST /api/rules/{rule_id}/link`
- `DELETE /api/rules/{rule_id}/unlink`
- `POST /api/rules/{rule_id}/link-regulator`
- `POST /api/rules/{rule_id}/link-authority`
- `GET /api/rules/{rule_id}/subgraph`

### Wizard (6-Step)
- `POST /api/wizard/start-session`
- `POST /api/wizard/submit-step` (triggers AI at step 1)
- `GET /api/wizard/session/{id}`
- `PUT /api/wizard/session/{id}/edit-rule`
- `PUT /api/wizard/session/{id}/edit-terms`
- `POST /api/wizard/session/{id}/load-sandbox`
- `POST /api/wizard/session/{id}/sandbox-evaluate`
- `POST /api/wizard/session/{id}/approve`
- `DELETE /api/wizard/session/{id}`

### Session Persistence
- `POST /api/wizard/save-session`
- `GET /api/wizard/saved-sessions`
- `GET /api/wizard/resume-session/{id}`
- `DELETE /api/wizard/saved-session/{id}`

### Background Jobs
- `POST /api/jobs/submit`
- `GET /api/jobs/{job_id}/status`
- `GET /api/jobs/{job_id}/stream`
- `GET /api/jobs`
- `POST /api/jobs/{job_id}/cancel`

### Agent Events (SSE)
- `GET /api/agent-events/stream/{session_id}`

### Admin & Health
- `GET /health`
- `GET /api/stats`
- `GET /api/cache/stats` / `POST /api/cache/clear`

---

## Docker Compose

```bash
docker-compose up -d
```

| Service | Port | Description |
|---------|------|-------------|
| falkordb | 6379 | Graph database |
| backend | 5001 | FastAPI server |
| frontend | 3001 | Vite dev server |
| nginx | 80 | Reverse proxy with SSE support |

Nginx routes:
- `/api/*` → backend
- `/api/agent-events/*`, `/api/jobs/*` → backend (proxy_buffering off for SSE)
- `/*` → frontend

---

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=services --cov=api --cov-report=html
cd frontend && npm run build  # TypeScript compilation check
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKORDB_HOST` | localhost | FalkorDB host |
| `FALKORDB_PORT` | 6379 | FalkorDB port |
| `API_PORT` | 5001 | API server port |
| `AI_LLM_MODEL` | o3-mini | LLM model name |
| `ENABLE_AI_RULE_GENERATION` | true | Enable AI features |
| `ENABLE_CACHE` | true | Enable caching |
| `CACHE_TTL` | 300 | Cache TTL in seconds |

---

## Troubleshooting

1. **Empty dropdowns** → Graph may be empty. Run `python main.py --build-graph`
2. **"AI service is not enabled"** → Set `ENABLE_AI_RULE_GENERATION=true` and check credentials
3. **Wizard stuck at AI analysis** → Check backend logs, verify AI credentials, check SSE stream
4. **Rule validation failed** → Check `rule_id` starts with `RULE_`, priority is string, odrl_type matches outcome
5. **Progress bar stuck at 0%** → Verify SSE connection, check `progress_pct` in agent events
6. **Login not working** → Use `admin`/`admin` or `user`/`user`. Clear localStorage if corrupted.
7. **Editor not showing links** → Ensure rule exists and has LINKED_TO relationships in graph
8. **Port conflicts** → Backend: 5001, Frontend: 3001, FalkorDB: 6379, Nginx: 80

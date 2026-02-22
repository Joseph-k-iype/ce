# Compliance Engine v7.0.0

A scalable, production-ready compliance engine for cross-border data transfer evaluation using a graph-native architecture (FalkorDB), a React frontend, and AI-powered multi-agent rule generation. Agent-to-agent communication uses the [Google A2A SDK](https://github.com/google/a2a-python) (`a2a-sdk`) with LangGraph as the workflow backbone.

## Architecture Overview

```
compliance_engine/
├── api/                        # FastAPI application
│   ├── main.py                 # App entrypoint, router registration, static serving
│   ├── dependencies.py         # Shared dependencies (pagination, search filters)
│   └── routers/                # API router modules
│       ├── evaluation.py       # POST /api/evaluate-rules, /api/search-cases
│       ├── metadata.py         # Graph-native: countries, purposes, legal-entities, regulators, etc.
│       ├── rules_overview.py   # GET /api/rules-overview, /api/rules-overview-table
│       ├── graph_data.py       # GET /api/graph/rules-network, /api/graph/country-groups
│       ├── wizard.py           # Wizard lifecycle (6-step flow) with non-blocking AI
│       ├── sandbox.py          # Sandbox graph testing
│       ├── agent_events.py     # SSE streaming for agent progress
│       ├── rule_links.py       # CRUD for Rule↔Entity LINKED_TO relationships
│       ├── jobs.py             # Background job submission, tracking, streaming
│       ├── admin.py            # Admin CRUD operations
│       └── health.py           # GET /health, /api/stats, /api/cache/*
├── agents/                     # Multi-agent system
│   ├── ai_service.py           # Token auth & LLM calls (o3-mini)
│   ├── state/                  # LangGraph state
│   ├── executors/              # Google A2A SDK AgentExecutor implementations
│   ├── nodes/                  # Thin LangGraph node shims (wrap executors)
│   ├── prompts/                # All agent prompts (with entity linking support)
│   ├── workflows/              # LangGraph StateGraph
│   ├── protocol/               # A2A agent registry
│   └── audit/                  # Event-sourced audit trail
├── config/                     # Configuration (Pydantic v2 settings)
├── models/                     # Pydantic models (schemas, wizard, AgentEvent, jobs)
├── rules/                      # Rule definitions & data dictionaries
│   ├── dictionaries/           # Country groups & rule definitions
│   ├── data_dictionaries/
│   │   └── csv/                # 11 CSV data dictionaries (single source of truth)
│   └── templates/              # Cypher query templates
├── services/                   # Core services
│   ├── database.py             # FalkorDB connection
│   ├── cache.py                # LRU cache with TTL
│   ├── rules_evaluator.py      # Main evaluation engine (multi-rule, graph-native)
│   ├── sandbox_service.py      # Sandbox graph lifecycle
│   ├── session_store.py        # Wizard session persistence (JSON file-based)
│   ├── sse_manager.py          # SSE connection manager
│   └── job_manager.py          # Background job execution and tracking
├── utils/
│   ├── graph_builder.py        # Build RulesGraph from CSVs + rule definitions
│   └── data_uploader.py        # Upload case data to DataTransferGraph
├── frontend/                   # React 19 + TypeScript app (Vite)
│   └── src/
│       ├── pages/              # HomePage, EvaluatorPage, WizardPage, EditorPage, LoginPage
│       ├── components/         # evaluator/, wizard/ (6 steps), editor/, layout/, common/
│       ├── stores/             # Zustand stores (wizardStore, evaluationStore, editorStore, authStore)
│       ├── services/           # API client layer
│       ├── hooks/              # Custom hooks (useAgentEvents, useDropdownData, useEditorData)
│       └── types/              # TypeScript interfaces
├── nginx/                      # Nginx reverse proxy config
├── docker-compose.yml          # Full stack deployment
├── cli/                        # Interactive CLI for rule generation
├── data/saved_sessions/        # Server-side wizard session persistence
└── tests/                      # Test suite
```

## Key Design Principles

- **Graph-Native**: After `--build-graph`, ALL data is served from FalkorDB. No runtime CSV/JSON reads.
- **11 CSV Data Dictionaries**: Single source of truth for entities (countries, regulators, authorities, processes, etc.)
- **Multi-Rule Evaluation**: ALL matching rules fire — no short-circuit. Aggregate results across countries.
- **Non-Blocking AI**: Rule generation runs as background tasks via `asyncio.create_task()`.
- **SSE Streaming**: Real-time progress updates from agent pipeline to frontend.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Key variables:
```env
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
AI_TOKEN_API_URL=https://your-token-api/translate
AI_LLM_API_URL=https://your-llm-api/chat/completions
AI_LLM_MODEL=o3-mini
ENABLE_AI_RULE_GENERATION=true
```

### 3. Build Rules Graph

```bash
python main.py --build-graph
```

This ingests all 11 CSVs and rule definitions into FalkorDB. After this, CSV files are not needed at runtime.

### 4. Build Frontend

```bash
cd frontend && npm run build && cd ..
```

### 5. Run the Server

```bash
python main.py
```

Access:
- Frontend: http://localhost:5001/ (served by FastAPI)
- Frontend Dev: http://localhost:3001/ (Vite dev server with HMR)
- API Docs: http://localhost:5001/docs

### Docker Compose (Full Stack)

```bash
docker-compose up -d
```

Services:
- **FalkorDB**: port 6379
- **Backend**: port 5001
- **Frontend**: port 3001
- **Nginx**: port 80 (reverse proxy)

## Authentication

The UI requires login. Two built-in accounts are available:

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `admin` | `admin` | Admin | Policy Overview, Policy Evaluator, Policy Generator, Policy Editor |
| `user` | `user` | User | Policy Overview, Policy Evaluator |

Admin-only pages (Policy Generator, Policy Editor) are hidden from the navigation for regular users and protected by route guards.

## UI Pages

| Page | Route | Role | Description |
|------|-------|------|-------------|
| Login | `/login` | All | Username/password authentication |
| Policy Overview | `/` | All | Data table with filters, search, and rule statistics |
| Policy Evaluator | `/evaluator` | All | Evaluate compliance with rich entity dropdowns |
| Policy Generator | `/generator` | Admin | 6-step wizard for AI-powered rule creation |
| Policy Editor | `/editor` | Admin | Rules table overview + per-rule graph editor |
| Rule Editor | `/editor/:ruleId` | Admin | Per-rule React Flow editor with entity linking |

## CSV Data Dictionaries

All 11 CSV files live in `rules/data_dictionaries/csv/` and are ingested during `--build-graph`:

| CSV File | Graph Node Type | Key Fields |
|----------|----------------|------------|
| `countries.csv` | Country | Name, ISO 2, ISO 3, Legal Entity ID, RTN Code |
| `legal_entities.csv` | LegalEntity | Name |
| `regulators.csv` | Regulator | Country Code, Region, Type, Definition, Notification/Approval flags |
| `authorities.csv` | Authority | Name, Country Code ISO 2 |
| `purpose_of_processing.csv` | PurposeOfProcessing | Name, Description |
| `data_categories.csv` | DataCategory | Name, Definition, GDPR Category Name |
| `sensitive_data_categories.csv` | SensitiveDataCategory | Name, Definition, Country Code |
| `processes.csv` | Process | Name, Definition, L1/L2/L3 Names, Global Business Function |
| `global_business_functions.csv` | GlobalBusinessFunction | Name, RTN Code, GBGF L1/L2, Privacy Notice |
| `gdc.csv` | GDC | Name, Definition, Data Domain, Privacy Indicator, L2/L3 |
| `data_subjects.csv` | DataSubject | Name, Definition |

## Three Rule Sets

### SET 1: Case-Matching Rules
Search for historical cases in the DataTransferGraph. Uses case-insensitive CONTAINS matching on country names. Rules with an expired `valid_until` date are skipped. If ANY triggered rule is a prohibition, the overall result is **PROHIBITED**.

**Defined in:** `rules/dictionaries/rules_definitions.py` -> `CASE_MATCHING_RULES`

### SET 2A: Transfer Rules
Country-to-country transfer permissions/prohibitions with highest priority.

**Defined in:** `rules/dictionaries/rules_definitions.py` -> `TRANSFER_RULES`

### SET 2B: Attribute Rules
Rules based on data attributes (health, financial, biometric data).

**Defined in:** `rules/dictionaries/rules_definitions.py` -> `ATTRIBUTE_RULES`

## Key Features

### Graph-Native Architecture
After building the graph, ALL endpoints serve data from FalkorDB via Cypher queries. No runtime file I/O. This ensures:
- Single source of truth (the graph)
- Fast query performance
- Consistent data across all endpoints

### Multi-Rule Evaluation
The evaluator fires ALL matching rules — no short-circuit. Results are aggregated:
- All triggered rules are collected across countries
- Deduplicated by `rule_id`
- Duties and assessments are unioned
- If ANY rule is a prohibition → overall status is **PROHIBITED**

### Entity Linking (LINKED_TO)
Rules can be linked to graph entities via `LINKED_TO` relationships:
- Regulators, Authorities
- PurposeOfProcessing, DataCategory, SensitiveDataCategory
- Process, GDC, DataSubject
- LegalEntity, GlobalBusinessFunction

The editor provides a UI for managing these links per rule.

### Legal Entity Support
Rules and evaluations can target specific legal entities within countries. Legal entities are loaded from `legal_entities.csv` and linked to countries in the graph.

### Prohibition Logic
- Prohibitions do NOT have duties (only permissions can have duties)
- If ANY triggered rule is a prohibition, the overall transfer status is **PROHIBITED**
- This is enforced in both the graph schema and the evaluation engine

### Rule Expiration
Rules can have a `valid_until` date. Expired rules are automatically excluded from evaluation via the Cypher query: `WHERE r.valid_until IS NULL OR r.valid_until >= $today`.

### Non-Blocking AI Pipeline
Rule generation runs as a background task. The wizard returns immediately with a session ID, and the frontend polls or uses SSE to track progress. Multiple rule generations can run concurrently via the job manager.

### Session Save/Resume
Wizard sessions can be saved from Step 4 (Review) onwards and resumed later. Sessions are persisted both server-side (JSON files in `data/saved_sessions/`) and client-side (localStorage for auto-recovery).

## Policy Generator Wizard (6 Steps)

Access the wizard at http://localhost:5001/generator (admin login required):

| Step | Action |
|------|--------|
| 1. Rule Input | Enter rule text, select origin country, toggle PII flag |
| 2. AI Analysis | Watch AI agents analyze the rule (real-time SSE progress) |
| 3. Metadata | Pre-filled from AI suggestions, all editable with graph dropdowns |
| 4. Review | Edit generated rule: ID, title, description, permission/prohibition, actions, duties |
| 5. Sandbox Test | Load rule into temporary graph and test with sample evaluations |
| 6. Approve | Confirm and promote rule to the main RulesGraph |

Sessions can be saved from Step 4 onwards and resumed later.

### CLI Tool

```bash
python -m cli.rule_generator_cli --interactive
python -m cli.rule_generator_cli --rule "Prohibit transfers from UK to China"
```

## API Endpoints

### Evaluation
- `POST /api/evaluate-rules` - Evaluate transfer compliance (multi-rule, graph-native)
- `POST /api/search-cases` - Search historical cases

### Rules & Metadata (Graph-Native)
- `GET /api/rules-overview` - Get all rules overview
- `GET /api/rules-overview-table` - Table-friendly rules data with filters
- `GET /api/countries` - List countries (from graph)
- `GET /api/purposes` - List purposes of processing
- `GET /api/processes` - List processes (L1/L2/L3)
- `GET /api/all-dropdown-values` - All dropdown values (countries, purposes, processes, legal entities, data categories, regulators, authorities, GBGF, sensitive data categories)
- `GET /api/legal-entities` - Legal entity mappings by country
- `GET /api/legal-entities/{country}` - Legal entities for a specific country
- `GET /api/purpose-of-processing` - Purposes of processing (from graph)
- `GET /api/group-data-categories` - Group data categories
- `GET /api/regulators` - All regulators
- `GET /api/regulators/{country_iso2}` - Regulators for a country
- `GET /api/authorities` - All authorities
- `GET /api/authorities/{country_iso2}` - Authorities for a country
- `GET /api/global-business-functions` - Global business functions
- `GET /api/sensitive-data-categories` - Sensitive data categories
- `GET /api/data-categories` - Data categories with GDPR classification

### Rule Links (LINKED_TO CRUD)
- `GET /api/rules/{rule_id}/links` - Get all linked entities for a rule
- `POST /api/rules/{rule_id}/link` - Create LINKED_TO edge
- `DELETE /api/rules/{rule_id}/unlink` - Remove LINKED_TO edge
- `POST /api/rules/{rule_id}/link-regulator` - Link to a regulator
- `POST /api/rules/{rule_id}/link-authority` - Link to an authority
- `GET /api/rules/{rule_id}/subgraph` - Get rule subgraph for React Flow

### Wizard (6-Step Flow)
- `POST /api/wizard/start-session` - Start wizard session
- `POST /api/wizard/submit-step` - Submit step data (triggers AI at step 1)
- `GET /api/wizard/session/{id}` - Get session state
- `PUT /api/wizard/session/{id}/edit-rule` - Edit rule definition
- `PUT /api/wizard/session/{id}/edit-terms` - Edit terms dictionary
- `POST /api/wizard/session/{id}/load-sandbox` - Load to sandbox graph
- `POST /api/wizard/session/{id}/sandbox-evaluate` - Test in sandbox
- `POST /api/wizard/session/{id}/approve` - Approve & load to main graph
- `DELETE /api/wizard/session/{id}` - Cancel session

### Wizard Session Persistence
- `POST /api/wizard/save-session` - Save session for later resume
- `GET /api/wizard/saved-sessions` - List saved sessions
- `GET /api/wizard/resume-session/{id}` - Resume a saved session
- `DELETE /api/wizard/saved-session/{id}` - Delete saved session

### Background Jobs
- `POST /api/jobs/submit` - Submit a background job (rule generation)
- `GET /api/jobs/{job_id}/status` - Poll job status
- `GET /api/jobs/{job_id}/stream` - SSE stream for job progress
- `GET /api/jobs` - List recent jobs
- `POST /api/jobs/{job_id}/cancel` - Cancel a running job

### Agent Events
- `GET /api/agent-events/stream/{session_id}` - SSE event stream

### Admin & Health
- `GET /health` - Health check
- `GET /api/stats` - System statistics
- `GET /api/cache/stats` - Cache statistics
- `POST /api/cache/clear` - Clear cache
- `GET /api/agent/sessions` - List audit sessions
- `GET /api/agent/sessions/{id}` - Session details

## Graph Schema

### RulesGraph

**Nodes:**
- Country (name, iso2, iso3, rtn_code)
- CountryGroup (name)
- LegalEntity (name, country)
- Regulator (name, country_code, region, regulator_type, ...)
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
- `Country -[:BELONGS_TO]-> CountryGroup`
- `Country -[:HAS_LEGAL_ENTITY]-> LegalEntity`
- `Country -[:HAS_REGULATOR]-> Regulator`
- `Country -[:HAS_AUTHORITY]-> Authority`
- `Country -[:HAS_GBGF]-> GlobalBusinessFunction`
- `Country -[:HAS_SENSITIVE_DATA_CATEGORY]-> SensitiveDataCategory`
- `Rule -[:TRIGGERED_BY_ORIGIN]-> CountryGroup | Country | LegalEntity`
- `Rule -[:TRIGGERED_BY_RECEIVING]-> CountryGroup | Country | LegalEntity`
- `Rule -[:ORIGINATES_FROM]-> Country`
- `Rule -[:RECEIVED_IN]-> Country`
- `Rule -[:HAS_PERMISSION]-> Permission`
- `Rule -[:HAS_PROHIBITION]-> Prohibition`
- `Rule -[:LINKED_TO]-> Regulator | Authority | PurposeOfProcessing | DataCategory | SensitiveDataCategory | Process | GDC | DataSubject | LegalEntity | GlobalBusinessFunction`
- `Permission -[:CAN_HAVE_DUTY]-> Duty` (Prohibitions do NOT have duties)
- `Process -[:HAS_SUBPROCESS]-> Process`
- `Process -[:BELONGS_TO_GBGF]-> GlobalBusinessFunction`

### DataTransferGraph

Nodes: Case, Country, Jurisdiction, Purpose, ProcessL1/L2/L3, PersonalData, PersonalDataCategory

Key relationships: ORIGINATES_FROM, TRANSFERS_TO, HAS_PURPOSE, HAS_PROCESS_L1/L2/L3

## Adding New Rules

### Manual Addition

Edit `rules/dictionaries/rules_definitions.py`:

```python
TRANSFER_RULES["MY_NEW_RULE"] = TransferRule(
    rule_id="RULE_MY_01",
    name="My New Transfer Rule",
    description="Description of the rule",
    priority=5,
    origin_group="EU_EEA",
    receiving_countries=frozenset({"SomeCountry"}),
    outcome=RuleOutcome.PROHIBITION,
    odrl_type="Prohibition",
)
```

Then rebuild: `python main.py --build-graph`

## Testing

```bash
pytest tests/ -v
```

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

## License

Internal use only.

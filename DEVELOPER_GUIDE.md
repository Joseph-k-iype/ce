# Developer Guide: Privacy Policy Engine

This repository wraps a sophisticated React (Vite) frontend around a Python (FastAPI) backend powered by a custom FalkorDB/Redis graph engine instance.

## Architecture

**Frontend Stack**: React 18, Vite, TailwindCSS, React-Select.
**Backend Stack**: FastAPI, Uvicorn, custom Python Graph wrappers.
**Database Layer**: Redis with the FalkorDB Graph module, mounted identically in Docker.

### Request Lifecycle
1. The frontend (`LogicBuilder.tsx` or similar) fires REST calls via Axios interceptors to `/api/*`.
2. The FastAPI routers (`routers/admin.py` or `routers/wizard.py`) sanitize payloads via Pydantic (`models/rule_spec.py`).
3. Business logic is handled by internal services (e.g. `services/rules_evaluator.py`).
4. Graph interactions are facilitated by connection pools (`services/database.py`) and cached recursively using `services/cache.py`.

## Adding New Frontend Components
All dashboard and UI logic resides in `frontend/src/components/dashboard`. 
- Leverage standard Tailwind generic configurations for styling. We rely on gradients, micro-animations, and structured whitespace to maintain a premium feel.
- When mutating backend data, optimistic UI strategies should be favored (e.g., manipulating state instantly while awaiting network resolution), backed by explicit cache invalidation in FastAPI.

## Adding Backend Cypher Features
FalkorDB strictly enforces openCypher syntax.
- **Rules Evaluator**: The workhorse of the app. It calculates boolean intersections by executing complex query templates located in `services/cypher_templates`. 
- **Graph Builder**: `utils/graph_builder.py` reconstructs logic rules deterministically from Excel logic or Pydantic payloads.
- **Cache**: When modifying graph nodes mapping relationships (e.g. `MERGE (Rule)-[:HAS_ATTRIBUTE]->(Attribute)`), YOU MUST call `cache.clear()` in the controller to ensure endpoint hydration doesn't stagnate.

## Run Book
```bash
# Start backend
python3 main.py --reload
# Start frontend
cd frontend
npm run dev
```

# DBA Guide: Privacy Policy Engine

## Database Provider
This application runs structurally on an in-memory embedded graph database. We deploy the **Redis** engine augmented by the **FalkorDB** module, which provides ultra-fast Cypher executions across the semantic compliance models.

## Deployment Footprint
Instances are mapped natively using standard Redis TCP specifications (`localhost:6379`) via Docker.
- Graph ID: `compliance_graph`

## Maintenance and Administration

### Index Strategy
Given the query intensity of the Rule Evaluator, multiple specific indexes are strictly defined. Look within `utils/graph_builder.py::_create_indexes()` during bootstrap:
- Single-property schema indexes on `Country(name)`, `Rule(rule_id)`, `DataCategory(name)`, etc.
- By design, the application does NOT use full-text indexing; instead we rely structurally on exact node traversal (`MATCH (r:Rule)-[:TRIGGERED_BY]->...`).

### Cache Layer
The backend utilizes an LRU caching system (`services/cache.py`) specifically because FalkorDB path-finding across multi-tier conditions can occasionally invoke recursive heavy sub-queries.
- Default TTLs sit at 60s to 600s depending on the volatility of the dimension array.
- When bulk updating rules (e.g., via Excel), the cache is systematically ripped out spanning all namespaces to guarantee referential integrity downstream.

### Fault Tolerance & Circuit Breaking
The connection system guarantees stability by using randomized jitter and exponential backoffs (up to 3 distinct retries) inside `FalkorDBService`. If the graph stalls under immense simulation tests, the connection breaks cleanly rejecting standard API 5xxs without cascading into deadlock.

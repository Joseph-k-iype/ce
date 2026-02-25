# Data Modeler Guide: Privacy Policy Engine

The Privacy Policy Engine relies on an explicit Graph semantic model to enforce its logical guarantees.

## Node Entity Glossary
- **Domain Scope**: `Country`, `CountryGroup`, `LegalEntity`. All geopolitical boundary limits.
- **Data Dimension**: `DataCategory`, `PurposeOfProcessing`, `DataSubject`.
- **Structural Models**: `Rule`, `Action`, `RuleAttribute`.
- **ODRL Components**: `Permission`, `Prohibition`, `Duty`.

## ODRL Ontology (Open Digital Rights Language)
Rather than simple booleans, our relationships encode the outcome state dynamically:
- `(:Rule)-[:HAS_PERMISSION]->(:Permission)`
- `(:Rule)-[:HAS_PROHIBITION]->(:Prohibition)`
- `(:Permission)-[:CAN_HAVE_DUTY]->(:Duty {module: "PIA", value: "Completed"})`

When the simulation engine matches a Rule to the Context scope, it queries the resulting edges to define if data flow is halted or approved, and strictly aggregates residual specific `Duty` requirements before execution.

## The Logic Tree
Introduced explicitly for complex permutations, instances of `Rule` store a stringified payload inside the `logic_tree` property mapping nested AST nodes (`AND`, `OR`, `CONDITION`). This enables recursive, N-depth hierarchical boundaries beyond basic array intersections.

When users manually type strings like "Acme Beta Systems" into visual input arrays, the graph triggers a resilient structural hook returning `MERGE` clauses allocating new semantic boundaries that automatically auto-hydrate backwards up the query pipelines.

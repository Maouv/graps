# Data Contracts

> **Summary Block:** Versioned minimum contracts for deterministic structural graph, semantic overlay, settings, IDs, and confidence.

## Stable IDs
- File: scan-root-relative POSIX path.
- Function: `<file_id>::<qualified_function_name>`.
- Module: canonical language boundary relative to scan root.
- Route: normalized method/path/handler identity.
- Flow: `<root_id>#<flow_kind>`.
AI never rewrites these IDs.

## graph.json
Top-level fields: `schema_version`, scan metadata/hash/diagnostics, typed node collections, typed edge collections, and flows. Entities retain path/language/range/member data needed by their type. Every call edge carries `kind`, `confidence`, source location/order, optional target/candidates, and unresolved reason.

## architecture.json
Contains `schema_version`, `graph_content_hash`, timestamp, module semantic metadata, flow labels, and optional semantic groups. Every module/node/member reference must exist in graph truth. Capabilities are module metadata, never core hierarchy entities.

## settings.json
Contains schema version, default-ON `ai_enrichment`, semantic/user overrides, panel widths, and tab state. Invalid or missing preferences receive safe defaults and never mutate graph truth.

## Determinism
Serialization order is deterministic before hashing/writing. Unknown AI fields are rejected or intentionally ignored by strict model configuration; there is no implicit structural acceptance.

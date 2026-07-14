# Technical Architecture

> **Summary Block:** SSoT for structural truth, module/flow resolution, optional AI enrichment, storage/cache, runtime boundaries, and implementation change areas.

## Truth hierarchy
`filesystem + parser facts → graph.json → optional validated architecture.json → UI`. Missing, stale, invalid, disabled, or unavailable enrichment always falls back to graph truth.

## Runtime boundaries
| Boundary | Owns | Must not do |
|---|---|---|
| Scanner/parsers | Discovery, syntax facts, ranges, calls, routes, diagnostics | Call AI or persist semantic claims |
| Graph/module/flow layer | Stable IDs, deterministic topology, resolution/confidence/order | Guess dynamic calls as resolved |
| AI adapter | Structured enrichment request/retry/cache | Alter graph structure |
| Semantic validator | Allowlisted ID/label/group validation | Repair structural truth from AI |
| Storage | Version/hash checks and atomic `.graps` persistence | Store secrets or absolute paths |
| Server/API | Safe graph/source/module/flow/scan/settings access | Permit root escape or leak stack/path |
| Frontend | Render graph + optional overlay | Derive hidden edges or treat labels as facts |

## Structural scanning
Normalize scan-root-relative POSIX IDs. Exclude `.graps`, VCS, build/dependency directories, binaries, and credential rules. Capture per-file errors without aborting the project. Retain classes, functions, qualified names, source ranges, imports, call sites, branch markers, routes, and diagnostics where supported.

## Module boundary precedence
- Java/Kotlin: declared package, then directory.
- Go: package/directory.
- Python: package, then folder.
- JavaScript/TypeScript: workspace or `package.json`, then folder.
- Rust: crate/module.
- Other: folder fallback with explicit boundary confidence.
AI may name, summarize, suggest capabilities, merge-view, or group existing module IDs; it cannot define boundaries from zero or hide originals.

## Flow taxonomy
- `call_sequence`: required direct static calls in source order; never marketed as complete execution flow.
- `control_flow`: incremental branch/loop/return structure.
- `request_flow`: incremental route → handler → service/dependency linkage.
- `cross_service_flow`: deferred.
Edges carry `kind`, `confidence`, source location/order, and unresolved reason/candidates. Branches stay non-linear.

## AI enrichment
Per changed module, AI may return only module ID, semantic name, responsibility, capabilities, and `{node_id,label,summary}` flow labels. Instructor + Pydantic shape validation retries about three times; Graps then validates every reference against structural allowlists. No edge/order/member mutation fields exist. Instructor requires explicit approval and exact version pin before installation.

## Storage
`{scan_root}/.graps/` contains `graph.json`, `architecture.json`, `settings.json`, and `cache/`. Files are schema-versioned, deterministically hashed, written atomically, and joined only on matching graph hash. Changed files invalidate affected modules only. `.graps` is excluded before recursion.

## Existing code alignment
- Modify parser modules to retain normalized facts.
- Extend `graph_builder.py` and `resolver.py`; add focused module/flow model layers.
- Add focused storage and enrichment validation modules.
- Extend `server/app.py` additively while preserving protections.
- Let `cli.py` establish scan root and structural readiness.
- Reintroduce a lightweight frontend only after packaging constraints are checked.

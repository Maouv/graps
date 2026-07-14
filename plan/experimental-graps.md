---
id: PROJ-0001
type: project
status: planning
owner: Maou
created: 2026-07-14
updated: 2026-07-14
depends_on: []
related:
  - README.md
  - graps/scanner/graph_builder.py
  - graps/scanner/ast_parser.py
  - graps/scanner/tree_sitter_parser.py
  - graps/server/app.py
  - graps/ai/provider.py
  - graps/ai/cache.py
---

# Experimental Graps — Architecture Explorer Implementation Plan

> **Summary Block:** Rebuild Graps on branch `experimental` as a three-panel code architecture explorer. Its deterministic structural graph—scanner, parser, modules, calls, routes, source ranges, and flow order—is the source of truth; AI is optional enrichment only. The application must remain useful with AI disabled, unavailable, or failing. Done means a scanned project can be explored through `dir-panel`, `workspace`, and `ai-panel`, with source, structural flow, cache, secure API contracts, and verified fallback behavior.

> **Plan status:** Planning only. This document defines the implementation contract; it does not authorize dependency installation, code changes, commit, or push.

---

## §0 — Keputusan Final

| Area | Keputusan |
|---|---|
| Source of truth | Structural analysis owns all IDs, hierarchy boundaries, nodes, edges, call order, branch metadata, and confidence. |
| AI role | AI Enrichment is optional and only supplies names, responsibility, capability suggestions, summaries, and labels mapped to existing structural IDs. |
| AI prohibition | AI must never create/delete structural nodes or edges, change call order, invent relationships, or replace a deterministic module boundary. |
| Core UI | Canonical desktop shell is exactly `dir-panel | workspace | ai-panel`. These panel names must not be renamed. |
| Reserved spaces | Regions marked empty remain literally empty; no placeholder cards, fake analytics, or “coming soon” filler. |
| Click behavior | Folder expands/collapses only. File expands functions and opens its source tab. Module expands contents and opens a module overview tab. Function opens a flow tab, not source. Flow opens its relevant flow tab. |
| Module identity | Folder/package-derived structural module ID is deterministic. Package boundary has language-specific precedence; AI may provide a semantic overlay only. |
| Feature | Not a mandatory hierarchy entity. AI-inferred items such as Login/Register/Refresh Token are optional module capabilities. |
| Flow truth | Use distinct edge/flow types. MVP calls direct static sequence `call_sequence`; it must not be marketed as complete execution/control flow. |
| Branching | Branches, early exits, loops, unresolved/dynamic calls, and confidence are first-class structural metadata—not flattened into a lying linear diagram. |
| Scan behavior | Structural scan always runs and cannot be toggled off. `AI Enrichment` is the separate setting and defaults ON. |
| Cache | Project-local only: `{scan_root}/.graps/`. `.graps` is automatically excluded from scanning. |
| AI failure | AI OFF, no key, invalid output, rate limit, or provider failure falls back to deterministic technical labels; the app remains usable. |
| AI output | Instructor + Pydantic is planned for structured output, then Graps semantic validation. Adding Instructor requires explicit approval and an exact pinned version. |
| Icons | Use selectively vendored SVGs from [microsoft/vscode-codicons](https://github.com/microsoft/vscode-codicons), no runtime CDN or mixed icon library. Existing right split icons remain; the left control mirrors them in CSS/code, not duplicate assets. |
| Responsive model | Tablet/mobile preserve the desktop mental model with drawer/overlay panels, not three skinny columns. Interactive touch targets are at least 44px. |
| UX | Mobile-first implementation, minimal bundle, no heavy UI library unless explicitly approved. |

### §0.1 Visual shell contract

```text
+----------------------+--------------------------------------+----------------------------+
|                      |                                      |                            |
|                      |                                      |  left/right split controls |
+----------------------+--------------------------------------+----------------------------+
|                      |                 tabs +              |                            |
|                      |--------------------------------------|                            |
|                      |                                      |                            |
|      dir-panel       |              workspace               |         ai-panel           |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |  ------------------------  |
|                      |                                      |  | input bar             | |
|                      |                                      |  ------------------------  |
+----------------------+--------------------------------------+----------------------------+
```

### §0.2 Language boundary precedence

| Language/ecosystem | Structural module boundary |
|---|---|
| Java/Kotlin | Declared package, then directory as fallback. |
| Go | Package/directory. |
| Python | Package (`__init__.py` where applicable), then folder. |
| JavaScript/TypeScript | Workspace or `package.json` boundary, then folder. |
| Rust | Crate/module. |
| Other/unknown | Folder fallback with an explicit `boundary_confidence` value. |

---

## §1 — Goal, Scope, dan Non-goals

### §1.1 Goal

Deliver a local-first architecture explorer where a developer can open a project and reliably answer: **what is in this folder/module, what does this function structurally call, where is its source, and what business responsibility may it have when AI is available?**

### §1.2 In scope

1. Deterministic project scan producing a versioned knowledge graph.
2. Folder/package/module/file/function navigation in `dir-panel`.
3. Source, flow, and module overview tabs in `workspace`.
4. `ai-panel` with input bar and status-aware AI interaction.
5. Module inference, direct-call flow, simple branch representation, and route-to-function linkage.
6. Per-project `.graps` storage, incremental scan, graph hashing, and selective re-enrichment.
7. Optional structured AI enrichment with semantic validation and deterministic fallback.
8. Responsive, accessible, locally-vendored-Codicons UI.
9. Secure source/API behavior: path traversal protection, source root enforcement, and no credential source sent to AI.

### §1.3 Non-goals for this implementation

- A guaranteed complete runtime execution graph for dynamic Python/JavaScript.
- Accurate cross-service tracing across arbitrary HTTP, queues, databases, or distributed systems.
- AI-defined project/module boundaries.
- AI-generated structural edges, sequence, nodes, or code modifications.
- A mandatory visual node graph canvas; the first workspace is source/flow/module views.
- Cloud-synced, global cache; storage is project-local only.
- Plugin marketplace, collaboration layer, edits to scanned code, or automatic code fixes.
- Replacing every parser/language at once. Python has first-class flow support; JavaScript/TypeScript follows; other language support degrades honestly.

### §1.4 Definition of Done at project level

- A scan root opens into a stable structural explorer with no AI requirement.
- Every rendered module/file/function/flow maps to a stable structural ID.
- A function tab displays a truthful `call_sequence` or explicitly identifies unresolved/branch conditions.
- AI can enrich labels only after schema and semantic validation; failure never blocks browsing.
- Storage is contained in `{scan_root}/.graps`, excluded from future scans.
- UI works at desktop, tablet, and phone widths without collapsing the three-panel mental model.
- Targeted unit, API, UI, responsive, accessibility, security, cache, and fallback acceptance tests pass.

---

## §2 — Terminologi dan Source of Truth

| Term | Definition | Owner/source of truth |
|---|---|---|
| Scan root | User-selected project directory being analyzed. | CLI/server invocation. |
| Structural graph | Deterministic graph of filesystem, packages, files, classes, functions, imports, calls, routes, and structural flow. | Scanner + parser + graph builder. |
| Architecture map | Validated semantic overlay referencing structural graph IDs. | AI enrichment + semantic validator. |
| Folder | Physical directory from scan root. | Filesystem scan. |
| Package | Language-aware namespace/crate/package boundary. | Parser/resolver. |
| Structural module | Deterministic folder/package candidate with stable ID. | Module resolver. |
| Semantic module view | Optional named/grouped overlay preserving underlying structural modules. | AI enrichment/user override. |
| File | Scan-root-relative source file. | Filesystem + parser. |
| Function | Parsed callable with a stable qualified ID and source range. | Parser. |
| Route | Parsed HTTP route/decorator/handler relationship when support exists. | Parser + route linker. |
| Call site | Parsed invocation in a function body. | Parser. |
| Resolved call | Call site linked to one known function. | Resolver. |
| Unresolved call | Call site that cannot be proved statically. It remains visible with reason/confidence. | Resolver. |
| `call_sequence` | Source-order representation of directly resolved calls for a function. | Flow engine. |
| `control_flow` | Branch/loop/return-aware structure. Incremental capability, never implied by plain sequence. | Flow engine. |
| `request_flow` | Route → handler/controller → service/dependency sequence. | Route/call resolver. |
| Enrichment | AI-owned labels/summaries/capabilities mapping only to structural IDs. | AI adapter + validator. |

### §2.1 Stable identifiers

- File ID: scan-root-relative POSIX path, e.g. `backend/auth/service.py`.
- Function ID: `<file_id>::<qualified_function_name>`, e.g. `backend/auth/service.py::AuthService.login`.
- Structural module ID: canonical language boundary relative to scan root, e.g. `backend/auth`.
- Route ID: `<method> <path> -> <function_id>` or a normalized hash if a route has multiple handlers.
- Flow ID: `<function_id>#call_sequence`, `<function_id>#control_flow`, or `<route_id>#request_flow`.
- IDs are assigned structurally and must never be rewritten by AI.

### §2.2 Truth hierarchy

```text
Filesystem + parser facts
        ↓
Structural graph (graph.json)
        ↓
Validated architecture map (architecture.json; optional)
        ↓
UI rendering
```

If the architecture map is missing, stale, invalid, or unavailable, the UI renders from `graph.json` only.

---

## §3 — Architecture Overview

```text
scan_root
  │
  ├─ filesystem discovery + exclusions
  │       ↓
  ├─ language parser / AST extraction
  │       ↓
  ├─ structural normalization
  │   folders • packages • files • classes • functions • imports
  │   routes • call sites • source ranges • parser diagnostics
  │       ↓
  ├─ graph builder + call resolver + module resolver
  │       ↓
  ├─ structural graph ────────────────► {scan_root}/.graps/graph.json
  │       │                                       │
  │       ├─ flow builder                         ├─ hash/index/cache metadata
  │       │                                       │
  │       └─ UI available now                     │
  │                                               │
  └─ if AI Enrichment ON + provider available ────┘
          ↓ per changed structural module
      Instructor/Pydantic response
          ↓
      Graps semantic validation against graph IDs
          ↓
      architecture map ───────────────► {scan_root}/.graps/architecture.json
          ↓
      semantic labels only in UI
```

### §3.1 Runtime boundaries

| Boundary | Responsibility | Must not do |
|---|---|---|
| `scanner` | Discover, parse, normalize source facts. | Call AI or persist semantic claims. |
| graph/module/flow layer | Construct deterministic graph and resolve what can be proved. | Guess dynamic calls as resolved. |
| AI layer | Request, validate syntactic schema, retry, cache AI result. | Alter graph structure. |
| semantic validator | Reject unknown/duplicate/malformed AI references. | Repair structural data based on AI. |
| server/API | Expose scan, graph, source, settings, enrichment status safely. | Leak absolute paths or allow source-root escape. |
| frontend | Render deterministic graph plus optional overlay. | Derive hidden structural edges or treat AI labels as facts. |

### §3.2 Existing code alignment

- `graps/scanner/ast_parser.py` and `graps/scanner/tree_sitter_parser.py` already parse language syntax and need normalized metadata retention.
- `graps/scanner/graph_builder.py` is the primary extension point; current graph construction must retain source ranges/classes and grow calls/routes/modules rather than discard parser facts.
- `graps/scanner/resolver.py` is the import/edge-resolution base; call resolution must be explicit about confidence.
- `graps/server/app.py` already has graph/source/chat primitives and security guards; it must evolve contracts without breaking source root/path traversal protections.
- `graps/ai/provider.py` and `graps/ai/cache.py` are the provider/cache seam; structured enrichment belongs here or in focused sibling modules, not in scanner code.
- `graps/cli.py` owns scan-root setup and should initiate structural scan before serving UI.

---

## §4 — Data Model dan Schema

All serialized schemas require a top-level `schema_version` and deterministic ordering before hashing/writing. Unknown fields in AI payloads are rejected or ignored intentionally by Pydantic configuration; no implicit acceptance.

### §4.1 `graph.json` — structural truth

```json
{
  "schema_version": 1,
  "scan": {
    "root_id": ".",
    "scanned_at": "2026-07-14T12:00:00Z",
    "content_hash": "sha256:...",
    "languages": {"python": 12},
    "diagnostics": []
  },
  "nodes": {
    "folders": [],
    "packages": [],
    "modules": [],
    "files": [],
    "classes": [],
    "functions": [],
    "routes": []
  },
  "edges": {
    "contains": [],
    "imports": [],
    "calls": [],
    "route_handlers": []
  },
  "flows": []
}
```

### §4.2 Structural entity minimum fields

| Entity | Required fields |
|---|---|
| Folder | `id`, `parent_id`, `name`, `path`, `kind: "folder"` |
| Package | `id`, `path`, `language`, `boundary_kind`, `confidence` |
| Module | `id`, `path`, `kind: "module"`, `source: "package"|"folder"`, `members`, `boundary_confidence` |
| File | `id`, `parent_id`, `path`, `language`, `content_hash`, `line_count` |
| Class | `id`, `file_id`, `name`, `qualified_name`, `line_start`, `line_end` |
| Function | `id`, `file_id`, `class_id?`, `name`, `qualified_name`, `line_start`, `line_end`, `params`, `returns?`, `decorators`, `callsites` |
| Route | `id`, `method`, `path`, `handler_id`, `source_location`, `confidence` |
| Edge | `id`, `source`, `target?`, `kind`, `confidence`, `source_location`, `reason?` |
| Flow | `id`, `kind`, `root_id`, `nodes`, `edges`, `diagnostics` |

### §4.3 Call and flow schema

```json
{
  "id": "backend/auth/service.py::login#call_sequence",
  "kind": "call_sequence",
  "root_id": "backend/auth/service.py::login",
  "nodes": [
    {"id": "backend/auth/service.py::login", "kind": "entry", "source_order": 0},
    {"id": "backend/auth/service.py::verify_password", "kind": "function", "source_order": 1},
    {"id": "backend/auth/service.py::create_token", "kind": "function", "source_order": 2}
  ],
  "edges": [
    {
      "source": "backend/auth/service.py::login",
      "target": "backend/auth/service.py::verify_password",
      "kind": "direct_call",
      "confidence": "resolved",
      "source_order": 1
    },
    {
      "source": "backend/auth/service.py::login",
      "target": null,
      "kind": "dynamic_call",
      "confidence": "unresolved",
      "reason": "indexed dispatch expression"
    }
  ],
  "diagnostics": []
}
```

For conditionals, preserve branch node/edge metadata. Example: `condition_true`, `condition_false`, `early_return`, `loop_body`. The UI may initially render an honest simplified branch representation, but it must not turn a branch into a linear sequence.

### §4.4 `architecture.json` — validated semantic overlay

```json
{
  "schema_version": 1,
  "graph_content_hash": "sha256:...",
  "enriched_at": "2026-07-14T12:00:00Z",
  "modules": [
    {
      "module_id": "backend/auth",
      "name": "Authentication",
      "responsibility": "Handles user identity and session creation",
      "capabilities": ["Login", "Register", "Refresh Token"],
      "flow_labels": [
        {
          "node_id": "backend/auth/service.py::login",
          "label": "Authenticate User",
          "summary": "Authenticates a submitted user identity"
        }
      ]
    }
  ],
  "semantic_groups": []
}
```

Rules:

- `module_id` must exist in `graph.json`.
- Capability is metadata only; it is never a structural hierarchy node.
- Each `flow_labels[].node_id` must exist in the specified structural flow.
- AI returns no edges, positions, source order, or structural member list.
- Semantic groups can reference module IDs but cannot remove/reparent structural module nodes.

### §4.5 `settings.json`

```json
{
  "schema_version": 1,
  "ai_enrichment": true,
  "module_overrides": {},
  "semantic_group_overrides": {},
  "ui": {
    "left_panel_width": 288,
    "right_panel_width": 336,
    "tabs": []
  }
}
```

UI state is preference data, not structural truth. Invalid/missing settings receive safe defaults.

---

## §5 — Structural Scanner

### §5.1 Discovery

1. Accept only an explicit scan root from CLI/API flow.
2. Normalize paths to relative POSIX IDs; never serialize absolute host paths.
3. Exclude `.graps`, VCS folders, configured ignores, build outputs, dependency directories, binary files, and hidden credential rules where applicable.
4. Record scanner/parser diagnostics per file without failing a whole project for one malformed source file.
5. Hash source/metadata deterministically to identify changed files and affected modules.

### §5.2 Parser extraction contract

For every supported language parser, normalize these when available:

- File language and encoding/error diagnostics.
- Imports/exports with locations.
- Classes, nested classes, functions, methods, async functions, and qualified names.
- Accurate `line_start` and `line_end`.
- Parameters, return annotations/type where parseable, decorators/annotations/comments where supported.
- Direct call sites in source order.
- Branch/conditional/loop/return structural markers for the MVP language subset.
- HTTP route declarations/handler references where framework patterns are supported.

### §5.3 Python-first implementation boundary

| Iteration | Supported behavior |
|---|---|
| First | Python functions/methods, direct local/imported calls, source ranges, source-order sequence. |
| Next | Simple Python `if`/`else`, `return`, and route decorator → handler linkage. |
| Then | JavaScript/TypeScript direct calls and common exported handlers. |
| Later | Go/Rust/Java/Kotlin expansion when parser facts and resolver confidence support it. |

### §5.4 Error handling

- Syntax errors create a file diagnostic and leave known filesystem/file data visible.
- Unsupported syntax/language creates no invented function/edge.
- Dynamic dispatch/import/reflection becomes an unresolved node/edge with a reason.
- A parser exception is captured at file boundary and never corrupts cached graph JSON.

---

## §6 — Module Resolution

### §6.1 Deterministic structural module candidates

1. Build folder and package nodes first.
2. Apply §0.2 language precedence to select a canonical structural boundary.
3. Assign module ID from canonical scan-root-relative path/package.
4. Attach contained folders/files/functions through structural `contains` edges.
5. Keep every original folder/package accessible in the explorer even when it belongs to a semantic group.

Example:

```json
{
  "id": "backend/auth",
  "kind": "module",
  "source": "folder",
  "path": "backend/auth",
  "members": ["backend/auth/controller.py", "backend/auth/service.py"],
  "boundary_confidence": "resolved"
}
```

### §6.2 Optional semantic grouping

AI may suggest a semantic view:

```json
{
  "id": "semantic:authentication",
  "name": "Authentication",
  "members": ["backend/auth", "shared/jwt"],
  "source": "ai",
  "structural_boundaries_preserved": true
}
```

The original `backend/auth` and `shared/jwt` nodes remain visible. User overrides in `settings.json` take precedence over AI suggestions and must not mutate `graph.json`.

### §6.3 Module overview data

A module tab may present:

- Structural path, language/package boundary, member files, public functions, imports/exports, routes, and diagnostics.
- Optional semantic name, responsibility, and capability list.
- AI status: enriched, structural fallback, stale overlay, disabled, or unavailable.

---

## §7 — Hybrid Flow Engine

### §7.1 Flow taxonomy

| Flow kind | MVP status | Meaning |
|---|---|---|
| `call_sequence` | Required | Source-order sequence of direct statically resolved calls from a function. |
| `control_flow` | Incremental | Branch/loop/return-aware structural graph. |
| `request_flow` | Incremental | Route → handler → service/dependency chain. |
| `cross_service_flow` | Deferred | HTTP/event/queue/database tracing across services. |

### §7.2 Resolution rules

- Direct invocation with one known target: `kind: direct_call`, `confidence: resolved`.
- Invocation with multiple static candidates: `kind: ambiguous_call`, `confidence: partial`, include candidates and reason.
- Indexed handler, reflection, monkey patching, dynamic import, or unknown external callable: `kind: dynamic_call`, `confidence: unresolved`.
- Unresolved data must remain visible in the flow/overview, not silently disappear.
- Preserve source order only within a lexical execution region; branch paths carry their own ordering.

### §7.3 Visual rules

- Function click opens a flow tab named after the function.
- The flow tab renders structural edges first, then substitutes semantic labels if a valid mapping exists.
- Branch decision nodes visually split true/false paths; never flatten them as sequential calls.
- Node details link to source function/file tabs.
- A visible badge/legend identifies `resolved`, `partial`, and `unresolved` edges.
- The tab calls itself **Call sequence** unless branch/loop analysis supports a true control-flow view.

### §7.4 AI label overlay

```json
{
  "node_id": "backend/auth/service.py::create_token",
  "label": "Generate Access Token",
  "summary": "Creates a signed token for the authenticated user"
}
```

The renderer uses `label ?? technical_name`; it never uses AI output to determine which node comes next.

---

## §8 — AI Enrichment

### §8.1 Input scope

- Enrich one changed structural module at a time.
- Send compact graph metadata and narrowly necessary source summaries only; do not send the whole project by default.
- Preserve existing credential-file exclusions and source token budgeting.
- Include only valid module/node IDs as an allowlist in the prompt context.

### §8.2 Output contract

Planned Pydantic model fields:

```text
ModuleEnrichment
  module_id: str
  name: str
  responsibility: str
  capabilities: list[str]
  flow_labels: list[FlowLabel]

FlowLabel
  node_id: str
  label: str
  summary: str | None
```

No edge field, ordering field, function creation field, or node deletion field exists in the output model. A model cannot populate a field that is absent. Nice little cage, no larp.

### §8.3 Two-stage validation

1. **Instructor + Pydantic validation**: JSON shape, field types, length limits, and retry up to three attempts for malformed structured output.
2. **Graps semantic validation**: module/node IDs exist, IDs are unique, labels are non-empty and bounded, all labels refer to allowed module flow nodes, and semantic group members refer to existing modules.

Rejected enrichment is not partially written. Preserve the last architecture map only when its `graph_content_hash` still matches; otherwise render structural fallback.

### §8.4 Failure matrix

| Condition | Structural graph | Architecture map/UI |
|---|---|---|
| AI ON + provider works | Scan/update normally. | Enrich changed modules; show semantic labels. |
| AI OFF | Scan/update normally. | Technical labels and folder/package names. |
| No API key/provider | Scan/update normally. | Status `unavailable`; technical fallback. |
| Invalid AI JSON after retry | Scan/update normally. | Status `failed`; technical fallback. |
| Semantic validation failure | Scan/update normally. | Reject payload; technical fallback. |
| Provider/network/rate failure | Scan/update normally. | Preserve compatible old overlay or technical fallback. |

### §8.5 Dependency gate

Instructor is not currently authorized for installation. Before implementation that adds it:

1. Present the exact package name and pinned version.
2. State why existing provider code cannot safely provide the same schema/retry behavior.
3. Obtain explicit approval.
4. Update `pyproject.toml` and lock/package metadata only after approval.

---

## §9 — Storage dan Cache

```text
{scan_root}/.graps/
├── graph.json             # structural truth
├── architecture.json      # validated semantic overlay
├── settings.json          # project settings and user overrides
└── cache/
    ├── scan-index.json    # content hashes / affected-module index
    └── enrichment/        # internal provider-safe cache entries
```

### §9.1 Cache behavior

| Trigger | Structural operation | AI operation |
|---|---|---|
| First project open | Full structural scan. | Enrich each eligible module if ON. |
| Unchanged project | Load graph/cache. | Load compatible architecture map/cache. |
| File changes | Reparse affected files and rebuild impacted graph/module data. | Re-enrich only affected modules if ON. |
| Settings toggles AI OFF | No structural rescan required unless source changed. | Hide/skip enrichment; retain data safely but do not render it as active. |
| Manual `/scan` | Explicit refresh; full or targeted according to command options. | Re-enrich affected/full scope if ON. |

### §9.2 Write safety

- Generate complete temporary JSON then atomically replace target file.
- Store `graph_content_hash` in architecture output; never join mismatched graph/overlay.
- Version schema files; incompatible versions trigger controlled rebuild/fallback.
- `.graps` is hard-excluded before recursive discovery to prevent self-analysis recursion.
- Cache keys must not contain raw provider secrets or absolute system paths.

---

## §10 — Settings dan Scan Behavior

### §10.1 Settings

| Setting | Default | Effect |
|---|---|---|
| AI Enrichment | ON | Enables semantic enrichment only; never disables structural scanning. |
| Panel sizes | Stable defaults | Persists user widths within safe min/max bounds. |
| Module overrides | Empty | User semantic labels/grouping override AI overlay only. |
| Tab/session state | Empty | Persists pinned/open tabs without treating them as graph state. |

### §10.2 Scan UX

- Project opening triggers structural readiness first.
- UI shows `Scanning structure`, `Structure ready`, `Enriching modules`, `AI unavailable`, or `Enrichment failed—using structural labels` as appropriate.
- `/scan` in `ai-panel` is a manual convenience command, not the normal way data appears.
- Planned command variants: `/scan`, `/scan --full`, `/scan --no-ai`; parser/UX must show invalid command help rather than silently ignore it.
- AI status messages never block tree, source, module, or structural flow interactions.

### §10.3 No-key and failure UX

Use a concise passive status in `ai-panel`; do not show a destructive modal or force configuration. The user can continue with technical labels like `backend/auth`, `login()`, and `create_token()`.

---

## §11 — Backend dan API Contracts

Existing API behavior must remain backward-compatible where possible; new endpoints are additive or explicitly versioned. All paths are scan-root-relative, normalized, and checked against path traversal.

| Endpoint | Purpose | Minimum response/behavior |
|---|---|---|
| `GET /api/graph` | Structural graph for explorer. | Versioned structural graph only or graph plus clearly separated enrichment status. |
| `GET /api/source?file=&fn=` | Source file/function. | Existing secure behavior retained; returns file/function source, language, and no absolute path. |
| `GET /api/modules/{module_id}` | Module overview. | Structural module + optional validated enrichment + status. |
| `GET /api/flows/{flow_id}` | Function/route flow. | Structural flow plus optional label mapping; unresolved diagnostics retained. |
| `GET /api/scan/status` | Initial/incremental scan state. | State, graph hash, changed modules, diagnostics summary, AI state. |
| `POST /api/scan` | Manual scan request. | Validated mode (`default`, `full`, `no_ai`); structural result even if AI fails. |
| `GET /api/settings` | Project settings. | AI setting and UI preference state with defaults. |
| `PUT /api/settings` | Persist allowed project settings. | Whitelist/validate fields; no arbitrary filesystem paths. |
| `POST /api/ai/chat` | Existing conversational input. | Preserve origin/security controls and graph-aware source context restrictions. |

### §11.1 API error semantics

- Invalid relative path/module/flow ID: `400` or `404`, never server stack detail.
- Scan parser failure: HTTP request succeeds if graph can be produced; include per-file diagnostics.
- AI unavailable/failure: scan/source/graph still succeeds; status conveys fallback.
- Invalid settings payload: `422` with field validation details.
- Mutating requests retain existing origin/host controls for loopback binding.

### §11.2 Source security invariants

- Do not expose scan-root absolute path.
- Resolve requested file and require it to remain under scan root.
- Credential files remain excluded from AI context.
- Do not introduce write/edit endpoints in this scope.

---

## §12 — Frontend Layout dan Interaction

### §12.1 Application shell

- Desktop: `dir-panel | workspace | ai-panel` with draggable separators and stable min/max widths.
- Split control indicates panel state using the existing custom selected/unselected assets.
- Left `dir-panel` uses the mirrored right split asset through CSS transform; do not create a duplicate SVG.
- Closing a panel expands `workspace`; reopening restores the previous width when valid.
- Empty top/side regions remain empty by contract.

### §12.2 `dir-panel` explorer

```text
(project) Project Name
├── (folder/package) backend
│   └── (module) auth
│       ├── (file) service.py
│       │   ├── (function) login()
│       │   └── (function) create_token()
│       └── (route) POST /login
└── (folder) frontend
```

Interaction rules:

1. Folder/package click: expand/collapse only; no workspace tab.
2. File click: expand function children and open/deduplicate its source tab.
3. Module click: expand contents and open/deduplicate module overview tab.
4. Function click: open/deduplicate flow tab.
5. Flow/route click: open/deduplicate its relevant flow tab.
6. Keyboard supports tree navigation, expand/collapse, and open actions.

### §12.3 `workspace`

Supported tab types:

| Tab | Content |
|---|---|
| Source | Syntax-highlightable source, language, source range/function focus, links to flow. |
| Flow | Structural call/control/request flow with confidence legend, semantic labels when valid, and source links. |
| Module | Structural members/routes/dependencies plus optional responsibility/capabilities. |

VS Code-like lifecycle:

- Single click opens/reuses a preview tab when safe.
- Double click or explicit pin creates a persistent tab.
- A dirty/modified tab concept is reserved only if the application later gains editing; current read-only tabs are never falsely marked dirty.
- Tabs deduplicate by stable entity/flow ID, close individually, support overflow, and restore safe persisted state.

### §12.4 `ai-panel`

First scope is intentionally small:

- Status line for scan/enrichment state.
- Input bar for normal chat and `/scan` commands.
- No invented dashboard widgets, activity feed, or capabilities panel before a decision exists.
- Chat can cite selected file/function context under existing source/credential safeguards.

### §12.5 Responsive behavior

| Width/mode | `dir-panel` | `workspace` | `ai-panel` |
|---|---|---|---|
| Desktop | Persistent/resizable. | Primary center region. | Persistent/resizable. |
| Tablet | Toggleable overlay/drawer. | Full remaining width. | Toggleable overlay/drawer. |
| Phone | Full-height drawer; one panel at a time. | Full width. | Full-height/bottom-sheet-like overlay; one panel at a time. |

The mobile layout uses the same tree, tabs, and panel identities—only their presentation changes. No drag-and-drop is required; all important actions are tap accessible.

---

## §13 — Design System

### §13.1 Tokens

| Token | Value/use |
|---|---|
| Workspace background | `#181818` |
| `dir-panel` / `ai-panel` background | `#1F1F1F` |
| Text/stroke/border | `#E4E4E4` |
| Box/input background | `#404040` |
| Border | `1px solid` using tokenized border color |
| XS radius | `4px` |
| SM radius | `6px` |
| MD radius | `8px` |
| LG radius | `12px` |
| XL radius | `16px` |
| Pill/full radius | `9999px` |

### §13.2 Icon policy

- Vendor only consumed Codicons SVG assets into `graps/public/icon/`.
- Add license/attribution material required by Codicons' license.
- Use CSS `currentColor` or equivalent tokenized styling where the SVG supports it.
- No Font Awesome, Lucide, Material icons, emoji-as-control, or CDN icon loads.
- Existing `split-horizontal-right-select.svg` and `split-horizontal-right-unselect.svg` remain the panel controls.
- Every icon-only control has `aria-label`, focus visibility, keyboard behavior, and a 44px minimum target on touch layouts.

### §13.3 Accessibility

- Semantic tree/list/tab roles, `aria-expanded`, selected/active tab state, and logical focus order.
- Visible keyboard focus; do not rely on color alone for resolved/partial/unresolved flow state.
- Text contrast validated against dark surfaces.
- Respect reduced-motion preferences for panel/tab transitions.

---

## §14 — Per-file Change Map

This is a planned map, not permission to edit. Names marked **new** are proposed so work stays isolated instead of stuffing every responsibility into current files.

| Path | Action | Responsibility |
|---|---|---|
| `graps/scanner/ast_parser.py` | Modify | Retain/normalize source ranges, classes, call sites, branch markers where parser supports them. |
| `graps/scanner/tree_sitter_parser.py` | Modify | Expose equivalent cross-language parser facts and diagnostics. |
| `graps/scanner/graph_builder.py` | Modify | Build versioned structural graph; retain metadata instead of dropping it; construct nodes/edges. |
| `graps/scanner/resolver.py` | Modify | Resolve imports/calls with explicit confidence and unresolved reasons. |
| `graps/scanner/module_resolver.py` | **New** | Deterministic package/folder module boundary inference. |
| `graps/scanner/flow_builder.py` | **New** | `call_sequence`, incremental branch/control metadata, and route flow assembly. |
| `graps/scanner/models.py` | **New** or focused existing module | Typed structural schema/dataclasses/Pydantic models after codebase style review. |
| `graps/scanner/__init__.py` | Modify | Export only deliberate public scanner contracts. |
| `graps/storage.py` | **New** | Atomic `.graps` graph/architecture/settings reads, writes, schema versioning, hashes. |
| `graps/ai/provider.py` | Modify | Keep provider selection; add enrichment invocation seam without scanner coupling. |
| `graps/ai/enrichment.py` | **New** | Instructor/Pydantic request/output models after dependency approval. |
| `graps/ai/validation.py` | **New** | Semantic validation against structural graph IDs/flow nodes. |
| `graps/ai/cache.py` | Modify | Project-local, hash-aware enrichment cache behavior. |
| `graps/server/app.py` | Modify | Additive scan/module/flow/settings endpoints; preserve host/origin/path protections. |
| `graps/cli.py` | Modify | Structural scan initialization, scan root, serving orchestration, scan command options. |
| `graps/frontend/` | **New/reintroduced** | New lightweight frontend from scratch; exact file layout decided during UI implementation without adding unapproved dependencies. |
| `graps/public/icon/` | Modify | Keep split assets; add only used vendored Codicons + license notice. |
| `pyproject.toml` | Modify only after approval | Exact pinned Instructor dependency and package/static asset config if required. |
| `tests/test_ast_parser.py` | Modify | Parser facts/source ranges/calls/branches coverage. |
| `tests/test_tree_sitter_parser.py` | Modify | Cross-language normalized extraction coverage. |
| `tests/test_graph_builder.py` | Modify | Structural graph nodes/edges/schema determinism. |
| `tests/test_resolver.py` | Modify | Resolved/partial/unresolved call confidence coverage. |
| `tests/test_cache.py` | Modify | Hash compatibility, incremental cache, atomic write fallback. |
| `tests/test_provider.py` | Modify | Provider availability/error behavior. |
| `tests/test_api.py` | Modify | New endpoints, status/error behavior, traversal/origin regression coverage. |
| `tests/test_module_resolver.py` | **New** | Language boundary and deterministic module IDs. |
| `tests/test_flow_builder.py` | **New** | Call sequence, branch and unresolved flow assertions. |
| `tests/test_enrichment_validation.py` | **New** | AI schema/semantic rejection and structural fallback. |
| `tests/test_storage.py` | **New** | `.graps` schema/version/atomic persistence. |
| `tests/fixtures/` | Modify/add | Minimal Python/JS/TS route, call, branch, dynamic-dispatch fixtures. |
| Frontend component/e2e tests | **New when frontend exists** | Explorer, tabs, responsive drawers, keyboard/a11y behavior. |

### §14.1 Files deliberately out of scope

- `BLUEPRINT.md` is historical reference, not the controlling plan for this experimental branch.
- Existing unrelated edge/lazy-render plans and issue documents stay untouched.
- No source-code write/edit API is introduced.

---

## §15 — Implementation Phases

The 20 capabilities are dependency-grouped into four phases. They are **not** 20 single engineering tasks; implementation should produce roughly 30–40 small, testable tasks ordered below.

### Phase 1 — Foundation

**Outcome:** A versioned, cacheable structural graph exists without AI or UI.

1. Define schema version and deterministic structural entity/edge models.
2. Add scan-root exclusions including `.graps` and stable relative ID normalization.
3. Preserve parser metadata already available: functions, classes, language, accurate source ranges, imports/call sites.
4. Extend graph builder to emit folders/packages/files/classes/functions/import edges instead of lossy file-only data.
5. Implement deterministic module resolver with language precedence.
6. Implement project-local storage, graph hashing, atomic write, and changed-file/module index.
7. Add tests for graph determinism, syntax-error resilience, exclusions, module boundaries, and cache invalidation.

**Phase gate:** `graph.json` can be built/read for a Python fixture project without any AI provider; `.graps` never appears as a scanned node.

### Phase 2 — Intelligence

**Outcome:** Structural flows and optional semantic overlay work without compromising truth.

1. Normalize Python direct call sites and resolve direct calls with confidence/reason fields.
2. Build `call_sequence` flow objects in source order.
3. Add simple conditional/return branch nodes; label unsupported constructs honestly.
4. Link supported route decorator declarations to handlers, then assemble initial `request_flow`.
5. Define AI enrichment Pydantic models and semantic validator tests.
6. Request explicit approval before adding pinned Instructor dependency.
7. Implement per-module enrichment, retry, semantic validation, and architecture-map persistence.
8. Implement all OFF/no-key/invalid/rate/provider-failure fallback states.
9. Expand JS/TS only after Python contracts and test suite are stable.

**Phase gate:** A function flow shows resolved and unresolved edges truthfully; invalid AI output cannot change graph JSON and cannot stop structural browsing.

### Phase 3 — Application UI

**Outcome:** The user can navigate, inspect, and understand the structural graph through the required shell.

1. Reintroduce frontend infrastructure with no unapproved dependency; decide static ES module/TypeScript build approach only after checking packaging constraints.
2. Implement canonical shell, panel state, custom split controls, CSS mirroring for the left control, and width persistence.
3. Implement keyboard-accessible `dir-panel` tree from structural graph.
4. Implement source, flow, and module overview workspace tabs with stable-ID deduplication.
5. Implement flow confidence/branch rendering and semantic label fallback.
6. Implement minimal `ai-panel`: status + chat/`/scan` input.
7. Vendor only used Codicons and include attribution/license assets.
8. Implement desktop/tablet/mobile drawer/overlay behavior and touch target requirements.

**Phase gate:** With AI disabled, user can click file/function/module and get the exact defined tab behavior at desktop and mobile widths.

### Phase 4 — Hardening

**Outcome:** The application is robust, secure, accessible, packageable, and release-ready.

1. Add scan/status/settings API contracts and input validation.
2. Verify all source traversal, credential-context, origin/host, and scan-root boundary protections.
3. Add tab persistence/overflow and invalid-state recovery.
4. Add accessibility/keyboard/reduced-motion/contrast tests.
5. Add responsive interaction tests for overlay panels and touch behavior.
6. Add performance measurements for scan/cached-load budgets on representative fixture projects.
7. Add migration/schema-version tests for stale graph/architecture cache.
8. Update README/docs only after behavior is real and exercised.
9. Run targeted then full relevant validation; record known parser limitations honestly.

**Phase gate:** Acceptance criteria in §16 are green; no feature claims full runtime control flow where only static sequence is implemented.

### §15.1 Dependency ordering

```text
schema + scanner + graph + storage
                 ↓
module resolver + call resolver + flow engine
                 ↓
semantic validation + optional AI enrichment
                 ↓
API contracts
                 ↓
three-panel UI + interactions
                 ↓
responsive/accessibility/security/performance hardening
```

### §15.2 Commit discipline when execution is authorized

- One coherent tested change per commit; do not mix frontend deletion/recreation, scanner schema, AI dependency, and unrelated fixes.
- Stage exact files, not `git add .`.
- Never commit/push unless the user explicitly asks in that execution turn.
- Any new dependency uses an exact pinned version and needs approval first.

---

## §16 — Tests dan Acceptance Criteria

### §16.1 Test matrix

| Area | Required evidence |
|---|---|
| Scanner | Exclusions, malformed source survival, stable relative IDs, correct source ranges, changed-file detection. |
| Graph | Deterministic serialized output, node/edge integrity, module boundary precedence, no `.graps` recursion. |
| Resolver/flow | Direct calls resolved, dynamic calls unresolved, branch paths non-linear, route linkage only when proven. |
| Storage | Atomic write behavior, graph/architecture hash matching, stale schema fallback, settings defaults. |
| AI | Pydantic malformed-response retry, unknown ID rejection, duplicate/oversize label rejection, no edge/order injection. |
| API | Graph/source/module/flow/status/settings behavior, traversal defense, missing IDs, AI failure not blocking scan. |
| UI | Exact click behaviors, stable tab deduplication, panel open/close/resize, empty slots remain empty. |
| Responsive/a11y | Tablet/mobile overlays, 44px targets, tree/tab keyboard behavior, aria state, visible focus. |
| Regression | Existing scanner, resolver, cache, provider, CLI, and API tests remain passing. |

### §16.2 Acceptance checklist

- [ ] Structural scan runs when a project opens without any AI key/provider.
- [ ] Graph contains stable folder/package/module/file/function IDs and source ranges.
- [ ] `.graps` is excluded from discovery and survives repeated scans without recursive growth.
- [ ] File click expands function hierarchy and opens source; function click opens flow, not source.
- [ ] Module click expands contents and opens a module overview.
- [ ] A direct call flow is labeled `call_sequence`; unresolved/dynamic calls visibly retain uncertainty.
- [ ] Conditional flow is not falsely rendered as a straight-line sequence.
- [ ] AI OFF/no key/provider failure leaves all structural browsing usable with technical labels.
- [ ] Valid AI label references only existing structural IDs; invalid enrichment is rejected atomically.
- [ ] AI cannot introduce/delete/reorder structural flow nodes or edges.
- [ ] `graph.json`, `architecture.json`, and `settings.json` live only under `{scan_root}/.graps`.
- [ ] `dir-panel`, `workspace`, and `ai-panel` names and canonical relationship remain unchanged.
- [ ] Empty reserved layout slots contain no placeholder product UI.
- [ ] Desktop panels resize; tablet/mobile use accessible drawers/overlays rather than squeezed columns.
- [ ] Only custom split assets and selectively vendored VS Code Codicons are used for controls.
- [ ] Icon controls expose aria labels and touch layouts meet the 44px target.
- [ ] Source endpoint rejects traversal and does not expose absolute scan-root paths.
- [ ] Targeted tests pass before broader regression suite is claimed green.

## Mandatory Review Section

### Potential Bugs

- Parser differences can produce inconsistent qualified names/source ranges across languages.
- Preview-tab lifecycle can accidentally replace a pinned tab if state is not modeled separately.
- Stale architecture overlay can display labels for changed graph IDs if hash checks are skipped.

### Known Risks

- Static analysis of Python/JS cannot resolve all dynamic calls; overstating confidence would mislead users.
- Adding Instructor expands dependency surface and must wait for explicit approval.
- Reintroducing a frontend after prior deletion can reintroduce stale packaging/static-mount coupling if phased carelessly.
- Large repositories may expose scan latency/memory costs that fixtures do not reveal.

### Edge Cases

- Nested functions/classes, duplicate simple function names, decorated async functions, syntax errors, generated files, symlinks, binary files, Unicode paths, and ignored folders.
- Multiple possible call targets, dynamic dispatch, callbacks, reflection, and imported aliases.
- A module with no functions, a flow with zero resolved calls, or a project with AI enabled but no available provider.
- Screen rotation, narrow mobile width, persisted panel widths outside current viewport, and restored tabs for deleted files.

### Failure Cases

- Scanner/parser crashes for one file.
- Atomic graph/architecture write interrupted.
- Provider returns invalid JSON, valid JSON with invented IDs, rate limit, timeout, or missing SDK/key.
- API receives traversal paths, invalid IDs, malformed settings, or forbidden-origin requests.

### Negative Test Cases

- AI payload references unknown module/function/flow node IDs.
- AI payload attempts duplicate labels or sends an edge/order field.
- A dynamic call is incorrectly claimed resolved.
- `.graps/graph.json` appears in scan results.
- Mobile UI renders three compressed simultaneous columns.
- Function click opens source instead of a flow tab.

### Regression Risk

- Existing graph/API tests may rely on older flat node dictionaries and current `GET /api/graph` response shape.
- Existing AI chat context and source endpoint behaviors must remain secure after graph schema expansion.
- CLI default scan/cache paths may rely on current assumptions; project-local behavior needs explicit migration coverage.

### Rollback Plan

- Keep schema versioned; unsupported/new graph data falls back to last compatible graph or a clean rescan.
- Feature-flag AI enrichment through project settings; disable enrichment without disabling structural exploration.
- Keep API additions additive until an explicit versioned breaking-change decision.
- Revert individual coherent commits; do not roll back via destructive reset unless explicitly authorized.

### Validation Checklist

- [ ] `git diff --check` passes after each implementation slice.
- [ ] Targeted scanner/resolver/storage/enrichment tests pass for the touched behavior.
- [ ] API tests cover error and fallback states, not only happy paths.
- [ ] UI behavior is manually smoke-tested at desktop, tablet, and phone widths.
- [ ] Project-local cache output is inspected and contains no absolute path or secret.
- [ ] Full relevant test suite runs once dependencies are available and approved.

### Review Checklist

- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist

- [ ] Every §16.2 criterion has a corresponding automated test, manual smoke evidence, or explicit justified limitation.
- [ ] No planned dependency was installed without explicit approval.
- [ ] No claim of full control/execution flow is made unless the implemented engine proves branch/loop/return handling.

### User Testing Result

- Not started — planning artifact only.

### Post Implementation Review

- Not started — complete after Phase 4 acceptance is met.

### Lessons Learned

- To be recorded during execution; do not retroactively invent outcomes.

### Future Improvement

- Cross-service HTTP/event/database tracing.
- Additional language-specific route/framework resolvers.
- User-editable semantic annotations with provenance/audit history.
- Visual graph canvas only after source/flow/module navigation proves sufficient and stable.

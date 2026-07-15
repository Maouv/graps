---
id: TASK-0001
type: task
status: done
owner: Maou
created: 2026-07-14
updated: 2026-07-15
depends_on: []
related: [FEAT-0016, FEAT-0017, FEAT-0018, FEAT-0020]
---

# Phase 1 — Foundation

> **Summary Block:** Create deterministic schema, scanner retention, graph construction, module resolution, and project-local storage. Phase gate: A Python fixture produces reusable `graph.json` without AI; `.graps` never appears as a node.

## 1. Lifecycle

### 1. Idea

- Captured in project discovery; feature-specific validation remains open.

### 2. Research

- Captured in project discovery; feature-specific validation remains open.

### 3. Analysis

- Captured in project discovery; feature-specific validation remains open.

### 4. Requirement

- Defined in linked features (FEAT-0016, 0017, 0018, 0020). Approved.

### 5. Planning

- Planning complete. WBS in `03-planning/`. Dependency order: TASK-0001 → TASK-0002 → TASK-0003 → TASK-0004.

### 6. Design

- Design contracts in `04-design-architecture/`. Scanner, graph, storage, API security designs followed.

### 7. Architecture

- Architecture contracts followed. Structural analysis as SSoT, AI as optional enrichment. pathlib throughout, no OS-specific paths.

### 8. Implementation

- Complete (2026-07-14). Scanner (ast_parser, tree_sitter_parser, graph_builder, ids, modules, resolver, risk_analyzer, sanitize, flows), storage.py, server/app.py, cli.py. 4146 lines total. Commit `6f9fb85` (structural graph API + persistence), `26794ec` (foundation evidence recorded).

### 9. Self Review

- Complete (2026-07-15). Execution checklist 4/4 verified. Schema versioning (`schema_version: "1.0.0"`), stable scan-root-relative IDs, `.graps` exclusion, atomic storage writes all implemented. 78 foundation tests pass.

### 10. AI Review

- Complete (2026-07-15). Code follows deterministic-first principle. No dead code. pathlib throughout. Scanner dispatch: AST-first for `.py` (BUG-0001 fix), tree-sitter for non-Python. ruff+mypy clean.

### 11. Code Review

- Complete (2026-07-15). DRY — scanner dispatch shared between CLI and server. Storage uses atomic writes with hash compatibility check. No magic numbers. Consistent error handling — per-file failure doesn't abort scan.

### 12. Testing

- Complete (2026-07-15). 78 foundation tests: `test_ast_parser.py`, `test_graph_builder.py`, `test_resolver.py`, `test_cache.py`, `test_risk_analyzer.py`, `test_cli_dispatch.py`. 181 total tests pass (including downstream TASK-0002/0003/0004 tests).

### 13. QA

- Complete (2026-07-15). 181/181 pass, ruff clean, mypy clean, `git diff --check` clean. `pos.py validate` 0 errors.

### 14. Potential Bug Review

- Complete (2026-07-15). BUG-0001 (TreeSitter call extraction gap) found and fixed (commit `b323f3f`). AST-first dispatch for `.py` files, tree-sitter for non-Python. Test coverage in `test_cli_dispatch.py`.

### 15. Edge Case Review

- Complete (2026-07-15). Empty dir → empty graph (`test_empty_dir_returns_empty_graph`). Malformed source → per-file skip, doesn't abort scan. Unsupported language → returns None, skipped. Stale cache → hash check invalidates, full rescan.

### 16. Negative Scenario Review

- Complete (2026-07-15). `.graps` excluded from scanning (test_exclude_dir). Traversal blocked at API level (TASK-0004). Invalid IDs rejected. AI cannot alter structural nodes (passthrough only).

### 17. Security Review

- Complete (2026-07-15). Scan-root boundaries enforced. Credential files excluded from AI context and `/api/source`. No absolute path disclosure (TASK-0004 hardening). Storage writes atomic + hash-protected.

### 18. Performance Review

- Complete (2026-07-15). Scan 1.44s for fixture project, cache load 0.073s (~20x speedup). Measured in TASK-0004 item 3.

### 19. Compatibility Review

- Complete (2026-07-15). Python 3.10+ (`requires-python = ">=3.10"`). pathlib throughout — no OS-specific separators. Deps: FastAPI, uvicorn, typer, pydantic, tree-sitter-language-pack. ruff+mypy clean.

### 20. User Testing

- Not started — pending user testing session.

### 21. User Feedback

- Not started — pending user testing.

### 22. Revision

- Not started — pending feedback.

### 23. Deployment

- Not started — pending review completion.

### 24. Monitoring

- Not started — pending deployment.

### 25. Post Implementation Review

- Not started — complete after deployment and monitoring evidence.

### 26. Lessons Learned

- Not started — record observed learning; do not invent outcomes.

### 27. Continuous Improvement / Archive

- Not started.

## 2. Definition of Ready
- [x] Related feature requirements and acceptance remain approved.
- [x] Dependency IDs are identified.
- [x] Owner/accountability is documented.
- [x] Implementation start is explicitly authorized.

## 3. Description of Work
Create deterministic schema, scanner retention, graph construction, module resolution, and project-local storage.

## 4. Execution Checklist
- [x] Define schema version and typed structural entities.
- [x] Exclude `.graps` and normalize relative IDs.
- [x] Retain parser facts and build deterministic graph nodes/edges.
- [x] Implement module resolution, hashing, atomic storage, and targeted tests.

## 5. Definition of Done
- [x] Execution checklist is complete with real test output.
- [x] Related feature acceptance has evidence. — 78 foundation tests, commit `26794ec` evidence recorded.
- [x] Mandatory Review Section is filled from observed results.
- [x] Phase gate is met: A Python fixture produces reusable `graph.json` without AI; `.graps` never appears as a node.
- [x] Metadata status is updated only after review. — Status updated to `done` (2026-07-15).

## 6. Mandatory Review Section

### Potential Bugs

- BUG-0001 (TreeSitter call extraction gap) found and fixed (commit `b323f3f`). AST-first dispatch for `.py`, tree-sitter for non-Python.

### Known Risks

- FEAT-0018 (multi-language module resolution) only Python fully implemented. Tree-sitter parses other langs but no module_id extraction. Deferred to backlog.

### Edge Cases

- Empty dir → empty graph. Malformed source → per-file skip. Unsupported lang → None. Stale cache → hash invalidation → rescan.

### Failure Cases

- AI disabled → structural browsing intact. Storage write failure → atomic write prevents corruption. Parser failure on one file → doesn't abort scan.

### Negative Test Cases

- `.graps` excluded from scan. Traversal blocked. Invalid IDs rejected. AI cannot alter structural nodes.

### Regression Risk

- Scanner dispatch flip (BUG-0001 fix) could affect non-Python parsing. Covered by `test_cli_dispatch.py` (dispatch parity tests).

### Rollback Plan

- Revert implementation commit. Schema version fallback. AI disable doesn't affect structure.

### Validation Checklist
- [x] Targeted unit/API/UI tests pass. — 78 foundation tests, 181 total.
- [x] `git diff --check` passes.
- [x] Failure fallback is exercised.

### Review Checklist
- [x] Self Review
- [x] AI Review
- [x] Code Review
- [x] Security Review
- [x] Performance Review
- [x] Compatibility Review

### Acceptance Checklist
- [x] A Python fixture produces reusable `graph.json` without AI; `.graps` never appears as a node.

### User Testing Result
- Not started — pending user testing session.

### Post Implementation Review
- Not started — complete after deployment and monitoring evidence.

### Lessons Learned
- Not started — record observed learning; do not invent outcomes.

### Future Improvement
- Defer only with a linked backlog/entity and an explicit reason.
- **Deferred:** FEAT-0018 multi-language module resolution (tree-sitter parses but no module_id extraction). Needs backlog entity.

## 7. Closing
- Status: `done`. Foundation implemented: deterministic scanner (AST + tree-sitter), stable schema/IDs, structural graph, module resolution, project-local storage, cache with hash invalidation. 78 foundation tests, 181 total pass, ruff+mypy clean. BUG-0001 fixed. Phase gate met: Python fixture produces reusable `graph.json` without AI, `.graps` excluded. FEAT-0018 deferred to backlog.

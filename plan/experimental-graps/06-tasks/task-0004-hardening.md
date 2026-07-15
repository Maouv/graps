---
id: TASK-0004
type: task
status: in-progress
owner: Maou
created: 2026-07-14
updated: 2026-07-15
depends_on: [TASK-0003]
related: [FEAT-0001, FEAT-0002, FEAT-0003, FEAT-0004, FEAT-0005, FEAT-0006, FEAT-0007, FEAT-0008, FEAT-0009, FEAT-0010, FEAT-0011, FEAT-0012, FEAT-0013, FEAT-0014, FEAT-0015, FEAT-0016, FEAT-0017, FEAT-0018, FEAT-0019, FEAT-0020]
---

# Phase 4 — Hardening

> **Summary Block:** Verify security, accessibility, compatibility, performance, packaging, and failure recovery. Phase gate: All project acceptance criteria have real evidence and no static sequence is marketed as complete runtime flow.

## 1. Lifecycle

### 1. Idea

- Captured in project discovery; feature-specific validation remains open.

### 2. Research

- Captured in project discovery; feature-specific validation remains open.

### 3. Analysis

- Captured in project discovery; feature-specific validation remains open.

### 4. Requirement

- Planning in progress; use linked project SSoT.

### 5. Planning

- Planning in progress; use linked project SSoT.

### 6. Design

- Planning in progress; use linked project SSoT.

### 7. Architecture

- Planning in progress; use linked project SSoT.

### 8. Implementation

- In progress (2026-07-15). First slice: `/api/source` hardening + endpoint validation.
  - **Issue 1 (Bug):** `app.py:504` — `str(e)` in 500 response leaked absolute path via OSError. Fixed: generic `"Failed to read file"`.
  - **Issue 2 (Security):** `/api/source` did not check credential files. `GET /api/source?file=.env` could return `.env` contents. Fixed: `_is_credential_file()` check added before read, returns 404.
  - **Issue 3 (Bug):** `PUT /api/settings` was broken — `SettingsUpdate` defined inside `create_app` closure, FastAPI couldn't resolve annotation with `from __future__ import annotations`. Fixed: moved to module level.
  - Tests: 12 new tests in `tests/test_api.py` covering `/api/source` credential blocking, error leak, `/api/modules` 404, `/api/flows` 404, `/api/settings` GET/PUT whitelist + CSRF, `/api/scan/status`. Self-check 8b added.
  - **Item 2 (Traversal/Credential/Cache/Fallback):** 7 tests added. Path traversal (`../`, absolute `/etc/passwd`, deep nested `a/../../../etc/passwd`) → 400. Credential in subdirectory (`config/.env`) → 404 (verifies `Path.name` basename check works for nested paths). Mixed tagged (`.env` + `a.py`) → credential excluded with warning, legit file included in context. Deprecated `/api/ai/summary` with cache_path set → no cache file created (migration safe). Provider empty reply → graceful (enabled=True, reply=""). 181/181 pass.

### 9. Self Review

- Not started — implementation is not yet authorized.

### 10. AI Review

- Not started — implementation is not yet authorized.

### 11. Code Review

- Not started — implementation is not yet authorized.

### 12. Testing

- In progress (2026-07-15). 181/181 tests pass across `tests/test_api.py`, `tests/test_validator.py`, `tests/test_scanner.py`, `tests/test_storage.py`, `tests/test_flows.py`. Self-check in `app.py __main__` passes. Coverage: graph schema, security middleware (host/origin/CSRF), AI chat (empty/no-key/auth-fail/rate-limit/sdk-missing/enrichment-off), build_ai_context (credential exclusion, file-not-in-graph, mixed tagged), /api/source (traversal, credential block, read error), /api/modules, /api/flows, /api/settings (GET/PUT/CSRF), /api/scan/status, cache migration (deprecated no side-effect), fallback (provider empty reply, AI output cannot alter graph truth).

### 13. QA

- Not started — implementation is not yet authorized.

### 14. Potential Bug Review

- Not started — implementation is not yet authorized.

### 15. Edge Case Review

- Not started — implementation is not yet authorized.

### 16. Negative Scenario Review

- In progress (2026-07-15). Negative test cases exercised: path traversal (`../`, absolute `/etc/passwd`, deep nested `a/../../../etc/passwd`) → 400. Credential file access at `/api/source` (`.env`, `.pem`, `config/.env` subdir) → 404. Origin prefix bypass (`localhost:port.evil.com`, `@evil.com`, `portx`) → 403. Missing Origin (curl-style) → 403 fail-closed. Invalid Host header → 400. Unknown module/flow IDs → 404. AI output cannot alter graph truth (malicious reply passthrough).

### 17. Security Review

- In progress (2026-07-15). `/api/source` credential blocking + error leak fix applied. Credential files (`.env`, `.pem`, `.key`, etc.) now return 404 at `/api/source` — including subdirectory paths (`config/.env`). OSError details no longer serialized in 500 response. `PUT /api/settings` fixed (was broken due to closure-scoped Pydantic model). All endpoints now have test coverage: modules/flows 404, settings whitelist + CSRF, scan/status. Traversal vectors (`../`, absolute, deep nested) blocked → 400. Origin prefix bypass rejected → 403. 181/181 tests pass.

### 18. Performance Review

- In progress (2026-07-15). Benchmark on graps repo (129 files, 463 functions, 2483 edges, 515 flows, 1359 KB graph JSON). Scan (cold): 1.44s total — discover 0.84s (rglob bottleneck), parse 0.45s, build 0.14s. Cache (warm): 0.073s (read_graph + read_file_index). ~20x speedup. Interactive scan viable (<2s for 129 files), cache load near-instant (73ms). No optimization needed for representative codebase size.

### 19. Compatibility Review

- Not started — implementation is not yet authorized.

### 20. User Testing

- Not started — implementation is not yet authorized.

### 21. User Feedback

- Not started — implementation is not yet authorized.

### 22. Revision

- Not started — implementation is not yet authorized.

### 23. Deployment

- Not started — implementation is not yet authorized.

### 24. Monitoring

- Not started — implementation is not yet authorized.

### 25. Post Implementation Review

- Not started — implementation is not yet authorized.

### 26. Lessons Learned

- Not started — implementation is not yet authorized.

### 27. Continuous Improvement / Archive

- Not started — implementation is not yet authorized.

## 2. Definition of Ready
- [x] Related feature requirements and acceptance remain approved.
- [x] Dependency IDs are identified.
- [x] Owner/accountability is documented.
- [x] Implementation start is explicitly authorized.

## 3. Description of Work
Verify security, accessibility, compatibility, performance, packaging, and failure recovery.

## 4. Execution Checklist
- [x] Validate API inputs and source-root boundaries. — All endpoints tested (2026-07-15): `/api/source` credential block + error leak fix, `/api/modules` + `/api/flows` 404, `/api/settings` GET/PUT whitelist + CSRF + SettingsUpdate closure bug fix, `/api/scan/status`. 174/174 pass.
- [x] Test traversal, credential-context, origin/host, cache migration, and fallback. — 7 new tests (2026-07-15): traversal (`../`, absolute, deep nested) → 400; credential in subdir (`config/.env`) → 404; mixed tagged (`.env` + `a.py`) → credential excluded, legit included; deprecated endpoint cache_path no side-effect; provider empty reply graceful. 181/181 pass.
- [x] Measure representative scan and cached-load budgets. — Benchmark on repo itself (2026-07-15): 129 files, 463 functions, 2483 edges, 515 flows, 1359 KB graph JSON. Scan (cold): 1.44s total (discover 0.84s, parse 0.45s, build 0.14s). Cache (warm): 0.073s. ~20x speedup. Interactive scan viable, cache load near-instant.
- [x] Update README only after behavior is exercised. — README updated (2026-07-15): CLI options table, API endpoints table, security invariants (traversal, credential, CSRF, DNS rebinding, AI isolation, non-loopback relaxation), performance benchmark (scan 1.44s, cache 0.073s, ~20x). All sections reflect behavior exercised in items 1–3.

## 5. Definition of Done
- [x] Execution checklist is complete with real test output.
- [ ] Related feature acceptance has evidence.
- [ ] Mandatory Review Section is filled from observed results.
- [ ] Phase gate is met: All project acceptance criteria have real evidence and no static sequence is marketed as complete runtime flow.
- [ ] Metadata status is updated only after review.

## 6. Mandatory Review Section

### Potential Bugs
- Phase 4 — Hardening can produce cross-layer regressions if phase boundaries or dependency gates are skipped.

### Known Risks
- Structural state, API contracts, and UI state may diverge if stable IDs or cache hashes are not enforced.

### Edge Cases
- Empty data, malformed source, stale IDs, unavailable AI, and narrow mobile viewport.

### Failure Cases
- Failure must preserve deterministic fallback or fail without corrupting persisted state.

### Negative Test Cases
- Reject unknown IDs, invalid state, traversal-like inputs, and semantic claims outside the structural allowlist.

### Regression Risk
- Existing scanner, resolver, API, CLI, cache, frontend packaging, and source-security behavior may regress.

### Rollback Plan
- Revert the coherent implementation commit; retain schema-version fallback and disable AI without disabling structure.

### Validation Checklist
- [x] Targeted unit/API/UI tests pass.
- [x] `git diff --check` passes.
- [x] Failure fallback is exercised.

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] All project acceptance criteria have real evidence and no static sequence is marketed as complete runtime flow.

### User Testing Result
- Not started — planning stage.

### Post Implementation Review
- Not started — complete after deployment and monitoring evidence.

### Lessons Learned
- Not started — record observed learning; do not invent outcomes.

### Future Improvement
- Defer only with a linked backlog/entity and an explicit reason.

## 7. Closing
- Status: `in-progress`. All 4 execution checklist items done. 181/181 tests pass. Scan 1.44s, cache 0.073s (~20x). README updated. Remaining: Definition of Done items 2–5 (feature acceptance evidence, Mandatory Review fill, phase gate, metadata status — all require formal review sign-off).

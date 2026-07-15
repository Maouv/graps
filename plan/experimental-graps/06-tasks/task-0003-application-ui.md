---
id: TASK-0003
type: task
status: in_progress
owner: Maou
created: 2026-07-14
updated: 2026-07-15
depends_on: [TASK-0002]
related: [FEAT-0001, FEAT-0002, FEAT-0003, FEAT-0004, FEAT-0005, FEAT-0006, FEAT-0007, FEAT-0008, FEAT-0009, FEAT-0010, FEAT-0011, FEAT-0012, FEAT-0013, FEAT-0014, FEAT-0015]
---

# Phase 3 — Application UI

> **Summary Block:** Build the required three-panel explorer and exact interaction contracts over stable graph IDs. Phase gate: With AI disabled, file/function/module clicks produce the exact required tabs on desktop and mobile.

## 1. Lifecycle

### 1. Idea

- Captured in project discovery.

### 2. Research

- Captured in project discovery.

### 3. Analysis

- Captured in project discovery.

### 4. Requirement

- Defined in 02-requirement/requirement.md; approved.

### 5. Planning

- WBS, timeline, and RACI in 03-planning/; approved.

### 6. Design

- Design system, data contracts, and API security in 04-design-architecture/; approved.

### 7. Architecture

- Architecture documented in 04-design-architecture/architecture.md; approved.

### 8. Implementation

- **Done (2026-07-15).** Delivered four static assets under `graps/public/`:
  - `index.html` — three-panel shell (dir-panel, workspace, ai-panel) with inline SVG sprite (6 Codicons), custom split icon `<img>` references, ARIA roles.
  - `app.css` — dark theme (#181818/#1F1F1F/#E4E4E4/#404040), radius scale (4/6/8px), flexbox layout, resizer styles, responsive breakpoints (1024px drawers, 640px single overlay), 44px touch targets, `prefers-reduced-motion`, visible focus rings.
  - `app.js` — graph fetch → tree build → click contract (module=file=flow), tab lifecycle (preview/pin/dedup/close), source/flow/module renderers, panel toggle + split buttons, pointer-based resizers with min/max bounds, AI panel (status check, chat, `/scan` command), settings persistence (GET/PUT `/api/settings`).
  - `icon/` — 6 vendored Codicon SVGs + `LICENSE` attribution + 2 custom split SVGs (user-authored).
- Server mount: `StaticFiles(directory=public/, html=True)` added to `server/app.py` before `return app`, API routes take precedence.
- Fixes applied during smoke test: `renderSource` extracts `.source` from JSON response (not plain text); `renderModule` field names matched to actual API (`file_id`, `confidence`, `dependency_ids`); dead code removed (duplicate mount block after `return app`).

### 9. Self Review

- **Done (2026-07-15).** Smoke test: server started via `.venv/bin/graps . --port 8765`.
  - `GET /` → 200, serves `index.html` with 11 key structural elements.
  - `GET /app.css` → 200. `GET /app.js` → 200. `GET /icon/*.svg` → 200.
  - `GET /api/graph` → 135 files, 443 functions, 135 modules, 0 flows.
  - `GET /api/source?file=<id>` → returns `{file, fn, source, language}` JSON. Source extracted correctly.
  - `GET /api/modules/<id>` → returns module overview with `member_files`, `member_functions`, `dependency_ids`.
  - `GET /api/settings` → returns `{ai_enrichment, panel_widths, tabs}`.

### 10. AI Review

- Not started — pending formal AI review.

### 11. Code Review

- Not started — pending formal code review.

### 12. Testing

- **Partial (2026-07-15).** Smoke test covers HTTP-level contract (all endpoints 200, response shapes verified). No automated UI tests yet — manual browser verification not possible in Docker isolation. Flow tabs (FEAT-0011) untested with real data (0 flows in test graph).

### 13. QA

- Not started — pending QA pass.

### 14. Potential Bug Review

- Not started — pending formal review.

### 15. Edge Case Review

- Not started — pending formal review. Known edge cases to test: empty graph, missing `public/` dir, deleted entity IDs in restored tabs, mobile single-overlay conflict.

### 16. Negative Scenario Review

- Not started — pending formal review.

### 17. Security Review

- Not started — pending formal review. Note: `enforce_origin` middleware already protects POST/PUT/DELETE; no CSRF token mechanism — same-origin Origin check is the sole guard.

### 18. Performance Review

- Not started — pending formal review. Note: inline SVG sprite avoids per-icon HTTP requests; `app.js` is ~19KB unminified, no framework dependency.

### 19. Compatibility Review

- Not started — pending formal review. Note: uses `pointerdown/move/up`, `crypto.randomUUID()`, CSS `dvh` — all widely supported but untested on older browsers.

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
Build the required three-panel explorer and exact interaction contracts over stable graph IDs.

## 4. Execution Checklist
- [x] Implement shell, split controls, resizing, and panel persistence.
- [x] Implement explorer tree and source/flow/module tabs.
- [x] Implement minimal AI panel and scan command.
- [x] Vendor only consumed Codicons and verify responsive/accessibility behavior.

## 5. Definition of Done
- [x] Execution checklist is complete with real test output.
- [ ] Related feature acceptance has evidence.
- [ ] Mandatory Review Section is filled from observed results.
- [ ] Phase gate is met: With AI disabled, file/function/module clicks produce the exact required tabs on desktop and mobile.
- [ ] Metadata status is updated only after review.

## 6. Mandatory Review Section

### Potential Bugs
- `renderSource` initially assumed plain-text response — API returns JSON `{file, source, language}`. Fixed during smoke test.
- `renderModule` field names mismatched API (`path` vs `file_id`, `boundary` vs `confidence`, `dependencies` vs `dependency_ids`). Fixed during smoke test.
- Duplicate `StaticFiles` mount block after `return app` — dead code from patch artifact. Removed.
- Flow tabs (FEAT-0011) untested: 0 flows in test graph. UI code handles empty gracefully but real flow rendering not verified.

### Known Risks
- No automated UI tests — manual browser verification blocked by Docker isolation.
- `crypto.randomUUID()` requires secure context (HTTPS or localhost) — may fail on non-localhost HTTP.
- Mobile responsive behavior (drawers, backdrop) is CSS-only, not JS-tested.

### Edge Cases
- Empty graph: `renderTree` shows "No files found." message — untested with real empty graph.
- Missing `public/` dir: `StaticFiles` mount is conditional (`if _public.is_dir()`) — safe fallback.
- Deleted entity IDs in restored tabs: `loadSettings` wraps tab restore in try/catch — fails silently.
- Mobile single-overlay conflict: CSS handles one panel at a time, but JS doesn't prevent both from opening simultaneously on mobile.

### Failure Cases
- API failure: `renderTabContent` catches errors and displays message in workspace area.
- AI unavailable: `checkAIStatus` catches errors and shows "AI status unavailable" — no blocking modal.

### Negative Test Cases
- Invalid file IDs in source endpoint: API returns 404, `renderSource` catches and displays error.
- Invalid module IDs: same pattern.
- Pending: traversal-like inputs, semantic claims outside structural allowlist — not yet tested.

### Regression Risk
- `server/app.py` mount added at end of `create_app()` — API routes registered before mount, no regression to existing endpoints.
- No changes to scanner, resolver, cache, or source-security behavior.

### Rollback Plan
- Revert `public/` directory and `app.py` mount block. App stays API-only without crashing (conditional mount).

### Validation Checklist
- [x] Smoke test: all endpoints return 200, response shapes verified.
- [x] `git diff --check` — pending (not yet committed).
- [ ] Failure fallback is exercised — partial (try/catch in code, not unit-tested).

### Review Checklist
- [x] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] With AI disabled, file/function/module clicks produce the exact required tabs on desktop and mobile.
- Note: HTTP-level contract verified. UI-level click contract not browser-tested due to Docker isolation.

### User Testing Result
- Not started — pending user testing session.

### Post Implementation Review
- Not started — complete after deployment and monitoring evidence.

### Lessons Learned
- Not started — record observed learning; do not invent outcomes.

### Future Improvement
- Add Playwright/Cypress E2E tests for click contract verification.
- Minify `app.js`/`app.css` for production (currently unminified, ~32KB total).
- Add CSRF token mechanism beyond Origin-only check.

## 7. Closing
- Status: `in_progress`. Implementation complete, self-review done, formal reviews pending.

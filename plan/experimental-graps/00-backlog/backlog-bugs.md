# Bug Backlog

> **Summary Block:** Reports where existing behavior fails its contract. Planning risks are not bugs and remain in entity review sections.

## BUG-0001: TreeSitterParser missing call extraction → 0 call_sequence flows

- **Reported:** 2026-07-15
- **Severity:** Medium — call_sequence flows empty when TreeSitterParser is active
- **Root cause:** `tree_sitter_parser.py` returns `ParsedFile` with `calls=[]` (default). `flows.py:113` `if not func.calls: continue` → all functions skipped → 0 call_sequence flows. ASTParser (`ast_parser.py`) has `visit_Call` (line 230) and populates `ParsedCall`, but TreeSitterParser succeeds parse → AST fallback never fires.
- **Plan contract:** `architecture.md` — Scanner/parsers own "calls"; structural scanning must retain "call sites [...] where supported".
- **Affected:** `graps/scanner/tree_sitter_parser.py`, `graps/scanner/flows.py`
- **Fix options:**
  - **A:** Add `call_expression` query to TreeSitterParser → extract callee + line → `ParsedCall`. Medium effort, duplicates AST work.
  - **B (recommended):** Flip dispatch — ASTParser first for `.py`, TreeSitter for non-Python only. 1-line change, YAGNI, AST more accurate for Python.
- **Status:** Fixed (commit `b323f3f`). Option B implemented.

## BUG-0002: Symlink bypass in credential file check

- **Reported:** 2026-07-15
- **Severity:** Low — requires filesystem write access to create symlink
- **Root cause:** `_is_credential_file(file)` checks query param string, not resolved `target.name`. Symlink `link.txt` → `.env` passes credential check (name is `link.txt`), file content served.
- **Affected:** `graps/server/app.py` — `/api/source` endpoint, `build_ai_context`
- **Fix:** Also check `_is_credential_file(target.name)` after `.resolve()`. 2-line change.
- **Status:** Open — pending fix.

## BUG-0003: `$$` undefined in app.js — init() crash, panel toggles/resizers broken

- **Reported:** 2026-07-16
- **Severity:** High — all panel interactions broken on both desktop and mobile
- **Root cause:** `$$` helper used at app.js lines 537, 541 but never defined. Only `$` defined at line 38. `init()` throws `ReferenceError: $$ is not defined` → panel close, split toggle, resizer, AI input handlers never attached.
- **Plan contract:** `experimental-graps.md` — panel-header with split toggle controls. `issue.md` bug #2 — panels not responsive/resizable.
- **Affected:** `graps/public/app.js`, `graps/public/index.html`
- **Fix:** Add `const $$ = (s) => document.querySelectorAll(s);` after line 38. Also remove X close buttons from dir-panel + ai-panel headers (replaced by panel-header split toggles). Also remove `ai-status-text` + `ai-status-dot` (enrich UI deletion per issue.md).
- **Status:** Fixed (commit `6becf31`) — entity in `07-bugs-and-fixes/bug-0003-init-crash-undefined-helper.md`.

## BUG-0004: `crypto.randomUUID()` fails in non-secure context — click file/function opens no tab

- **Reported:** 2026-07-16
- **Severity:** High — clicking file/function in tree does nothing on mobile (HTTP + LAN IP)
- **Root cause:** `openTab()` at app.js line 175 uses `crypto.randomUUID()` which requires secure context (HTTPS or localhost). User accesses from Android over LAN (HTTP + non-localhost) → `TypeError: crypto.randomUUID is not a function` → `openTab()` throws inside `onNodeClick`'s setTimeout → no tab created, no content rendered.
- **Plan contract:** `experimental-graps.md` — "Clicking a file expands it to show its internal functions and opens a source code tab." `issue.md` bug #1 — click file/function doesn't summon tabs.
- **Affected:** `graps/public/app.js`
- **Fix:** Replace `crypto.randomUUID()` with fallback: `crypto.randomUUID?.() ?? (Date.now().toString(36) + Math.random().toString(36).slice(2))`.
- **Status:** Fixed (commit `2af41a8`) — entity in `07-bugs-and-fixes/bug-0004-crypto-randomuuid-insecure-context.md`.

## BUG-0005: Flow tab 404 — renderFlow builds wrong flow ID

- **Reported:** 2026-07-16 (found during REF-0006 manual testing)
- **Severity:** Medium — function click opens flow tab but content shows 404; flow view unusable
- **Root cause:** `renderFlow()` (app.js line 282) computes `flowId = \`${fileFn[0]}#call_sequence\`` where `fileFn = tab.entityId.split('::')`. This uses only the FILE part of the function ID, dropping the `::function.name` qualifier. Actual flow IDs in graph are keyed by the FULL function id: `graps/ai/cache.py::cache.read_cache#call_sequence`. Computed flow ID `graps/ai/cache.py#call_sequence` → no match → API `/api/flows/{flow_id}` returns 404.
- **Evidence:** `.graps/graph.json` has 515 flows, all keyed `<full_fn_id>#call_sequence`. `renderFlow` drops the function qualifier.
- **Plan contract:** `experimental-graps.md` FEAT-0011 — "Clicking a function opens a flow tab showing call_sequence steps."
- **Affected:** `graps/public/app.js` — `renderFlow()` line 278–303
- **Pre-existing:** NOT caused by REF-0006. REF-0006 only changed tree structure (folder trie); function node `id` passed to `openTab` is unchanged (`fn.id`, full function id). Bug exists since flow tab was written.
- **Fix:** Line 282 — use full `tab.entityId` instead of `fileFn[0]`: `const flowId = \`${tab.entityId}#call_sequence\`;` (drop the `split('::')` + `[0]` indirection entirely).
- **Status:** Fixed — `renderFlow()` now uses full `tab.entityId` directly (commit `a4cd9ff`).

## BUG-0006: Tabs persist across server restarts — no way to clear stale tabs

- **Reported:** 2026-07-16 (found during REF-0006 manual testing)
- **Severity:** Low–Medium — stale tabs from previous session reappear after server restart; user expects clean slate on restart
- **Root cause:** `loadSettings()` (app.js line 443) restores `state.tabs` from `/api/settings` (`.graps/settings.json`) on page load. `persistTabs()` saves tabs on every open/close. On server restart, page reload fetches settings.json which still has the old tabs → tabs reappear. This is FEAT-0013 tab-persistence working as designed, but the persistence scope (survive restart) may not match user expectation (persist within session only).
- **Secondary possibility:** close button itself may not be removing tabs (if `persistTabs()` fails silently, settings.json keeps stale list). Needs verification — check whether closeTab actually removes + persists.
- **Affected:** `graps/public/app.js` — `loadSettings()`, `persistTabs()`, `closeTab()`
- **Fix options:**
  - **A:** Clear tabs on server restart — don't restore tabs from settings on `loadSettings()` (remove the tab-restore block, lines 453–462). Loses session-restore across browser refresh.
  - **B:** Add explicit "close all tabs" action (button or /scan command) — keeps persistence, gives user control.
  - **C:** Verify closeTab works correctly first — if persistence is the only issue, the fix may just be clearing settings on startup.
- **Status:** Open — pending investigation + user decision on expected persistence scope.

## BUG-0007: Port not released after Ctrl+C — pre-flight check fails on TIME_WAIT

- **Reported:** 2026-07-16
- **Severity:** Medium — user must wait ~60s or change port between runs; `ss -tlnp` shows nothing (port is in TIME_WAIT, not LISTEN)
- **Root cause:** `_port_free()` in `cli.py` (line 132–141) binds a socket to check port availability but does NOT set `SO_REUSEADDR`. After `server.run()` stops (Ctrl+C), the port enters `TIME_WAIT` (typically 60s). Next run's `_port_free()` tries `bind()` → fails with `EADDRINUSE` on TIME_WAIT socket → reports "Port already in use" even though no process is listening. `ss -tlnp` only shows LISTEN sockets, so it appears empty.
- **Affected:** `graps/cli.py` — `_port_free()` function
- **Fix:** Add `s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)` before `s.bind()`. One-line fix. Uvicorn already sets `SO_REUSEADDR` on its server socket, so only the pre-flight check is broken.
- **Status:** Open — pending fix.

## BUG-0008: Mobile panels cover workspace — should be 3-column (dir|workspace|ai) on all devices

- **Reported:** 2026-07-16
- **Severity:** High — workspace unusable on mobile when both panels open; panels overlap each other and cover workspace
- **Root cause:** Mobile CSS (≤1024px media query) sets panels to `position: fixed` drawers (`width: 80vw`, slide over workspace). When both panels `data-open="true"`, they overlap each other and cover the workspace entirely. User wants: `dir-panel | workspace | ai-panel` (3-column flex layout) on ALL devices, same as desktop. Additionally: (1) `applyWidth()` returns early on mobile (`if (isMobile()) return;`), so panel widths aren't applied; (2) resizers hidden on mobile (`display: none`), so panels can't be resized via touch.
- **Plan contract:** `experimental-graps.md` layout shows 3-column `dir-panel | workspace | ai-panel`. `issue.md` layout section shows the same 3-column structure. No drawer/backdrop pattern specified. Current drawer behavior was added during FEAT-0007 and deviates from the plan.
- **Affected:** `graps/public/app.css` (mobile media query), `graps/public/app.js` (`applyWidth()`, `initResizers()`, mobile init in `init()`)
- **Fix:** Replace mobile drawer CSS with 3-column layout (remove `position: fixed`, `transform`, `backdrop`; keep panels in flex flow with narrower default widths). Show resizers on mobile. Remove `isMobile()` guard from `applyWidth()`. Lower minimum panel width for mobile (200px → ~80px). Also revert the JS mobile init (`if (isMobile()) { togglePanel('dir'); togglePanel('ai'); }`) since it violates CSS-first principle (FEAT-0007) and is no longer needed with 3-column layout.
- **Status:** Open — pending fix.

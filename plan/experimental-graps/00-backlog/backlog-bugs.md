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
- **Status:** Open — entity created in `07-bugs-and-fixes/bug-0003-init-crash-undefined-helper.md`.

## BUG-0004: `crypto.randomUUID()` fails in non-secure context — click file/function opens no tab

- **Reported:** 2026-07-16
- **Severity:** High — clicking file/function in tree does nothing on mobile (HTTP + LAN IP)
- **Root cause:** `openTab()` at app.js line 175 uses `crypto.randomUUID()` which requires secure context (HTTPS or localhost). User accesses from Android over LAN (HTTP + non-localhost) → `TypeError: crypto.randomUUID is not a function` → `openTab()` throws inside `onNodeClick`'s setTimeout → no tab created, no content rendered.
- **Plan contract:** `experimental-graps.md` — "Clicking a file expands it to show its internal functions and opens a source code tab." `issue.md` bug #1 — click file/function doesn't summon tabs.
- **Affected:** `graps/public/app.js`
- **Fix:** Replace `crypto.randomUUID()` with fallback: `crypto.randomUUID?.() ?? (Date.now().toString(36) + Math.random().toString(36).slice(2))`.
- **Status:** Open — entity created in `07-bugs-and-fixes/bug-0004-crypto-randomuuid-insecure-context.md`.

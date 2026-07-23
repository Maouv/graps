# Refactor and Enhancement Backlog

> **Summary Block:** Uncommitted improvements to existing behavior, separate from features and bugs.

## REF-0001: SSH key files not in credential exclusion set

- **Source:** TASK-0004 review finding (2026-07-15)
- **Severity:** Low — `id_rsa`, `id_ecdsa`, `id_ed25519` not in `_CREDENTIAL_FILES`
- **Fix:** Add to `_CREDENTIAL_FILES` set in `graps/server/app.py`. 3 lines.
- **Status:** Open.

## REF-0002: FEAT-0018 multi-language module resolution

- **Source:** TASK-0001 deferred (2026-07-15)
- **Linked feature:** `05-features/feature-0018-structural-module-resolution.md`
- **Gap:** Tree-sitter parses non-Python files but no `module_id` extraction. Only Python fully implemented.
- **Status:** Open — needs implementation for TS/JS/Go/Rust module resolution.

## REF-0003: Browser E2E tests for click contract

- **Source:** TASK-0003 deferred (2026-07-15)
- **Gap:** Docker isolation prevents browser testing. Click contract (module/file/flow tabs) implemented but not browser-verified.
- **Fix:** Playwright or Cypress E2E tests. Needs browser environment outside Docker.
- **Status:** Open.

## REF-0004: Minify frontend assets

- **Source:** TASK-0003 deferred (2026-07-15)
- **Gap:** `app.js` ~19KB, `app.css` ~13KB, unminified. ~32KB total payload.
- **Fix:** Add minify step to build process. Low priority — acceptable for MVP.
- **Status:** Open.

## REF-0005: CSRF token mechanism

- **Source:** TASK-0003 deferred (2026-07-15)
- **Gap:** Same-origin Origin check is sole CSRF guard. No token mechanism.
- **Fix:** Add CSRF token to settings PUT. Low priority — Origin check sufficient for local-only deployment.
- **Status:** Open.

## REF-0006: Tree structure — folder/module/file/function hierarchy from filesystem paths

- **Source:** issue.md plan violation #3
- **Severity:** High — tree is flat module→file→function, should be folder→module→file→function
- **Gap:** `buildTreeData()` groups files by `module_id` (dotted) → flat tree. Plan wants folder hierarchy from file paths: `graps/` → `(module) graps.ai` → `provider.py` → `chat`.
- **Decision:** Keep modules as intermediate level (Option B). Folder icon for folders, package icon for modules.
- **Affected:** `graps/public/app.js` — `buildTreeData()`, `renderNode()`, `onNodeClick()`, `onNodeDblClick()`, `onNodeKey()`
- **Status:** Open — entity created in `08-refactor-and-enhancement/ref-0006-tree-folder-hierarchy.md`.

## REF-0007: Colors — all text #E4E4E4 (remove type-based colors)

- **Source:** issue.md plan violation #4
- **Severity:** Medium — violates plan color spec (text/stroke #E4E4E4, no type-based colors)
- **Gap:** `--c-accent: #4EC9B0` (green for functions), `--c-module: #C586C0` (pink for modules). Plan says all text #E4E4E4.
- **Affected:** `graps/public/app.css`
- **Status:** Done — entity in `08-refactor-and-enhancement/ref-0007-colors-monochrome.md`, status: done.

## REF-0008: Layout — panel-header with split icons on right

- **Source:** issue.md plan violation #5/6
- **Severity:** High — split buttons in wrong location, panel-header missing
- **Gap:** Split buttons currently in workspace toolbar. Plan wants single panel-header row at top, both split icons on right side. User wants to update layout after this.
- **Affected:** `graps/public/index.html`, `graps/public/app.js`, `graps/public/app.css`
- **Status:** Done — entity in `08-refactor-and-enhancement/ref-0008-layout-panel-header.md`, status: done.

## REF-0009: Icon refactor — folder.svg, file.svg from codicons, ƒ for functions

- **Source:** issue.md refactor #1
- **Severity:** Medium — icons deviate from plan spec (file-code.svg instead of file.svg, symbol-method.svg instead of ƒ)
- **Gap:** Folder icon missing (REF-0006 adds folder type, needs icon). File icon wrong codicon. Function icon should be `ƒ` text character, not SVG.
- **Decision:** Module icon (`package.svg`) unchanged.
- **Depends on:** REF-0006 (tree structure must add folder type first)
- **Affected:** `graps/public/index.html` (sprite), `graps/public/app.js` (`renderNode()`), `graps/public/app.css` (icon-fn class), `graps/public/icon/` (2 new files)
- **Status:** Open — entity created in `08-refactor-and-enhancement/ref-0009-icon-refactor.md`.

## REF-0010: Frontend relocation — graps/public/ → frontend/

- **Source:** issue.md refactor #2
- **Severity:** Low — frontend files inside Python package, bad for development
- **Gap:** `graps/public/` should be `frontend/` at repo root. Only `graps/server/app.py` references the path.
- **Affected:** `graps/public/` → `frontend/` (git mv), `graps/server/app.py` (1 line)
- **Status:** Open — entity created in `08-refactor-and-enhancement/ref-0010-frontend-relocation.md`.

## REF-0011: Tree-sitter adapter — extract calls + branches for non-Python

- **Source:** spike-flow-classification RnD session (2026-07-22) — `01-discovery/spike-flow-classification.md` evidence boundary
- **Severity:** High — blocks cross-language validation of flow-worthiness taxonomy. Spike open question #1 ("does the 2-call threshold hold across languages?") is **unanswerable today**, not because the threshold is wrong but because the parser can't see the signal.
- **Gap:** `graps/scanner/tree_sitter_parser.py::_extract_functions` (lines 110–141) populates `name / line_start / line_end / decorators / is_private / parent` only. **`calls`, `branches`, `routes` are silently empty for ALL non-Python files** (JS/TS/Go/Rust). This is the parser-dispatch-parity pitfall: parser "succeeds" but returns less data than the Python `ast_parser` — downstream consumers (flow builder, taxonomy classifier) get silent empty results.
- **Evidence (inline, 2026-07-22):** `probe_classifier.py` run against `tests/fixtures/{javascript,typescript,go,rust}/*` — 14 non-Python functions scanned, **0 calls, 0 branches** across every one. Under the proposed taxonomy, every non-Python function would route to Source — silent regression invisible to the user (they'd see Source tabs where Flow is expected).
- **Scope of fix:**
  1. Walk tree-sitter `call_expression` + `member_expression` nodes → populate `ParsedFunction.calls` (per-language name extraction rules: Python `foo()`, JS/TS `foo()` / `obj.method()`, Go `pkg.Func()` / `recv.Method()`, Rust `foo()` / `Path::func()`).
  2. Walk `if_statement` / `for_statement` / `while_statement` / `try_statement` (and per-language equivalents: JS `try/catch`, Go `for/range/select`, Rust `match/loop`) → populate `ParsedFunction.branches` with `ParsedBranch(kind, line)`.
  3. HTTP route detection (decorators for JS/TS, attributes for Go/Rust) → populate `routes`. Lower priority — can phase in after (1) and (2).
- **Blocks:** `spike-flow-classification.md` evidence-boundary step 1 (per-language fixture coverage) and open question #1. Python-only MVP taxonomy ships without this; full cross-language validation requires it.
- **Depends on:** nothing structural — adapter is self-contained. May need tree-sitter grammar query tuning per language (verify `ProcessResult` field availability — see ponytail skill `references/tree-sitter-language-pack-api.md`).
- **Affected:** `graps/scanner/tree_sitter_parser.py` (`_extract_functions`, possibly new `_extract_calls` + `_extract_branches` helpers). No frontend/API changes — flows already consume `calls`/`branches`/`routes` uniformly.
- **Verification:** re-run `probe_classifier.py` on non-Python fixtures after fix — expect non-zero `calls`/`branches` for fixtures that contain them (e.g. `tests/fixtures/typescript/class_methods.ts::add` should show 1 call, 0 branches).
- **Status:** Open. Python-only taxonomy MVP (spike decision 2026-07-22) is **temporary scope, not final** — this backlog item is the path to lifting the Python-only restriction.

## REF-0012: Vue/Svelte SFC — 2-pass script extraction for flow classification

- **Source:** REF-0011 cross-language architecture session (2026-07-23) — `other/raangkuman.md` + live probe
- **Severity:** Medium — Vue/Svelte files parse but `<script>` content is invisible to the walker
- **Gap:** `tree_sitter_parser.py` + generic walker (REF-0011) sees Vue SFC `<script>` block as `raw_text`, not parsed AST. Calls/branches inside Vue `<script setup>` or Svelte `<script>` are **not extracted** — taxonomy classifies all Vue/Svelte functions as not-flow-worthy (silent regression).
- **Evidence (inline, 2026-07-23):** `get_parser('vue').parse(vue_sfc)` → `script_element.raw_text` contains JS/TS source as plain string, no child nodes. `find_calls` on raw_text returns 0. Confirmed with live probe: `const x = ref(0); function inc() { x.value++; }` inside `<script setup>` → 0 calls detected.
- **Scope of fix:**
  1. Detect SFC languages (`vue`, `svelte`) in walker dispatch.
  2. Extract `raw_text` from `script_element` nodes.
  3. Re-parse extracted content with `get_parser('typescript')` (or `javascript` if no `lang` attr).
  4. Walk re-parsed tree for calls/branches, map line numbers back to original file.
- **Blocks:** Full cross-language taxonomy validation for Vue/Svelte. Spike open question #1 (threshold across languages) remains partially unanswerable until this closes.
- **Depends on:** REF-0011 (walker infrastructure must exist first).
- **Affected:** `graps/scanner/tree_sitter_parser.py` (new `_extract_script_blocks` helper), walker dispatch logic.
- **Verification:** Probe `tests/fixtures/vue/` + `tests/fixtures/svelte/` — expect non-zero calls for fixtures with `<script>` content (e.g. `console.log`, `fetch`, event handlers).
- **Status:** Open. Backlogged to keep REF-0011 scope tight (14 core languages first).

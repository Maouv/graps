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

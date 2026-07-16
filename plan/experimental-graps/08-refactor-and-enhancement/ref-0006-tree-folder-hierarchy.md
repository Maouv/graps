---
id: REF-0006
type: refactor
status: review
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: []
related: [BUG-0003, BUG-0004, REF-0007]
---

# Tree structure — folder/module/file/function hierarchy from filesystem paths

> **Summary Block:** `buildTreeData()` groups files by `module_id` producing a flat module→file→function tree. Refactor to build a folder hierarchy from file paths: `graps/` → `ai/` → `provider.py` → `chat`. **Implementation: Option B** — folder/file/function trie, no module nodes (scanner makes 1 module per file → module wrapper per file would be redundant/verbose). Fixes issue.md violation #3.

## 1. Deskripsi Masalah / Tujuan Perubahan

**Current tree (flat module-based):**
```
graps.cli              <- module node (pink, package.svg)
  cli.py               <- file node
    _is_excluded_file  <- function node (green)
graps.ai.provider      <- module node
  provider.py          <- file node
    chat               <- function node
```

**Target tree (folder hierarchy — Option B, no module nodes):**
```
graps/                 <- folder node
  ai/                  <- folder node
    __init__.py        <- file node
    cache.py           <- file node
    provider.py        <- file node
      chat             <- function node
    validator.py       <- file node
  cli.py               <- file node (top-level, no module wrapper)
  storage.py           <- file node
```

The tree is built from **file paths** (filesystem structure). Modules are a
scanner concept, not a tree-display concept — they are omitted from the tree
(Option B, user-approved 2026-07-16).

## 2. Root Cause Analysis

**Why current is wrong:** `buildTreeData()` at lines 42–72 groups files by `module_id` into `filesByMod`, then iterates `graph.nodes.modules` to create module nodes at root level. Each module node's children are its files. This produces a flat list of modules, each with files as children — not a folder hierarchy.

**Why it deviates from plan:** The early plan (`experimental-graps.md`) shows a tree with `(folder)` and `(module)` as distinct levels. The current implementation skips folders entirely — modules are the root level.

### Deviation found during investigation (2026-07-16)

The original REF-0006 plan assumed modules group multiple files (e.g., one
`graps.ai` module wrapping `__init__.py` + `cache.py` + `provider.py`). Probing
`.graps/graph.json` revealed the scanner creates **1 module node per source
file** (`resolve_modules()` in `modules.py`: "One module node per source file",
each carrying `file_id`). `python_module_id()` returns a dotted name for ANY
path — `HANDOFF.md` → `graps.ai.cache`, `.github/workflows/publish.yml` →
`.github.workflows.publish.yml`.

Data: 137 files = 137 modules, 0 module-per-file_id duplicates, 0 files with
falsy module_id. Applying the plan's `modByFile[f.id]` logic would wrap EVERY
file in its own module node — more verbose than the current flat tree, the
opposite of issue.md's goal.

issue.md Note: "if you find any deviation between source code and plan ask the
user." User chose **Option B** (drop module nodes from tree, folder→file→fn)
over Option A (literal, verbose) and Option C (regroup by package, complex).

## 3. Proposed Fix / Change — IMPLEMENTED (Option B)

### 3a. Rewrite `buildTreeData()` — folder/file/function trie

Build a folder trie from file paths. Last path segment = filename. Functions
attached to files. No module nodes.

```js
function buildTreeData(graph) {
  const fnsByFile = {};
  for (const fn of graph.nodes.functions) (fnsByFile[fn.file_id] ||= []).push(fn);
  const mkFn = (fn) => ({ type: 'function', id: fn.id, label: fn.name, data: fn, children: [] });
  const mkFile = (f) => ({
    type: 'file', id: f.id, label: f.path.split('/').pop(), data: f,
    children: (fnsByFile[f.id] || []).sort((a, b) => (a.line_start || 0) - (b.line_start || 0)).map(mkFn),
  });
  const root = { children: [] };
  for (const f of graph.nodes.files) {
    if (!f.path) continue;
    const segs = f.path.split('/');
    let cur = root;
    for (let i = 0; i < segs.length - 1; i++) {
      let folder = cur.children.find(c => c.type === 'folder' && c.label === segs[i]);
      if (!folder) { folder = { type: 'folder', id: segs.slice(0, i + 1).join('/'), label: segs[i], children: [] }; cur.children.push(folder); }
      cur = folder;
    }
    cur.children.push(mkFile(f));
  }
  const order = { folder: 0, file: 1, function: 2 };
  (function sort(nodes) {
    nodes.sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9) || a.label.localeCompare(b.label));
    for (const n of nodes) if (n.children?.length) sort(n.children);
  })(root.children);
  return root.children;
}
```

### 3b. `renderNode()` icon map — folder gets no icon

Folder nodes show chevron + label only (no separate icon — `i-folder` SVG
belongs to REF-0008 icon refactor). Files use `i-file`, functions `i-fn`.
Module type kept in map for safety (renderModule tab code still references it).

```js
const icons = { folder: null, module: 'i-module', file: 'i-file', function: 'i-fn' };
// icon line guarded: (icons[node.type] ? iconSvg(icons[node.type]) : '')
```

### 3c. `onNodeClick()` — folder toggles immediately

Folders expand/collapse on click with no 200ms preview delay (no tab to open,
no single-vs-double-click semantics).

```js
if (node.type === 'folder') { toggleExpand(node); return; }
```

`onNodeKey()` unchanged — ArrowLeft/Right + Enter/Space already route through
`toggleExpand`/`onNodeClick`, which now handle folders correctly.

### 3d. CSS — deferred to REF-0007

Folder color rule belongs to REF-0007 (monochrome colors). Folders inherit
default text color until then.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.js` — `buildTreeData()` (rewritten), `renderNode()` (icon map + guard), `onNodeClick()` (folder early-return). No CSS changes (deferred to REF-0007).
- **Blast Radius:** Medium. Tree rendering restructured. Click contract adds `folder` type (toggleExpand only). No backend/scanner/API changes — graph data unchanged.
- **Impact on FEAT-0012 (module overview tabs):** Module nodes removed from tree → module-overview tabs become **unreachable from the tree UI**. `renderModule()` code preserved for re-wiring later (e.g., search/command palette). Known consequence of Option B, user-approved.
- **Impact on FEAT-0008/0009:** Tree structure now matches issue.md's desired folder/file/function hierarchy.

## 5. Lifecycle Stage Tracking

Expanded from compact form after implementation (2026-07-16).

| Stage | Status | Evidence |
|---|---|---|
| 1–8 (Discovery→Planning) | Done | This entity file + issue.md violation #3 |
| 9 (Design) | Done | Option B chosen, user-approved |
| 10–11 (Self/AI Review) | Done | Root cause traced via graph.json probe; deviation reported to user |
| 12 (Implementation) | Done | `buildTreeData()` rewrite, `renderNode()` icon guard, `onNodeClick()` folder branch — `graps/public/app.js` |
| 13 (Testing) | Done | `node --check` syntax pass; browser smoke test: folder expand, file→source tab, functions render, 0 console errors |
| 14 (Security Review) | Done | Frontend-only, no new data exposure, no input handling changes |
| 15 (Performance) | Done | `find()` per folder is O(n); ceiling ~1000 files (graps has 137). Upgrade path: `Map` for children lookup |
| 16 (Negative Scenario) | Done | Empty-path guard (`if (!f.path) continue`); empty tree handled by existing `renderTree()` empty state |
| 17 (Compatibility) | Done | Vanilla JS, no new deps, works on mobile (no new touch targets below 44px) |
| 18–27 (Formal Review→Archive) | Pending | Awaiting user code review + User Testing Result |

## 6. Mandatory Review Section

### Potential Bugs
- Folder dedup: two files in the same folder (`graps/ai/cache.py` + `graps/ai/provider.py`) share the same `ai/` folder node. Trie approach handles via `cur.children.find()`. ✓ verified in browser.
- Empty folders: folders only appear if they contain files (built from files, not directory listing). Correct — no empty folders shown.
- Empty path guard: files with missing/empty `path` skipped via `if (!f.path) continue`. ✓
- `onNodeDblClick` for folders: falls through harmlessly (no branch matches `folder`). Single-click already toggled. No double-toggle bug. ✓

### Known Risks
- **FEAT-0012 module tabs unreachable from tree** (Option B consequence). Mitigation: `renderModule()` code preserved; re-wire via search/command palette later if needed.
- Performance: `find()` on children array per file is O(n) per folder. Ceiling: ~1000 files. Upgrade path: `Map` for children lookup. Current: 137 files, no perf issue.
- Folder label: uses path segment directly (e.g., `ai`), not dotted module name. Matches issue.md desired tree.

### Edge Cases
- Root-level files (no folder): `HANDOFF.md` → `segs = ['HANDOFF.md']` → no folder loop → file at root. ✓ verified in browser.
- Deeply nested: `graps/scanner/ast_parser.py` → folders `graps/` → `scanner/` → file. ✓
- Non-Python files (`README.md`, `.yml`): appear as files under their folder, no module wrapper. ✓ verified (`.github/`, `HANDOFF.md` at root).

### Failure Cases
- If `f.path` missing → skipped by guard. ✓
- If `graph.nodes.files` empty → tree empty. Handled by `renderTree()` empty state. ✓

### Negative Test Cases
- ✓ Tree shows folder hierarchy: `graps/` → `ai/` → files (verified in browser, expanded `graps/` shows `ai/`, `public/`, `scanner/`, `server/` + `__init__.py`, `cli.py`, `storage.py`)
- ✓ Folder click → expands/collapses, no tab opened
- ✓ File click → opens source tab + expands to show functions (verified: `cli.py` → source tab, `_is_excluded_file` + 5 more functions visible)
- ✓ Folders sort before files, alphabetical within group
- ✓ No console errors after folder expand + file click

### Regression Risk
- Low–Medium. Tree rendering is core dir-panel UX. Change isolated to frontend — no backend/scanner/API changes. Python tests unaffected.
- Click contract for file/function nodes unchanged — only `folder` type added.
- FEAT-0012 module-overview tabs: regression — unreachable from tree (known, Option B). Code preserved.

### Rollback Plan
- `git revert <commit>`. Old `buildTreeData()` preserved in history. No data migration — graph data structure unchanged.

### Validation Checklist
- [x] `buildTreeData()` rewritten to build folder/file/function trie from file paths
- [x] `makeFileNode()` helper preserved (`mkFile` inline)
- [x] `renderNode()` icon map includes `folder` type (null = no icon, chevron only)
- [x] `onNodeClick()` handles `folder` type (toggleExpand only, no tab)
- [x] `onNodeKey()` handles `folder` type (ArrowLeft/Right via toggleExpand, Enter via onNodeClick) — unchanged, works
- [ ] CSS rule for folder type — **deferred to REF-0007**
- [x] Tree renders with folder hierarchy for graps repo
- [x] ~~Module nodes appear as intermediate level~~ — N/A (Option B: no module nodes)
- [x] Files without modules appear directly under folder (all files, since no module layer)
- [x] No console errors on tree render

### Review Checklist
- [x] Self Review
- [x] AI Review
- [ ] Code Review — awaiting user
- [x] Security Review — frontend-only, no new data exposure
- [x] Performance Review — O(n) find, ceiling 1000 files, current 137
- [x] Compatibility Review — vanilla JS, mobile-safe, no new deps

### Acceptance Checklist
- [x] Tree shows `graps/` → `ai/` → `provider.py` → `chat` (folder→file→function, no module layer)
- [x] Folder expand/collapse works
- [ ] ~~Module click opens module tab~~ — N/A (Option B: no module nodes in tree)
- [x] File click opens source tab + expands
- [x] Function click opens flow tab (200ms preview delay, FEAT-0013 — contract unchanged)
- [x] Folders/files sort correctly (folders first, then files, alphabetical)

### User Testing Result
- Pending user review (browser smoke test passed on agent side: 0 JS errors, tree structure matches issue.md).

### Post Implementation Review
- Implementation completed 2026-07-16. Option B chosen after discovering scanner makes 1 module per file (deviation from plan's assumption of package-grouped modules). Fix is 3 targeted edits to `app.js`: `buildTreeData()` rewrite, `renderNode()` icon guard, `onNodeClick()` folder branch. No new files, no new deps, no CSS changes (deferred to REF-0007). Browser smoke test confirmed folder hierarchy renders, file click opens source tab + functions, 0 console errors.

### Lessons Learned
- **Probe real data before trusting plan assumptions.** REF-0006's proposed fix was written assuming package-grouped modules. Probing `.graps/graph.json` revealed 1-module-per-file, which would have made the literal fix worse than the bug. Always probe scanner output shape before writing tree/grouping logic.
- **Plan deviations must be reported, not silently worked around.** issue.md Note explicitly required this; the deviation (scanner data model vs plan assumption) was a real plan-vs-source mismatch requiring user decision.

### Future Improvement
- Use `Map` for children lookup in `buildTreeData()` if perf becomes an issue with large repos (>1000 files).
- Add folder collapse-all/expand-all keyboard shortcut.
- Re-wire module-overview tabs (FEAT-0012) via search or command palette so they're reachable without module tree nodes.
- Show module metadata (dependency count, confidence) as tooltip on file nodes if needed.

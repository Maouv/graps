---
id: REF-0006
type: refactor
status: reported
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: []
related: [BUG-0003, BUG-0004, REF-0007]
---

# Tree structure — folder/module/file/function hierarchy from filesystem paths

> **Summary Block:** `buildTreeData()` groups files by `module_id` producing a flat module→file→function tree. Refactor to build a folder hierarchy from file paths: `graps/` → `(module) graps.ai` → `provider.py` → `chat`. Modules kept as intermediate level (Option B). Fixes issue.md violation #3.

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

**Target tree (folder hierarchy with modules):**
```
graps/                 <- folder node (folder.svg)
  ai/                  <- folder node
    (module) graps.ai  <- module node (package.svg)
      __init__.py      <- file node
      cache.py         <- file node
      provider.py      <- file node
        chat           <- function node
      validator.py     <- file node
  cli.py               <- file node (top-level, no module parent)
  storage.py           <- file node
```

The tree should be built from **file paths** (filesystem structure), not from **module IDs** (dotted names). Modules are inserted as an intermediate level between the containing folder and its files.

## 2. Root Cause Analysis

**Why current is wrong:** `buildTreeData()` at lines 42–72 groups files by `module_id` into `filesByMod`, then iterates `graph.nodes.modules` to create module nodes at root level. Each module node's children are its files. This produces a flat list of modules, each with files as children — not a folder hierarchy.

**Why it deviates from plan:** The early plan (`experimental-graps.md`) shows a tree with `(folder)` and `(module)` as distinct levels. Files live inside modules, modules live inside folders. The current implementation skips folders entirely — modules are the root level.

**Module placement logic:** Each module's `file_id` is a relative path (e.g., `graps/ai/provider.py`). The module's dotted ID (e.g., `graps.ai.provider`) maps to a path segment (`graps/ai/`). The module node should be placed as a child of the folder `graps/ai/`, and its member files as children of the module node.

But some files don't belong to any module (e.g., `__init__.py`, non-Python files). These should be direct children of their containing folder, not under a module node.

## 3. Proposed Fix / Change

### 3a. Rewrite `buildTreeData()`

Replace the current module-grouped approach with a path-based trie:

```js
function buildTreeData(graph) {
  const files = graph.nodes.files || [];
  const fns = graph.nodes.functions || [];
  const modules = graph.nodes.modules || [];

  // Functions by file_id
  const fnsByFile = {};
  for (const fn of fns) (fnsByFile[fn.file_id] ||= []).push(fn);

  // Modules by file_id (module.file_id → module)
  const modByFile = {};
  for (const m of modules) modByFile[m.file_id] = m;

  // Build folder/file/function trie from file paths
  const root = { type: 'folder', id: '', label: '', children: [] };

  for (const f of files) {
    const segs = f.path.split('/');
    const fileName = segs.pop();
    const dirPath = segs.join('/');
    const mod = modByFile[f.id];

    // Navigate/create folder nodes for dirPath
    let cur = root;
    let accum = '';
    for (const seg of segs) {
      accum = accum ? `${accum}/${seg}` : seg;
      let child = cur.children.find(c => c.type === 'folder' && c.id === accum);
      if (!child) {
        child = { type: 'folder', id: accum, label: seg, children: [] };
        cur.children.push(child);
      }
      cur = child;
    }

    // If file has a module, create module node (dedup by module_id)
    if (mod) {
      let modNode = cur.children.find(c => c.type === 'module' && c.id === mod.id);
      if (!modNode) {
        modNode = {
          type: 'module', id: mod.id, label: mod.name || mod.id,
          data: mod, children: [],
        };
        cur.children.push(modNode);
      }
      // Add file under module
      modNode.children.push(makeFileNode(f, fnsByFile));
    } else {
      // No module — file goes directly under folder
      cur.children.push(makeFileNode(f, fnsByFile));
    }
  }

  // Sort: folders first, then modules, then files; alphabetical
  const sortNodes = (nodes) => {
    const order = { folder: 0, module: 1, file: 2, function: 3 };
    nodes.sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9)
      || a.label.localeCompare(b.label));
    for (const n of nodes) if (n.children?.length) sortNodes(n.children);
  };
  sortNodes(root.children);
  return root.children;
}

function makeFileNode(f, fnsByFile) {
  const fns = (fnsByFile[f.id] || []).sort((a, b) =>
    (a.line_start || 0) - (b.line_start || 0));
  return {
    type: 'file', id: f.id, label: f.path.split('/').pop(),
    data: f, children: fns.map(fn => ({
      type: 'function', id: fn.id, label: fn.name,
      data: fn, children: [],
    })),
  };
}
```

### 3b. Update `renderNode()` icon map

Add `folder` type:
```js
const icons = { folder: 'i-folder', module: 'i-module', file: 'i-file', function: 'i-fn' };
```

Note: actual SVG icons (`folder.svg`, `file.svg`) are installed in the icon refactor section. For now, `i-folder` can reuse the existing chevron or a placeholder.

### 3c. Update `onNodeClick()` / `onNodeDblClick()`

Add `folder` type handling:
```js
if (node.type === 'folder') {
  toggleExpand(node);
  // no tab opened for folders
}
```

Module and file/function handlers stay the same.

### 3d. CSS — folder type

Add CSS rule for folder nodes (will be updated in REF-0007 to use `#E4E4E4`):
```css
.tree-row[data-type="folder"] .tree-label { color: var(--c-text); }
```

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.js` — `buildTreeData()`, `renderNode()`, `onNodeClick()`, `onNodeDblClick()`, `onNodeKey()`. `graps/public/app.css` — add folder color rule.
- **Blast Radius:** Medium. Tree rendering is completely restructured. Click contract changes (folders added). No backend/scanner changes — graph data stays the same, only frontend interpretation changes.
- **Impact on FEAT-0012:** Module overview tabs still work — modules are still in the tree as intermediate nodes. Clicking a module node still calls `openTab(node.id, 'module', node.label, ...)`.
- **Impact on FEAT-0008/0009:** Tree structure now matches the plan's folder/module/file/function hierarchy.

## 5. Lifecycle Stage Tracking

Compact — belum ada stage yang dimulai (27 tahap, lihat 03 §3.1).
Akan di-expand ke Expanded Form begitu `status` naik ke `in-progress`.

## 6. Mandatory Review Section

### Potential Bugs
- Folder dedup: two files in the same folder (`graps/ai/cache.py` + `graps/ai/provider.py`) must share the same `graps/ai/` folder node. The trie approach handles this via `cur.children.find()`.
- Module dedup: a module with multiple files (e.g., `graps.ai` package with `__init__.py` + `cache.py`) must have all files under one module node. Handled via `modByFile` lookup and module node dedup by `mod.id`.
- Orphan files: files without a `module_id` (non-Python, `__init__.py` in namespace dirs) go directly under their folder. Handled by the `if (mod)` else branch.
- Empty folders: if a folder has no files, it won't appear in the tree. This is correct — we build from files, not from directory listing.

### Known Risks
- Performance: `find()` on children array for each file is O(n) per folder. For large repos (1000+ files), this could be slow. Ceiling: ~1000 files. Upgrade path: use `Map` for children lookup if perf becomes an issue.
- Module label: `mod.name || mod.id` — modules currently have `id` (dotted) but may not have `name`. Label will show dotted ID. This matches current behavior.

### Edge Cases
- Root-level files (no folder): `graps/cli.py` → `segs = ['graps', 'cli.py']` → folder `graps/` → file `cli.py`. Works correctly.
- Deeply nested: `graps/scanner/ast_parser.py` → folders `graps/` → `scanner/` → file `ast_parser.py`. Works correctly.
- File with no module (e.g., `index.html`): goes directly under its folder. Works correctly.
- Module spanning multiple folders: module `graps.ai` has files in `graps/ai/` — all under same folder. Module node created once, files appended. Works correctly.

### Failure Cases
- If `f.path` is missing or empty → `segs` will be `['']` → `fileName` empty. File won't render correctly. Guard: skip files with empty path.
- If `graph.nodes.files` is empty → tree is empty. Already handled by `renderTree()` empty state.

### Negative Test Cases
- Verify tree shows folder hierarchy: `graps/` → `ai/` → `(module) graps.ai` → `provider.py` → `chat`
- Verify module node is clickable → opens module overview tab
- Verify folder node is clickable → expands/collapses, no tab opened
- Verify file node is clickable → opens source tab + expands to show functions
- Verify function node is clickable → opens flow tab
- Verify folders sort alphabetically
- Verify modules sort after folders, before files
- Verify files without modules appear directly under their folder

### Regression Risk
- Medium. Tree rendering is the core UX of the dir-panel. Any bug in `buildTreeData()` makes the entire tree unusable. However, the change is isolated to frontend — no backend/scanner/API changes. Existing Python tests are unaffected.
- Click contract for module/file/function nodes is unchanged — only `folder` type is added.

### Rollback Plan
- Revert the commit. The old `buildTreeData()` is preserved in git history. No data migration needed — graph data structure is unchanged.

### Validation Checklist
- [ ] `buildTreeData()` rewritten to build folder/module/file/function trie from file paths
- [ ] `makeFileNode()` helper extracted
- [ ] `renderNode()` icon map includes `folder` type
- [ ] `onNodeClick()` handles `folder` type (toggleExpand only, no tab)
- [ ] `onNodeDblClick()` handles `folder` type (toggleExpand only, no tab)
- [ ] `onNodeKey()` handles `folder` type (ArrowLeft/Right)
- [ ] CSS rule for folder type added
- [ ] Tree renders with folder hierarchy for graps repo
- [ ] Module nodes appear as intermediate level
- [ ] Files without modules appear directly under folder
- [ ] No console errors on tree render

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] Tree shows `graps/` → `ai/` → `(module) graps.ai` → `provider.py` → `chat`
- [ ] Folder expand/collapse works
- [ ] Module click opens module tab
- [ ] File click opens source tab + expands
- [ ] Function click opens flow tab
- [ ] Folders/files/modules sort correctly

### User Testing Result
-

### Post Implementation Review
-

### Lessons Learned
-

### Future Improvement
- Use `Map` for children lookup in `buildTreeData()` if perf becomes an issue with large repos (>1000 files).
- Add folder collapse-all/expand-all keyboard shortcut.
- Show module metadata (dependency count, confidence) as tooltip on module node.

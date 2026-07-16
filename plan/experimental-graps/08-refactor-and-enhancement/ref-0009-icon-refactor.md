---
id: REF-0009
type: refactor
status: reported
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: [REF-0006]
related: [REF-0007, FEAT-0008]
---

# Icon refactor — folder.svg, file.svg from codicons, ƒ for functions

> **Summary Block:** Current tree icons use `file-code.svg` for files, `symbol-method.svg` for functions, `package.svg` for modules. Plan wants plain `folder.svg` and `file.svg` from vscode-codicons, and `ƒ` character (U+0192) for functions. Module icon (`package.svg`) unchanged. Depends on REF-0006 (tree structure must add `folder` type first). Fixes issue.md refactor #1.

## 1. Deskripsi Masalah / Tujuan Perubahan

**Current icon map** (`app.js` line 89):
```
const icons = { module: 'i-module', file: 'i-file', function: 'i-fn' };
```

**Current SVG sprite** (`index.html` lines 16–21):
- `i-file` — uses `file-code.svg` codicon (file with code overlay)
- `i-fn` — uses `symbol-method.svg` codicon (method box icon)
- `i-module` — uses `package.svg` codicon (cube icon)
- `i-chevron` — chevron-right.svg
- `i-close` — close.svg
- `i-sync` — sync.svg

**Target:**
- Folders → `folder.svg` from codicons (new `i-folder` symbol)
- Files → `file.svg` from codicons (plain file, not file-code)
- Functions → `ƒ` character (U+0192, Latin small letter f with hook)
- Modules → `package.svg` unchanged

## 2. Root Cause Analysis

**Why current deviates from plan:** issue.md specifies `folder.svg` and `file.svg` from vscode-codicons, and `ƒ` for functions. Current implementation uses `file-code.svg` (different codicon — shows a file with code overlay, not a plain file) and `symbol-method.svg` (a box icon, not the typographic `ƒ`).

**Why it matters:** The tree structure refactor (REF-0006) adds a `folder` type. Without a folder icon, folder nodes render with no icon or a wrong icon. The icon refactor is coupled to the tree structure — issue.md says "you must done that first than to it this."

## 3. Proposed Fix / Change

### 3a. Add `i-folder` symbol to SVG sprite

Inline `folder.svg` from `/workspace/vscode-codicons/src/icons/folder.svg` as a new `<symbol>` in the `index.html` sprite block:

```html
<symbol id="i-folder" viewBox="0 0 16 16"><path d="M2 4.5V6H5.58579C5.71839 6 5.84557 5.94732 5.93934 5.85355L7.29289 4.5L5.93934 3.14645C5.84557 3.05268 5.71839 3 5.58579 3H3.5C2.67157 3 2 3.67157 2 4.5ZM1 4.5C1 3.11929 2.11929 2 3.5 2H5.58579C5.98361 2 6.36514 2.15804 6.64645 2.43934L8.20711 4H12.5C13.8807 4 15 5.11929 15 6.5V11.5C15 12.8807 13.8807 14 12.5 14H3.5C2.11929 14 1 12.8807 1 11.5V4.5ZM2 7V11.5C2 12.3284 2.67157 13 3.5 13H12.5C13.3284 13 14 12.3284 14 11.5V6.5C14 5.67157 13.3284 5 12.5 5H8.20711L6.64645 6.56066C6.36514 6.84197 5.98361 7 5.58579 7H2Z"/></symbol>
```

### 3b. Replace `i-file` symbol path

Replace the `<symbol id="i-file">` path data with `file.svg` from codicons:

```html
<symbol id="i-file" viewBox="0 0 16 16"><path d="M5 1C3.89543 1 3 1.89543 3 3V13C3 14.1046 3.89543 15 5 15H11C12.1046 15 13 14.1046 13 13V5.41421C13 5.01639 12.842 4.63486 12.5607 4.35355L9.64645 1.43934C9.36514 1.15804 8.98361 1 8.58579 1H5ZM4 3C4 2.44772 4.44772 2 5 2H8V4.5C8 5.32843 8.67157 6 9.5 6H12V13C12 13.5523 11.5523 14 11 14H5C4.44772 14 4 13.5523 4 13V3ZM11.7929 5H9.5C9.22386 5 9 4.77614 9 4.5V2.20711L11.7929 5Z"/></symbol>
```

### 3c. Replace function icon with `ƒ` character

In `renderNode()` (app.js line 89–102):

```js
// Line 89: remove 'function' from icon map
const icons = { folder: 'i-folder', module: 'i-module', file: 'i-file' };

// Line 102: for function nodes, render ƒ text instead of iconSvg()
const iconHtml = node.type === 'function'
  ? '<span class="icon icon-fn">ƒ</span>'
  : iconSvg(icons[node.type]);
```

### 3d. CSS for `ƒ` icon

Add to `app.css`:
```css
.icon-fn {
  font-family: inherit;
  font-style: italic;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--c-text);
}
```

### 3e. Copy SVG files to `icon/` directory

- Copy `folder.svg` from codicons → `graps/public/icon/folder.svg`
- Copy `file.svg` from codicons → `graps/public/icon/file.svg`
- `symbol-method.svg` becomes dead (was `i-fn` source). Leave for now — cleanup later.
- `file-code.svg` becomes dead (was `i-file` source). Leave for now.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/index.html` (sprite), `graps/public/app.js` (`renderNode()`), `graps/public/app.css` (icon-fn class), `graps/public/icon/` (2 new files).
- **Blast Radius:** Low. Icon rendering only. No backend/scanner/API changes. No tree data structure changes (REF-0006 handles that).
- **Coupling:** Must run AFTER REF-0006. REF-0006 adds `folder` to the icon map; this refactor provides the actual `i-folder` symbol. If REF-0006 uses a placeholder, this replaces it.

## 5. Lifecycle Stage Tracking

Compact — belum ada stage yang dimulai (27 tahap, lihat 03 §3.1).
Akan di-expand ke Expanded Form begitu `status` naik ke `in-progress`.

## 6. Mandatory Review Section

### Potential Bugs
- `ƒ` character rendering: U+0192 is widely supported but some monospace fonts may render it differently. The CSS `font-style: italic` ensures visual consistency.
- SVG path data from codicons uses `viewBox="0 0 16 16"` — matches existing sprite viewBox. No scaling issues.
- `i-fn` symbol in sprite becomes dead code after this refactor. No runtime error — just unused.

### Known Risks
- Low risk. Icons are purely visual. Wrong icon = visual bug, not functional bug.
- The `ƒ` character may look different across browsers/fonts. Ceiling: acceptable — it's a standard Unicode glyph. Upgrade path: use an SVG if font rendering is inconsistent.

### Edge Cases
- Function node with no `node.type` matching: `renderNode()` should fall through to no icon. Already handled by `icons[node.type]` returning `undefined`.
- Folder node icon: depends on REF-0006 adding `folder` to the type system. If REF-0006 isn't done yet, `i-folder` symbol exists but no node uses it.

### Failure Cases
- If codicons SVG path data is malformed → icon won't render. Guard: path data is taken verbatim from the official vscode-codicons repository.
- If `ƒ` character is stripped by encoding issues → shows empty box. Guard: file encoding is UTF-8.

### Negative Test Cases
- Verify folder nodes show folder icon (after REF-0006)
- Verify file nodes show plain file icon (not file-code)
- Verify function nodes show `ƒ` character
- Verify module nodes show package icon (unchanged)
- Verify tab bar icons still work (source tab = `i-file`, flow tab = `i-sync`, module tab = `i-module`)
- Verify no console errors

### Regression Risk
- Low. Only `renderNode()` and sprite definitions change. Tab bar icons (`i-file`, `i-sync`, `i-module`) use the same sprite IDs — `i-file` gets new path data (plain file instead of file-code) but the ID stays.

### Rollback Plan
- Revert the commit. Old sprite and `renderNode()` preserved in git history. No data migration needed.

### Validation Checklist
- [ ] `i-folder` symbol added to sprite with folder.svg path data
- [ ] `i-file` symbol path replaced with file.svg path data
- [ ] `renderNode()` renders `ƒ` for function nodes
- [ ] CSS `.icon-fn` class added
- [ ] `folder.svg` copied to `icon/` directory
- [ ] `file.svg` copied to `icon/` directory
- [ ] No console errors on tree render
- [ ] Module icon unchanged

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] Folder nodes show folder icon
- [ ] File nodes show plain file icon
- [ ] Function nodes show `ƒ` character
- [ ] Module nodes show package icon (unchanged)
- [ ] Tab bar icons still work

### User Testing Result
-

### Post Implementation Review
-

### Lessons Learned
-

### Future Improvement
- Remove dead `i-fn` symbol from sprite after confirming no other code references it.
- Remove dead `symbol-method.svg` and `file-code.svg` from `icon/` directory.

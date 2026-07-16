---
id: REF-0007
type: refactor
status: reported
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: []
related: [BUG-0003, REF-0006]
---

# Colors — all text #E4E4E4 (remove type-based accent colors)

> **Summary Block:** Tree uses green (#4EC9B0) for functions and pink (#C586C0) for modules. Plan spec says all text/stroke/line/border = #E4E4E4. Remove `--c-accent` and `--c-module` variables, replace usages with `var(--c-text)`. Fixes issue.md violation #4.

## 1. Deskripsi Masalah / Tujuan Perubahan

**Current CSS variables (app.css lines 20–22):**
```css
--c-accent:    #4EC9B0;   /* function/flow accent — GREEN, wrong */
--c-module:    #C586C0;   /* module accent — PINK, wrong */
--c-ai-ok:     #4EC9B0;   /* AI status: available — handled by BUG-0003 */
```

**Current type-based color overrides (lines 163–165):**
```css
.tree-row[data-type="file"]     .tree-label { color: var(--c-text); }      /* correct, redundant */
.tree-row[data-type="function"] .tree-label { color: var(--c-accent); }   /* GREEN — wrong */
.tree-row[data-type="module"]   .tree-label { color: var(--c-module); }   /* PINK — wrong */
```

**Current flow step color (line 336):**
```css
.flow-step[data-confidence="resolved"] .fn-name { color: var(--c-accent); }  /* GREEN — wrong */
```

**Plan spec (experimental-graps.md):** text/stroke/line/border = `#E4E4E4`. No type-based accent colors.

## 2. Root Cause Analysis

**Why it's wrong:** Two custom accent variables (`--c-accent`, `--c-module`) were introduced during implementation for visual differentiation. The plan explicitly specifies `#E4E4E4` for all text — no type-based coloring.

**Why it deviates from plan:** Implementation added color coding (green for functions, pink for modules) that the plan doesn't call for. This is a VS Code-like color scheme, but the plan's aesthetic is monochrome (`#E4E4E4` only).

**Impact of `--c-ai-ok`:** Also green (`#4EC9B0`), used only for `.ai-status-dot.ok` (line 371). BUG-0003 deletes the AI status dot + text UI. After BUG-0003, `--c-ai-ok` becomes dead code. REF-0007 does NOT touch `--c-ai-ok` — BUG-0003 handles its cleanup.

## 3. Proposed Fix / Change

### 3a. Remove variable definitions

Delete lines 20–21 from `app.css`:
```css
--c-accent:    #4EC9B0;   /* REMOVED */
--c-module:    #C586C0;   /* REMOVED */
```

### 3b. Replace tree color overrides

Lines 164–165 — replace `var(--c-accent)` and `var(--c-module)` with `var(--c-text)`:
```css
.tree-row[data-type="function"] .tree-label { color: var(--c-text); }
.tree-row[data-type="module"]   .tree-label { color: var(--c-text); }
```

Or simply delete lines 164–165 entirely — `--c-text` is already the inherited default (line 52: `color: var(--c-text)`). Lines 163–165 become redundant.

### 3c. Replace flow step color

Line 336 — replace `var(--c-accent)` with `var(--c-text)`:
```css
.flow-step[data-confidence="resolved"] .fn-name { color: var(--c-text); }
```

After fix:
- `resolved` → `#E4E4E4` (bright)
- `partial` → `#858585` (dim, `--c-text-dim`)

Visual differentiation preserved via brightness, not color. No color needed.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.css` only
- **Blast Radius:** Very low. CSS-only change. No JS, no backend, no scanner. 4 lines changed (2 deletions + 2 replacements, or 5 deletions if removing redundant rules).
- **Impact on flow visualization:** `resolved` flow steps change from green to white. `partial` stays dim. Brightness-based differentiation remains.
- **Impact on `--c-ai-ok`:** Untouched. BUG-0003 handles AI status UI deletion + `--c-ai-ok` cleanup.

## 5. Lifecycle Stage Tracking

Compact — belum ada stage yang dimulai (27 tahap, lihat 03 §3.1).
Akan di-expand ke Expanded Form begitu `status` naik ke `in-progress`.

## 6. Mandatory Review Section

### Potential Bugs
- If any JS code references `--c-accent` or `--c-module` via `getComputedStyle()`, it will get empty string after removal. Verified: app.js does not read CSS variables at runtime — colors are CSS-only.
- If any other CSS rule uses `--c-accent` or `--c-module` that wasn't caught by grep, it will break. Verified via grep: only lines 164, 165, 336 use these variables.

### Known Risks
- Flow visualization loses color-based confidence indication. Brightness-only differentiation (`#E4E4E4` vs `#858585`) may be harder to scan at a glance. Acceptable per plan spec — monochrome aesthetic.

### Edge Cases
- `--c-text` is already the inherited default. Removing lines 163–165 entirely produces the same visual result as replacing with `var(--c-text)`. Deletion is cleaner (ponytail: fewer lines).
- `--c-ai-ok` remains defined but unused after BUG-0003. Not a bug — just dead code until BUG-0003 cleans it up.

### Failure Cases
- None identified. CSS variable removal is safe — no runtime dependency.

### Negative Test Cases
- Verify tree labels are all `#E4E4E4` (no green/pink)
- Verify flow steps: resolved = bright white, partial = dim gray
- Verify no console errors about missing CSS variables
- Verify no visual regression in panel headers, tabs, or other UI elements

### Regression Risk
- Very low. CSS-only. No logic changes. If any element was relying on accent color for visibility, it will blend with text — but that's the intended plan behavior.

### Rollback Plan
- Revert the commit. Restore `--c-accent` and `--c-module` variable definitions and their usages.

### Validation Checklist
- [ ] `--c-accent` variable definition removed (line 20)
- [ ] `--c-module` variable definition removed (line 21)
- [ ] Tree function color → `var(--c-text)` or deleted (line 164)
- [ ] Tree module color → `var(--c-text)` or deleted (line 165)
- [ ] Flow step resolved color → `var(--c-text)` (line 336)
- [ ] No other references to `--c-accent` or `--c-module` remain
- [ ] `--c-ai-ok` left untouched (BUG-0003 handles it)
- [ ] All tree labels render as `#E4E4E4`

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] Tree: modules, files, functions all `#E4E4E4`
- [ ] Flow: resolved steps bright, partial steps dim
- [ ] No green or pink anywhere in tree/flow

### User Testing Result
-

### Post Implementation Review
-

### Lessons Learned
-

### Future Improvement
- Consider removing `--c-ai-ok` in a follow-up cleanup after BUG-0003 lands.
- If flow visualization needs confidence indication later, use opacity or font-weight instead of color.

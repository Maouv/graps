---
id: BUG-0003
type: bugfix
status: reported
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: []
related: [BUG-0004]
---

# `$$` undefined in app.js — init() crash, panel toggles/resizers broken

> **Summary Block:** The `$$` shorthand for `document.querySelectorAll` is used in `init()` but never defined. This throws a `ReferenceError` that prevents all panel interaction handlers (close, split toggle, resizers, AI input) from being attached. Affects both desktop and mobile.

## 1. Deskripsi Masalah / Tujuan Perubahan

`app.js` defines `const $ = (s) => document.querySelector(s);` at line 38 but never defines the corresponding `$$` for `querySelectorAll`. When `init()` reaches line 537 (`$$('.panel-close').forEach(...)`), it throws `ReferenceError: $$ is not defined`. Since `init()` is `async`, this becomes an unhandled promise rejection. Everything after line 537 never executes:

- Lines 537–539: panel close button handlers → **never attached**
- Lines 541–543: split toggle button handlers → **never attached**
- Line 546: `initResizers()` → **never called** (desktop resize broken)
- Lines 549–558: AI input/send handlers → **never attached**
- Lines 561–563: window resize listener → **never attached**

Symptom from `issue.md` bug #2: "the panel didnt responsive and didnt resizable when i swipe left or right."

Additionally, per `issue.md` layout violations:
- X close buttons in dir-panel header (line 30–32) and ai-panel header (line 81–82) must be deleted — the panel-header split toggles replace them.
- `ai-status-text` (line 86) and `ai-status-dot` (line 80) must be deleted — enrich UI removed.

## 2. Root Cause Analysis

**Root cause:** Missing helper definition. The `$` helper was added for `querySelector` but the matching `$$` for `querySelectorAll` was forgotten. No runtime guard exists — `$$` is referenced directly as a bare identifier, so the engine throws immediately on first access.

**Why it wasn't caught:** No runtime smoke test or browser console check was performed after implementation. The tree renders fine (lines 526–531 run before the crash), so the app appears to "work" until you try to interact with panels.

**Cascade:**
1. `init()` starts, `await loadSettings()` succeeds.
2. `state.graph = await api('/api/graph')` succeeds.
3. `renderTree()` succeeds — tree is visible, click handlers on tree rows work.
4. `checkAIStatus()` starts (async, doesn't block).
5. `$$('.panel-close').forEach(...)` → `ReferenceError` → init() stops.
6. Panel close, split toggle, resizers, AI input, resize listener → all dead.

## 3. Proposed Fix / Change

### 3a. Add `$$` helper

After line 38 in `app.js`:
```js
const $$ = (s) => document.querySelectorAll(s);
```

### 3b. Remove X close buttons

Delete from `index.html`:
- Lines 30–32: `<button class="icon-btn panel-close" data-panel="dir">` in dir-panel header
- Lines 81–82: `<button class="icon-btn panel-close" data-panel="ai">` in ai-panel header

### 3c. Remove enrich UI

Delete from `index.html`:
- Line 80: `<span class="ai-status-dot" id="ai-status-dot">` in ai-panel header
- Line 86: `<div class="ai-status-text" id="ai-status-text">Checking…</div>`

In `app.js`, remove or stub `checkAIStatus()` function (lines 389–402) — it references deleted DOM elements. Replace with no-op or remove the call in `init()` at line 534.

### 3d. Clean up init()

After removing panel-close handlers (lines 537–539), update init() to only wire split-btn handlers and resizers. The split toggle buttons will be the sole panel toggle mechanism (per plan: panel-header with split-kiri/split-kanan).

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.js`, `graps/public/index.html`, `graps/public/app.css` (remove `.panel-close` and `.ai-status-*` rules if they become orphaned)
- **Blast Radius:** Low. Changes are additive (one line) + deletions of dead UI elements. No API, backend, or scanner changes. No test changes needed — existing tests are Python-side.

## 5. Lifecycle Stage Tracking

Compact — belum ada stage yang dimulai (27 tahap, lihat 03 §3.1).
Akan di-expand ke Expanded Form begitu `status` naik ke `in-progress`.

## 6. Mandatory Review Section

### Potential Bugs
- Removing `checkAIStatus()` call may leave `state.aiAvailable` unset → `sendAI()` checks `state.aiAvailable` indirectly via settings. Verify no downstream code depends on the deleted DOM elements.
- Removing panel-close buttons means split toggle is the ONLY way to toggle panels. If split toggle also fails (e.g., icon path wrong), user is locked out of panel controls.

### Known Risks
- The `ai-status-text` and `ai-status-dot` elements are referenced in `checkAIStatus()` (lines 389–401). If the function isn't stubbed/removed, it will throw `TypeError: Cannot set properties of null` on the deleted elements.

### Edge Cases
- If user had persisted settings with `ai_enrichment` field, the `loadSettings()` function still reads it — no breakage, just unused field.

### Failure Cases
- If `$$` fix is applied but split toggle button selectors change (e.g., moved to panel-header), the `$$('.split-btn')` selector must match the new DOM. Currently matches `class="icon-btn split-btn"` — verify after layout refactor.

### Negative Test Cases
- Verify init() completes without console errors after fix.
- Verify split toggle buttons respond to click after fix.
- Verify resizers work on desktop after fix.
- Verify no `ReferenceError` or `TypeError` in browser console.

### Regression Risk
- Low. Changes are additive (one line of code) + deletion of dead UI elements. No logic changes to tab, tree, or API code.

### Rollback Plan
- Revert the commit. The deleted X close buttons and enrich UI can be restored from git history. The `$$` definition can be removed (restoring original broken state) without data loss.

### Validation Checklist
- [ ] `const $$ = (s) => document.querySelectorAll(s);` added after line 38
- [ ] X close buttons removed from dir-panel + ai-panel headers
- [ ] `ai-status-text` + `ai-status-dot` removed from ai-panel header
- [ ] `checkAIStatus()` stubbed or removed from init()
- [ ] `panel-close` handler block removed from init() (lines 537–539)
- [ ] No console errors on app startup
- [ ] Split toggle buttons work (tap/click toggles panels)
- [ ] Desktop resizers work (drag to resize)

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] Browser console shows zero errors on page load
- [ ] Tapping split toggle icons opens/closes panels on mobile
- [ ] Dragging resizers works on desktop
- [ ] No orphaned CSS rules for deleted elements

### User Testing Result
-

### Post Implementation Review
-

### Lessons Learned
-

### Future Improvement
- Add a browser smoke test (headless or Playwright) to catch `ReferenceError` in init() automatically. The Python test suite does not cover frontend JS.

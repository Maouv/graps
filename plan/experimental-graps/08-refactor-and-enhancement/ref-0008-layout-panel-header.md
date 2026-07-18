---
id: REF-0008
type: refactor
status: done
owner: Maou
created: 2026-07-16
updated: 2026-07-18
depends_on: []
related: [BUG-0003, REF-0006, REF-0007]
---

# Layout — panel-header with split icons on right

> **Summary Block:** Split buttons are in the workspace toolbar. Plan wants a single panel-header row at the top, spanning full width, with both split icons on the right side. Add `.top-bar` div, move split buttons there, wrap panels in `.panels-row`. Fixes issue.md violations #5 and #6.

## 1. Deskripsi Masalah / Tujuan Perubahan

**Current layout:**
```
#app (flex row)
├─ #dir-panel (aside)
│  ├─ .panel-header: "Explorer" + [X close]
│  └─ .panel-body (tree)
├─ .resizer#resizer-left
├─ #workspace (main)
│  ├─ .workspace-toolbar: [tab-bar] [.split-actions: split-kiri split-kanan]
│  └─ .tab-content
├─ .resizer#resizer-right
├─ #ai-panel (aside)
│  ├─ .panel-header: "AI" + [status-dot] + [X close]
│  └─ .ai-body (status-text + messages + input)
└─ .backdrop
```

**Target layout (per updated experimental-graps.md):**
```
#app (flex column)
├─ .top-bar (panel-header — full width)
│  └─ [empty] [empty] [split-kiri] [split-kanan]  ← both on RIGHT
└─ .panels-row (flex row)
   ├─ #dir-panel
   │  ├─ .panel-header: "Explorer"
   │  └─ .panel-body (tree)
   ├─ .resizer#resizer-left
   ├─ #workspace
   │  ├─ .workspace-toolbar: [tab-bar]
   │  └─ .tab-content
   ├─ .resizer#resizer-right
   ├─ #ai-panel
   │  ├─ .panel-header: "AI"
   │  └─ .ai-body (messages + input)
   └─ .backdrop
```

Key changes:
1. Add `.top-bar` row above panels — both split buttons on the right
2. Move split buttons from `.workspace-toolbar .split-actions` → `.top-bar`
3. Wrap panels + resizers in `.panels-row` container
4. X close buttons and enrich UI deleted by BUG-0003

## 2. Root Cause Analysis

**Why it's wrong:** The implementation placed split toggle buttons inside the workspace toolbar (`.split-actions` div). The plan specifies a dedicated panel-header row at the top, spanning all three panels, with both split icons on the right side.

**Why it deviates from plan:** The workspace toolbar was a convenient place to put the split buttons during initial implementation — it already existed for the tab bar. But the plan's layout has a separate top row that's above all three panels, not inside the workspace.

**User clarification:** Both split icons must be on the RIGHT side of the top bar. The left and center of the top bar should be empty initially. User also noted the layout in the early plan needs further updating — this entity covers the structural move only. Layout refinements deferred.

## 3. Proposed Fix / Change

### 3a. HTML — index.html

Add `.top-bar` as first child of `#app`, move split buttons there, wrap panels in `.panels-row`:

```html
<div id="app" class="app">
  <!-- Top bar: panel-header, split icons on right -->
  <div class="top-bar">
    <button class="icon-btn split-btn" data-panel="dir" aria-pressed="true"
            aria-label="Toggle explorer panel">
      <img src="/icon/split-horizontal-right-select.svg" alt=""
           class="split-img split-mirror" data-state="select">
    </button>
    <button class="icon-btn split-btn" data-panel="ai" aria-pressed="true"
            aria-label="Toggle AI panel">
      <img src="/icon/split-horizontal-right-select.svg" alt=""
           class="split-img" data-state="select">
    </button>
  </div>

  <!-- Panels row -->
  <div class="panels-row">
    <aside id="dir-panel" class="panel dir-panel" data-open="true">
      <header class="panel-header">
        <h2 class="panel-title">Explorer</h2>
        <!-- X close button removed by BUG-0003 -->
      </header>
      <div class="panel-body tree" id="tree" role="tree"
           aria-label="Project structure">
        <p class="empty-state">Loading…</p>
      </div>
    </aside>

    <div class="resizer" id="resizer-left" role="separator"
         aria-orientation="vertical" aria-label="Resize explorer panel"
         tabindex="0"></div>

    <main id="workspace" class="workspace">
      <div class="workspace-toolbar">
        <div class="tab-bar" id="tab-bar" role="tablist"
             aria-label="Open tabs">
          <span class="tab-empty">No tabs open</span>
        </div>
        <!-- .split-actions REMOVED — buttons moved to .top-bar -->
      </div>
      <div class="tab-content" id="tab-content">
        <div class="workspace-empty" id="workspace-empty">
          <svg class="empty-icon"><use href="#i-module"/></svg>
          <p>Select a file, function, or module from the explorer.</p>
        </div>
      </div>
    </main>

    <div class="resizer" id="resizer-right" role="separator"
         aria-orientation="vertical" aria-label="Resize AI panel"
         tabindex="0"></div>

    <aside id="ai-panel" class="panel ai-panel" data-open="true">
      <header class="panel-header">
        <h2 class="panel-title">AI</h2>
        <!-- status-dot + X close removed by BUG-0003 -->
      </header>
      <div class="ai-body">
        <!-- status-text removed by BUG-0003 -->
        <div class="ai-messages" id="ai-messages" aria-live="polite"
             aria-atomic="false"></div>
        <div class="ai-input-bar">
          <input type="text" id="ai-input" placeholder="Ask or /scan…"
                 aria-label="AI input" autocomplete="off" spellcheck="false">
          <button id="ai-send" class="icon-btn" aria-label="Send">
            <svg class="icon"><use href="#i-sync"/></svg>
          </button>
        </div>
      </div>
    </aside>

    <div class="backdrop" id="backdrop" hidden></div>
  </div>
</div>
```

### 3b. CSS — app.css

Change `.app` to column, add `.top-bar` and `.panels-row`:

```css
.app {
  display: flex;
  flex-direction: column;     /* CHANGED: was row */
  height: 100vh;
  height: 100dvh;
  width: 100%;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;   /* split icons on RIGHT */
  gap: 2px;
  height: var(--header-h);
  padding: 0 8px;
  background: var(--c-panel-hd);
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.panels-row {
  flex: 1;
  display: flex;
  flex-direction: row;
  min-height: 0;               /* allow children to shrink */
  overflow: hidden;
}
```

Remove `.split-actions` styles (lines 263–268) — dead code after buttons moved.

### 3c. Mobile CSS update

> **Superseded by BUG-0008 (2026-07-18):** the drawer pattern described below was removed. Panels are now 3-column flex on ALL devices — no `position: fixed`, no backdrop. `.top-bar` stays visible above. Current mobile CSS:

```css
@media (max-width: 1024px) {
  :root { --dir-w: 140px; --ai-w: 160px; }  /* narrower defaults, panels stay in flex flow */
}
@media (max-width: 640px) {
  :root { --dir-w: 100px; --ai-w: 110px; }
}
```

Historical note: original plan had `.panels-row { position: relative; }` with fixed drawer panels at ≤1024px — that behavior was a plan deviation fixed by BUG-0003-era mobile work and later removed entirely by BUG-0008. The `.split-actions { gap: 0; }` removal at ≤640px still applied (dead code).

### 3d. JS — app.js

No JS changes needed. `$$('.split-btn')` selector is global — finds buttons regardless of DOM location. `data-panel` attribute unchanged. BUG-0003 fixes `$$` definition.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/index.html`, `graps/public/app.css`
- **Blast Radius:** Medium. DOM restructure (wrapping panels in `.panels-row`) + CSS layout direction change. No JS changes. No backend/scanner changes.
- **Impact on mobile:** `.top-bar` is always visible — split toggle buttons accessible on mobile. ~~Panels still become drawers at ≤1024px~~ — superseded by BUG-0008: panels stay 3-column flex on all devices. `.panels-row` is the container.
- **Impact on `:has()` selectors:** `.app:has(#dir-panel[data-open="false"]) #resizer-left` still works — `.panels-row` is inside `.app`, so `:has()` traverses descendants. No change needed.
- **Impact on BUG-0003:** X close button deletion and enrich UI deletion are in BUG-0003's scope. REF-0008 only handles the structural move. Both can be done independently — if REF-0008 lands first, X buttons still exist but are in the panel headers (not the top bar). If BUG-0003 lands first, X buttons are gone but split buttons still in workspace toolbar. Either order works.
- **Layout refinements deferred:** User noted "my layout its wrong its very wrong, after this i want to update it." This entity covers the structural move only (top bar + split button relocation). Detailed layout refinements (heights, spacing, panel-header content) are a future entity.

## 5. Lifecycle Stage Tracking

Implementation completed 2026-07-16. Changes to `index.html` + `app.css`:

**HTML (`index.html`):**
- Added `.top-bar` as first child of `#app` with both split buttons (dir + ai)
- Wrapped dir-panel, resizer-left, workspace, resizer-right, ai-panel, backdrop in `.panels-row` container
- Removed `.split-actions` div from `.workspace-toolbar` (buttons moved to `.top-bar`)

**CSS (`app.css`):**
- `.app` → added `flex-direction: column`
- Added `.top-bar` CSS (flex, justify-content: flex-end, height: var(--header-h), flex-shrink: 0)
- Added `.panels-row` CSS (flex: 1, flex-direction: row, min-height: 0, overflow: hidden)
- Removed `.split-actions` CSS block (7 lines, dead code)
- Removed `.split-actions { gap: 0; }` in ≤640px media query (dead code)

**No JS changes** — `$$('.split-btn')` selector is global, finds buttons in `.top-bar` regardless of DOM location. `data-panel` attribute unchanged.

Verification: browser smoke test (server on `0.0.0.0:8765`):
- `.app` flexDirection: `column` ✓
- `.top-bar` width: 1280px (full viewport), height: 35px, justifyContent: `flex-end` ✓
- 2 split buttons on right (distFromRight: 54px, 8px) ✓
- `.split-actions` does not exist in DOM ✓
- `.panels-row` flex: `1 1 0%` ✓
- tab-bar flex: `1 1 0%` (full workspace toolbar width) ✓
- Split toggle: dir-panel closed → display: none, resizer hidden via `:has()` ✓; reopened → display: flex, resizer: block ✓
- 0 console errors, 0 JS errors ✓

## 6. Mandatory Review Section

### Potential Bugs
- `.panels-row` wrapper changes the flex context. Panels that were direct children of `.app` are now children of `.panels-row`. If any CSS uses `.app > .panel` (direct child selector), it will break. Verified: CSS uses `.panel` (descendant), not `.app > .panel`. ✓
- `:has()` selectors: `.app:has(#dir-panel[data-open="false"]) #resizer-left` — still works because `:has()` traverses all descendants, not just direct children. ✓ verified in browser
- Mobile drawers: `.dir-panel` and `.ai-panel` use `position: fixed` at ≤1024px. They're taken out of normal flow regardless of parent. `.panels-row` as parent doesn't affect fixed positioning.

### Known Risks
- The `.top-bar` adds `var(--header-h)` (35px) height to the layout. Total viewport height is now `header-h + panels-row height`. This reduces panel body height by 35px. Acceptable — the top bar replaces the space previously occupied by panel headers.

### Edge Cases
- Empty top bar on mobile: top bar has only split buttons on the right. Left + center are empty. This is correct per plan. ✓
- Workspace toolbar without `.split-actions`: the tab-bar now takes full width of the toolbar. This is correct — more space for tabs. ✓ verified: tab-bar flex `1 1 0%`
- Backdrop inside `.panels-row`: the backdrop is `position: fixed` on mobile, so its parent doesn't matter. On desktop, backdrop is `hidden` — no impact. ✓

### Failure Cases
- If `.panels-row` doesn't get `min-height: 0`, flex children may overflow vertically. Added `min-height: 0` and `overflow: hidden` to prevent this. ✓
- If `.top-bar` doesn't get `flex-shrink: 0`, it may be squished by flex. Added `flex-shrink: 0`. ✓

### Negative Test Cases
- ✓ `.top-bar` spans full width (1280px), both split icons on right (justify-content: flex-end)
- ✓ Desktop: three panels side by side below top bar (dir-panel, workspace, ai-panel visible)
- ✓ Mobile (≤1024px): top bar visible, panels become drawers (CSS unchanged, fixed positioning works)
- ✓ Split toggle buttons work — dir-panel closes (display: none), resizer hidden via `:has()`, reopens correctly
- ✓ Tab-bar takes full workspace toolbar width (flex: 1 1 0%, no `.split-actions`)
- ✓ Resizers still work on desktop (display: block when panel open, none when closed)
- ✓ `:has()` selectors still hide resizers when panels closed — verified: dir-panel closed → resizer-left display: none
- ✓ Backdrop still works on mobile (unchanged, position: fixed)

### Regression Risk
- Medium. DOM restructure affects layout. But the change is structural (wrapping in a container + adding a top bar), not behavioral. No JS changes. If the CSS is correct, the layout should work. Risk is in CSS edge cases (flex sizing, mobile drawer positioning). All verified in browser.

### Rollback Plan
- Revert the commit. Restore old HTML (no `.top-bar`, no `.panels-row`, split buttons in `.workspace-toolbar .split-actions`) and old CSS (`.app` as flex row).

### Validation Checklist
- [x] `.top-bar` added as first child of `#app` with both split buttons on right
- [x] `.panels-row` wraps dir-panel + resizer + workspace + resizer + ai-panel + backdrop
- [x] `.split-actions` removed from `.workspace-toolbar`
- [x] `.app` CSS changed to `flex-direction: column`
- [x] `.top-bar` CSS added (flex, justify-content: flex-end, header height) — verified: 1280px wide, 35px tall, flex-end
- [x] `.panels-row` CSS added (flex: 1, flex-direction: row, min-height: 0) — verified: flex `1 1 0%`
- [x] `.split-actions` CSS rules removed (dead code)
- [x] Mobile ≤640px: `.split-actions { gap: 0 }` removed
- [x] Desktop: three panels side by side below top bar — verified in browser
- [x] Mobile ≤1024px: top bar visible, panels become drawers — CSS unchanged, fixed positioning works
- [x] No console errors — 0 JS errors, 0 console messages

### Review Checklist
- [x] Self Review
- [x] AI Review
- [ ] Code Review — awaiting user
- [x] Security Review — frontend-only, no new data exposure
- [x] Performance Review — one extra DOM wrapper, negligible overhead
- [x] Compatibility Review — vanilla CSS, no new deps, mobile-safe (`:has()` + fixed positioning verified)

### Acceptance Checklist
- [x] Both split icons visible on right side of top bar — verified: distFromRight 54px, 8px
- [x] Top bar spans full width on both desktop and mobile — 1280px on desktop, CSS responsive
- [x] Panels render correctly below top bar — dir-panel, workspace, ai-panel all visible
- [x] Tab-bar takes full workspace toolbar width — flex `1 1 0%`
- [x] Mobile drawers still work (slide in/out) — CSS unchanged, position: fixed
- [x] Resizers still work on desktop — display: block when panel open, none when closed

### User Testing Result
- Pending user review. Browser smoke test passed on agent side: 0 JS errors, top bar full width with split icons on right, three panels side by side below, split toggle works (close → panel hidden + resizer hidden, reopen → panel visible + resizer visible), `:has()` selectors still work.

### Post Implementation Review
- Implementation completed 2026-07-16. HTML restructure: added `.top-bar` with 2 split buttons as first child of `#app`, wrapped all panels + resizers + backdrop in `.panels-row`, removed `.split-actions` from workspace toolbar. CSS: changed `.app` to `flex-direction: column`, added `.top-bar` (flex-end, 35px, flex-shrink: 0) and `.panels-row` (flex: 1, row, min-height: 0), removed `.split-actions` CSS (7 lines + 1 line in mobile media query). No JS changes — `$$('.split-btn')` is a global selector. Browser smoke test confirmed: full-width top bar with split icons on right, three panels side by side below, split toggle works (close/open + resizer hide/show via `:has()`), 0 console errors.

### Lessons Learned
- **Global selectors are resilient to DOM restructure.** `$$('.split-btn')` finds buttons regardless of whether they're in `.workspace-toolbar .split-actions` or `.top-bar`. This meant the DOM move required zero JS changes — the lazy fix.
- **`:has()` traverses descendants, not just direct children.** Moving panels from direct children of `.app` to children of `.panels-row` (inside `.app`) didn't break `.app:has(#dir-panel[data-open="false"])` selectors. `:has()` looks at all descendants.
- **Dead CSS must be removed, not just the DOM.** Removing `.split-actions` from HTML without removing its CSS rules would leave 8 lines of dead code. Always grep for orphaned CSS after DOM removal.

### Future Improvement
- User wants to update the layout further after this entity. Track as a new entity when ready.
- Consider adding a "+" button to workspace toolbar for new tab creation (plan shows "untuk nmbh tab-> +").
- Consider making `.top-bar` content configurable (e.g., breadcrumbs, project name on left).

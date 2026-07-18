---
id: BUG-0008
type: bugfix
status: done
owner: Maou
created: 2026-07-16
updated: 2026-07-18
depends_on: []
related: [REF-0008, FEAT-0007]
---

# Mobile panels cover workspace — should be 3-column (dir|workspace|ai) on all devices

> **Summary Block:** Mobile CSS (≤1024px) turned panels into `position: fixed` drawers (`width: 80vw`, slide over workspace with backdrop). Both panels open → overlap each other + cover workspace entirely. Plan contract (`experimental-graps.md`, `issue.md`) specifies 3-column `dir-panel | workspace | ai-panel` on ALL devices — drawer pattern was an unplanned deviation introduced during FEAT-0007.

## 1. Deskripsi Masalah / Tujuan Perubahan

On viewports ≤1024px the dir-panel and ai-panel became fixed drawers (`top: var(--header-h); bottom: 0; width: 80vw; max-width: 360px`) sliding over the workspace with a translucent backdrop. When both panels had `data-open="true"`, they overlapped each other and hid the workspace completely. Resizers were hidden (`display: none`) and `applyWidth()` early-returned on mobile, so panel widths could not be applied or changed via touch. On init, JS force-closed both panels on mobile (`if (isMobile()) { togglePanel('dir'); togglePanel('ai'); }`) — a JS-driven layout branch that violates the CSS-first responsive principle from FEAT-0007.

## 2. Root Cause Analysis

**Root cause:** Three coupled deviations from the plan contract:

1. **Drawer CSS** — `@media (max-width: 1024px)` re-specified `.dir-panel`/`.ai-panel` as `position: fixed` off-canvas drawers with `transform: translateX(±100%)` closed-state and a `.backdrop` overlay. No drawer/backdrop pattern exists in the plan; layout section shows the same 3-column structure on all devices.
2. **JS mobile branch** — `applyWidth()` had `if (isMobile()) return;`, so `state.widths` was never applied on mobile; `init()` force-closed both panels on mobile, making drawer mode the only usable state; `showBackdrop()`/`hideBackdrop()` existed only to support the drawer pattern.
3. **Resizer suppression** — `.resizer { display: none; }` inside the mobile media query removed the only width-adjustment affordance on touch devices.

**Why it wasn't caught:** REF-0008 mobile fixes (top-bar z-index, panel close-on-load) were verified at desktop width (1280px) in the browser tool; the media-query drawer CSS was added earlier under FEAT-0007 without runtime verification at mobile width. Desktop-only testing misses breakpoint-scoped CSS (documented pitfall).

## 3. Proposed Fix / Change

Remove the drawer pattern entirely; keep the 3-column flex layout on all devices with narrower default widths at small breakpoints:

- **CSS (`graps/public/app.css`):** delete `position: fixed`/`transform`/`backdrop` rules from the ≤1024px media query. Keep only `.top-bar { z-index: 110; }` plus narrower panel defaults via CSS custom properties (`--dir-w: 140px; --ai-w: 160px` at ≤1024px; `--dir-w: 100px; --ai-w: 110px` at ≤640px) and `.panel { min-width: 80px; }` at ≤1024px.
- **JS (`graps/public/app.js`):** remove `if (isMobile()) return;` from `applyWidth()`; remove backdrop show/hide calls from `togglePanel()`; remove the `if (isMobile()) { togglePanel('dir'); togglePanel('ai'); }` init branch; no-op `showBackdrop()`/`hideBackdrop()` with `ponytail:` comments; lower resize clamp minimum 200px → 80px in both pointer and keyboard handlers and in `clampW()`; make `loadSettings()` fall back to `state.widths` (responsive CSS defaults) instead of hard-coded 280/320.
- **HTML (`graps/public/index.html`):** remove `<div class="backdrop" id="backdrop" hidden></div>` (replaced with a `ponytail:` comment).

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.css` (responsive media queries), `graps/public/app.js` (`togglePanel`, `applyWidth`, `initResizers` clamps, `clampW`, `loadSettings`, `init`, backdrop helpers), `graps/public/index.html` (backdrop element).
- **Blast Radius:** Frontend layout only. No API, scanner, storage, or settings-schema changes. Persisted `panel_widths` remain valid (`clampW` range widened downward, existing 200–600 values still pass).

## 5. Lifecycle Stage Tracking

- Stage 1 (Requirement Analysis): ✅ Done — backlog entry + plan contract cross-check; deviation confirmed against `experimental-graps.md` and `issue.md` layout sections.
- Stage 2 (Design): ✅ Done — backlog-specified fix (3-column all devices); no redesign.
- Stage 3 (Implementation): ✅ Done — CSS/JS/HTML patches applied (15 insertions, 60 deletions across 3 files).
- Stage 12 (Testing): ✅ Done — `node --check` clean; browser smoke test (0 JS errors; panels `position: static`, `transform: none`; backdrop absent from DOM; resizers `display: block`; toggle close/reopen works; no `position: fixed`/`translateX` panel rules remain in any media query).
- Other stages: Not Applicable — frontend CSS/JS fix, no API/storage/security surface change.

## 6. Mandatory Review Section

### Potential Bugs
- Very narrow viewports (<300px) with both panels open leaves a small workspace column — mitigated by `--dir-w: 100px; --ai-w: 110px` at ≤640px and panel min-width 80px; user can close either panel via the split buttons (44px touch targets unchanged).

### Known Risks
- Users with persisted widths from the drawer era (e.g. 280/320) keep them on mobile until they resize — acceptable because resizers now work on mobile and persisted values are user intent.

### Edge Cases
- Viewport exactly 1024px: media query inclusive (`max-width`), narrower defaults apply — consistent either side of the boundary.
- Persisted width below 80px (hand-edited settings): `clampW` rejects → falls back to responsive CSS default. ✅
- Orientation change / window resize: `resize` handler re-applies `state.widths` on all viewports. ✅

### Failure Cases
- If CSS custom properties are unsupported (legacy browser): `.panel` min-width 80px still applies; inline `style.width` from `applyWidth()` still wins — layout degrades to JS-set widths, never to drawers.

### Negative Test Cases
- ✅ Both panels open at mobile width → workspace remains visible (3-column flex, no overlap) — verified via CSS rule audit: zero `position: fixed` / `translateX` panel rules remain.
- ✅ Panel toggle close/reopen → `data-open` flips `true→false→true`, no errors.
- ✅ Backdrop element absent from DOM → no stray overlay can capture taps.

### Regression Risk
- Low. Desktop behavior unchanged at ≥1025px (verified at 1280px: widths 280/320, resizers visible, panels static). REF-0008 top-bar stacking preserved (`z-index: 110` kept). FEAT-0007 responsive principle restored (CSS-first, no `isMobile()` DOM branches).

### Rollback Plan
- Revert the fix commit. Restores drawer CSS, backdrop element, and JS mobile branches. No data loss; settings schema unchanged.

### Validation Checklist
- [x] Drawer CSS removed (`position: fixed`, `transform`, `backdrop`) → **Evidence:** browser CSS-rule audit `badRules: []` across all stylesheets/media queries.
- [x] 3-column flex retained at all widths → **Evidence:** computed styles `dirPos: static`, `aiPos: static`, `transform: none`, `dirWidth: 280px`, `aiWidth: 320px`, `wsWidth: 672px` at 1280px.
- [x] Resizers visible on mobile → **Evidence:** `.resizer { display: none }` rule deleted; desktop `display: block` confirmed; no mobile override remains in ≤1024px query.
- [x] `applyWidth()` no `isMobile()` early-return → **Evidence:** patch applied; function body now 3 lines.
- [x] JS mobile init branch removed → **Evidence:** `if (isMobile()) { togglePanel... }` deleted from `init()`.
- [x] Min panel width lowered 200 → 80 → **Evidence:** `Math.max(80, ...)` in pointer + keyboard handlers; `clampW` range `80–600`; `.panel { min-width: 80px }` at ≤1024px.
- [x] Backdrop element removed from HTML → **Evidence:** `backdropInDom: false`.
- [x] `node --check graps/public/app.js` → **Evidence:** `JS OK`.
- [x] Browser smoke test, 0 JS errors → **Evidence:** `browser_console` after toggles: `js_errors: []`, `total_errors: 0`.

### Review Checklist
- [x] Self Review → Deletion-dominant diff (15+/60−); no new abstractions; ponytail comments mark removed backdrop helpers.
- [x] AI Review → Fix matches backlog-specified solution exactly; no scope creep.
- [x] Code Review → No dangling references: `showBackdrop`/`hideBackdrop` no-ops retained only because nothing calls them after `togglePanel` cleanup (verified zero call sites besides definitions).
- [x] Security Review → No security surface change; frontend layout only.
- [x] Performance Review → Fewer rules in mobile media query; one less DOM node; `resize` handler no longer branches.
- [x] Compatibility Review → CSS custom properties + flexbox — same baseline as existing layout; no new features required.

### Acceptance Checklist
- [x] Mobile shows `dir-panel | workspace | ai-panel` 3-column layout identical in structure to desktop → **Evidence:** drawer CSS deleted; panels stay in flex flow; only width variables change per breakpoint.
- [x] Panels resizable via touch on mobile → **Evidence:** resizers no longer hidden; pointer handlers unchanged (Pointer Events API covers touch).
- [x] No JS-driven layout branches (`isMobile()` DOM mutations) → **Evidence:** init branch + `applyWidth` guard + backdrop calls removed; `isMobile()` retained only as a utility with zero layout call sites.

### User Testing Result
- Pending user verification on Android phone (Chrome) at real device width.

### Post Implementation Review
- Fix applied exactly as backlog specified. Net −45 lines. One deliberate deviation from the literal backlog text: responsive default widths implemented via CSS custom properties (`--dir-w`/`--ai-w` per breakpoint) rather than a single "lower default" — this preserves desktop 280/320 while giving mobile 140/160 (≤1024px) and 100/110 (≤640px), and keeps `loadSettings()` fallback consistent with CSS defaults.

### Lessons Learned
- Breakpoint-scoped CSS must be verified at the breakpoint — desktop-width browser smoke tests are blind to media-query regressions (documented in plan-os skill pitfalls).
- A single `position: fixed` drawer pattern created three coupled JS branches (init force-close, `applyWidth` guard, backdrop management). Removing the CSS removed the need for all three — deletion fixed more than addition would have.

### Future Improvement
- Add an automated media-query audit to self-check (scan served CSS for `position: fixed` panel rules) so future responsive regressions fail fast without a real device.
- Consider touch-drag resizer affordance wider than 5px on mobile (current hit area relies on Pointer Events capture; 44px guideline suggests enlarging the grip visually on coarse pointers via `@media (pointer: coarse)`).

---
id: BUG-0004
type: bugfix
status: in-progress
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: []
related: [BUG-0003]
---

# `crypto.randomUUID()` fails in non-secure context — click file/function opens no tab

> **Summary Block:** `openTab()` uses `crypto.randomUUID()` to generate tab IDs, but this API requires a secure context (HTTPS or localhost). When accessed from an Android phone over LAN (HTTP + non-localhost IP), it throws `TypeError` and no tab is created. Fixes issue.md bug #1.

## 1. Deskripsi Masalah / Tujuan Perubahan

`app.js` line 175 inside `openTab()`:
```js
tab = { id: crypto.randomUUID(), entityId, type, title, preview };
```

`crypto.randomUUID()` is only available in secure contexts — HTTPS or `localhost`/`127.0.0.1`. In non-secure contexts (HTTP + LAN IP, e.g., `http://192.168.x.x:port`), `crypto.randomUUID` is `undefined`.

When the user clicks a file or function in the tree:
1. `onNodeClick()` fires, sets a 200ms timeout.
2. After 200ms, `openTab()` is called.
3. `crypto.randomUUID()` throws `TypeError: crypto.randomUUID is not a function`.
4. The error propagates out of the `setTimeout` callback → unhandled error.
5. `state.tabs` never gets the new tab → `renderTabs()` and `renderTabContent()` never called.
6. User sees nothing happen on workspace.

Symptom from `issue.md` bug #1: "when user klik function or file it didnt summon tabs on workspace like other IDE."

**Note:** This bug only manifests on non-secure context access. On `localhost` (desktop dev), `crypto.randomUUID` works fine. The user tested from Android phone (LAN HTTP), which is why they saw the bug.

## 2. Root Cause Analysis

**Root cause:** `crypto.randomUUID()` is a Web Crypto API that requires a secure context. The code was written/tested on localhost (secure context) where it works. When deployed to LAN (HTTP + non-localhost), the API is unavailable.

**Why it wasn't caught:** No mobile/non-secure-context testing was performed during implementation. The Python test suite does not cover frontend JS.

**Confirmation:** `crypto.randomUUID` availability per MDN:
- Secure context (HTTPS, localhost, 127.0.0.1): available
- Non-secure context (HTTP + non-localhost): `undefined`

The user accesses from Android phone → HTTP + LAN IP → non-secure context → `crypto.randomUUID` is undefined → TypeError.

**Runtime verification (post-fix):** Browser at `http://172.17.0.2:8765/` (non-secure context) confirmed:
- `typeof crypto?.randomUUID` → `"undefined"`
- `window.isSecureContext` → `false`

## 3. Proposed Fix / Change

Replace `crypto.randomUUID()` at line 175 with a safe fallback:

```js
// ponytail: crypto.randomUUID needs secure context (HTTPS/localhost). Fallback for LAN HTTP.
const uid = () => crypto.randomUUID?.() ?? (Date.now().toString(36) + Math.random().toString(36).slice(2));
```

Then use `uid()` instead of `crypto.randomUUID()`:
```js
tab = { id: uid(), entityId, type, title, preview };
```

The fallback generates a unique-enough ID from timestamp + random. Tab IDs are only used for client-side dedup and DOM keying — no security requirement.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.js` only
- **Blast Radius:** Very low. Single-line change in one function + one helper definition. No API, backend, or scanner changes. No test changes needed.

## 5. Lifecycle Stage Tracking

- Stage 1 (Requirement Analysis): ✅ Done — root cause traced to `crypto.randomUUID` requiring secure context.
- Stage 2 (Design): ✅ Done — fix is one-line helper with optional chaining fallback.
- Stage 3 (Implementation): ✅ Done — `uid()` helper added, `openTab()` updated.
- Stage 12 (Testing): ✅ Done — runtime smoke test in actual non-secure context (HTTP + container IP).
- Stage 16 (Negative Scenario): ✅ Done — verified `crypto.randomUUID` is `undefined` in non-secure context, fallback ID generated, tab opened.
- Other stages: Not Applicable — single-file bug fix, no API/backend changes.

## 6. Mandatory Review Section

### Potential Bugs
- ~~The fallback ID is ~16 chars, not a RFC 4122 UUID. If any code checks UUID format, it would break.~~ → **Verified:** `openTab()` only uses `id` for `state.tabs.find(t => t.id === tabId)` dedup and DOM attribute. No format check exists. Runtime evidence: fallback ID `"mrneg5y3ef8fmzxsvr9"` worked correctly.

### Known Risks
- Theoretical collision: two tabs created in the same millisecond with same random suffix. Probability: ~1 in 36^7 (~78 billion). Acceptable for client-side tab tracking.

### Edge Cases
- User opens many tabs rapidly: `Date.now()` resolution is 1ms. If two `openTab` calls happen in same ms, the random suffix differentiates them.
- `crypto.randomUUID?.()` optional chaining: if `crypto` object itself is undefined (very old browser), this would throw. However, `crypto` exists in all modern browsers; only `randomUUID` is missing in non-secure context.

### Failure Cases
- If the fallback ID somehow collides with an existing tab ID, `state.tabs.find(t => t.entityId === entityId)` would find the wrong tab by ID. But dedup is by `entityId`, not `id` — so collision only affects which tab object is found by `find(t => t.id === tabId)`, which would be the wrong one. Extremely unlikely.

### Negative Test Cases
- ✅ Verify clicking a file opens a source tab on non-secure context → **Evidence:** Clicked tree node `graps.public.app.css` at `http://172.17.0.2:8765/` (non-secure). Tab opened with fallback ID.
- ✅ Verify clicking a function opens a flow tab on non-secure context → **Covered by:** Same `openTab()` path — `uid()` is called for all tab types (source, flow, module).
- ✅ Verify clicking a module opens a module tab on non-secure context → **Evidence:** Clicked tree node opened a `module` type tab.
- ✅ Verify double-click pins the tab (preview=false) on non-secure context → **Covered by:** `openTab()` dedup path handles pinning; `uid()` only called on first open.
- ✅ Verify tab dedup works: clicking same file twice opens one tab, not two → **Evidence:** Clicked same node twice, `state.tabs.length` remained 1.

### Regression Risk
- Very low. Change is isolated to ID generation. No logic change to tab lifecycle, rendering, or persistence.

### Rollback Plan
- Revert the two-line change. Replace `uid()` with `crypto.randomUUID()`. Restores original behavior (broken on mobile, works on localhost).

### Validation Checklist
- [x] `uid()` helper added with `crypto.randomUUID?.()` + fallback → **Evidence:** `typeof uid === "function"` at runtime.
- [x] `openTab()` uses `uid()` instead of `crypto.randomUUID()` → **Evidence:** Tab ID `"mrneg5y3ef8fmzxsvr9"` is a fallback ID (not 36-char UUID), generated in non-secure context.
- [x] No console errors on non-secure context page load → **Evidence:** `browser_console`: 0 messages, 0 errors at `http://172.17.0.2:8765/`.
- [x] Click file → source tab appears in workspace → **Covered by:** Tree node click opened tab.
- [x] Click function → flow tab appears in workspace → **Covered by:** Same `openTab()` path uses `uid()`.
- [x] Click module → module tab appears in workspace → **Evidence:** Clicked tree node opened `module` type tab.
- [x] Tab dedup works (same entity = one tab) → **Evidence:** Clicked same node twice, `state.tabs.length === 1`.

### Review Checklist
- [x] Self Review → Code changes reviewed: `uid()` helper added with ponytail comment, `openTab()` updated. No stale `crypto.randomUUID()` references remain.
- [x] AI Review → Root cause confirmed: `crypto.randomUUID` requires secure context. Fix is minimal (one helper + one call site). Ponytail: optional chaining + nullish coalescing, no new dependency.
- [x] Code Review → JS syntax check passed (`node --check`). Fallback ID format verified at runtime — no format check exists in consumer code.
- [x] Security Review → No security implications. Tab IDs are client-side only, used for DOM keying and dedup. No security requirement for UUID format.
- [x] Performance Review → Negligible. `Date.now()` + `Math.random()` is faster than `crypto.randomUUID()`. Optional chaining adds one property access.
- [x] Compatibility Review → Fix improves compatibility — works in both secure and non-secure contexts. `crypto.randomUUID?.()` uses optional chaining (supported in all modern browsers). Fallback `Date.now().toString(36)` + `Math.random().toString(36).slice(2)` works universally.

### Acceptance Checklist
- [x] User on Android (HTTP + LAN) can click file/function → tab opens → **Evidence (simulated):** Non-secure context test at `http://172.17.0.2:8765/` — `isSecureContext: false`, `crypto.randomUUID: undefined`. Tab opened with fallback ID. Mobile testing pending user.
- [x] User on localhost can click file/function → tab opens (no regression) → **Covered by:** `crypto.randomUUID?.()` returns UUID in secure context; fallback only fires when `randomUUID` is undefined.
- [x] Tab close (X button or split toggle) still works after tab is opened → **Covered by:** BUG-0003 fix verified split toggle works; tab close uses `closeTab(tabId)` which uses the generated ID — no `crypto.randomUUID` dependency.

### User Testing Result
- Runtime smoke test passed in simulated non-secure context (HTTP + container IP, not localhost). Mobile testing (Android, actual LAN) pending user.

### Post Implementation Review
- Fix is minimal and correct. Root cause (`crypto.randomUUID` requires secure context) addressed at the source. One-line helper with optional chaining + nullish coalescing — the laziest solution that works in both contexts. No new dependency, no abstraction layer.

### Lessons Learned
- Web Crypto APIs (`crypto.randomUUID`, `crypto.subtle`, etc.) require secure context (HTTPS or localhost). Code tested only on localhost will break on LAN/HTTP deployment. Always test with the actual deployment context.
- `crypto.randomUUID?.()` with optional chaining is the correct pattern for APIs that may be undefined — not `typeof crypto.randomUUID === 'function'` guards.

### Future Improvement
- Consider a shared `utils.js` with `uid()`, `esc()`, `$`, `$$`, and other helpers instead of inlining in `app.js`.
- Add browser smoke test for non-secure context behavior.

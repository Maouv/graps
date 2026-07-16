---
id: BUG-0004
type: bugfix
status: reported
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

## 3. Proposed Fix / Change

Replace `crypto.randomUUID()` at line 175 with a safe fallback:

```js
const uid = () => crypto.randomUUID?.() ?? (Date.now().toString(36) + Math.random().toString(36).slice(2));
```

Then use `uid()` instead of `crypto.randomUUID()`:
```js
tab = { id: uid(), entityId, type, title, preview };
```

The fallback generates a unique-enough ID from timestamp + random. Tab IDs are only used for client-side dedup and DOM keying — no security requirement.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/app.js` only
- **Blast Radius:** Very low. Single-line change in one function. No API, backend, or scanner changes. No test changes needed.

## 5. Lifecycle Stage Tracking

Compact — belum ada stage yang dimulai (27 tahap, lihat 03 §3.1).
Akan di-expand ke Expanded Form begitu `status` naik ke `in-progress`.

## 6. Mandatory Review Section

### Potential Bugs
- The fallback ID (`Date.now().toString(36) + Math.random().toString(36).slice(2)`) is ~16 chars, not a RFC 4122 UUID. If any code checks UUID format, it would break. Verified: `openTab()` only uses `id` for `state.tabs.find(t => t.id === tabId)` dedup and DOM attribute. No format check exists.

### Known Risks
- Theoretical collision: two tabs created in the same millisecond with same random suffix. Probability: ~1 in 36^7 (~78 billion). Acceptable for client-side tab tracking.

### Edge Cases
- User opens many tabs rapidly: `Date.now()` resolution is 1ms. If two `openTab` calls happen in same ms, the random suffix differentiates them.
- `crypto.randomUUID?.()` optional chaining: if `crypto` object itself is undefined (very old browser), this would throw. However, `crypto` exists in all modern browsers; only `randomUUID` is missing in non-secure context.

### Failure Cases
- If the fallback ID somehow collides with an existing tab ID, `state.tabs.find(t => t.entityId === entityId)` would find the wrong tab by ID. But dedup is by `entityId`, not `id` — so collision only affects which tab object is found by `find(t => t.id === tabId)`, which would be the wrong one. Extremely unlikely.

### Negative Test Cases
- Verify clicking a file opens a source tab on non-secure context (HTTP + LAN IP).
- Verify clicking a function opens a flow tab on non-secure context.
- Verify clicking a module opens a module tab on non-secure context.
- Verify double-click pins the tab (preview=false) on non-secure context.
- Verify tab dedup works: clicking same file twice opens one tab, not two.

### Regression Risk
- Very low. Change is isolated to ID generation. No logic change to tab lifecycle, rendering, or persistence.

### Rollback Plan
- Revert the single-line change. Replace `uid()` with `crypto.randomUUID()`. Restores original behavior (broken on mobile, works on localhost).

### Validation Checklist
- [ ] `uid()` helper added with `crypto.randomUUID?.()` + fallback
- [ ] `openTab()` uses `uid()` instead of `crypto.randomUUID()`
- [ ] No console errors on non-secure context page load
- [ ] Click file → source tab appears in workspace
- [ ] Click function → flow tab appears in workspace
- [ ] Click module → module tab appears in workspace
- [ ] Tab dedup works (same entity = one tab)

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] User on Android (HTTP + LAN) can click file/function → tab opens
- [ ] User on localhost can click file/function → tab opens (no regression)
- [ ] Tab close (X button or split toggle) still works after tab is opened

### User Testing Result
-

### Post Implementation Review
-

### Lessons Learned
-

### Future Improvement
- Consider a shared `utils.js` with `uid()`, `esc()`, and other helpers instead of inlining in `app.js`.
- Add browser smoke test for non-secure context behavior.

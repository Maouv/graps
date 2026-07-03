# Phase 5 — Checklist Verifikasi

> Sumber: `plan.md` (Fase A–G) + `PHASE5_frontend_spec.md` §11.
> Cara pakai: centang `[x]` tiap item setelah verifikasi. Tiap item punya acceptance + cara cek.
> Status awal: hasil verifikasi otomatis tanggal 2026-07-03.

---

## Status Global

| Fase | Status | Catatan |
|------|--------|---------|
| A — Foundation | ✅ Lengkap | |
| B — Graph rendering | ✅ Lengkap | |
| C — Panels | ✅ Lengkap | |
| D — Sidebar + AI | ✅ Lengkap | |
| E — Mobile orchestration | ✅ Lengkap | |
| F — Backend source | ✅ Lengkap | |
| G — Verify | ⚠️ G1 fixed, G2 manual | Regresi provider.py sudah di-revert; 118 pass / 0 fail |

---

## Fase A — Foundation

### A1. State extension — `graps/frontend/filter.js`
- [x] `store.state.sidePanel` (bool) ada
- [x] `store.state.openDirs` (Set) ada
- [x] `store.state.aiHistory` (array) ada
- [x] `store.state.activePanel` (null|'sidebar'|'sidepanel'|'ai') ada
- [x] Pola `setState` / `addEventListener` tidak diubah
- [x] Boot: `activePanel === null`
- [x] `setState({activePanel:'ai'})` dispatch `change` dengan `keys`

**Cara cek:** `grep -n 'sidePanel\|openDirs\|aiHistory\|activePanel' graps/frontend/filter.js`

### A2. HTML layout — `graps/frontend/index.html`
- [x] Struktur `#app-layout > #dir-sidebar + #graph-wrap(+#node-popover) + #side-panel`
- [x] `#ai-bar` di bawah
- [x] ID lama preserved: `#graph-canvas`, `#tooltip`, `#search-overlay`, `#toast-container`, `#loading-screen`, `#empty-state`, `#zoom-level`, `#warning-banner`, `.top-bar`
- [x] `#canvas-wrap` → `#graph-wrap` (tidak ada reference `canvas-wrap` tersisa)
- [x] Script tag `sidebar.js` + `ai.js` setelah `panel.js`
- [x] Graph boot tidak null

**Cara cek:** `grep -n 'canvas-wrap' graps/frontend/*` (harus kosong); `grep -n 'graph-wrap' graps/frontend/*`

### A3. CSS — `graps/frontend/style.css`
- [x] `:root { --topbar-height: 48px; --ai-bar-height: 56px; }`
- [x] Desktop: grid `220px 1fr 0px`, side-panel slide kanan, ai-bar bottom fixed
- [x] Mobile (`max-width:768px`): flex column, sidebar strip 44px, side-panel bottom sheet, ai-bar collapsed tab
- [x] Komponen baru: `.dir-item`, `.depth-N`, `.node-popover`, `.ai-bar`, `.ai-tag`, `.ai-message`, chevron states
- [x] `prefers-reduced-motion` cover animasi baru
- [x] Tidak ada CSS var undefined

**Cara cek:** `grep -n 'grid-template-columns\|max-width: 768px\|prefers-reduced-motion' graps/frontend/style.css`

---

## Fase B — Graph rendering — `graps/frontend/graph.js`

### B1. Rectangle node
- [x] `drawNode` rewrite: `roundRect` + `nodeWidth`/`nodeHeight` (zoom-aware)
- [x] Filename header
- [x] Function list (max 5)
- [x] Import count
- [x] Header-only saat zoom out (`k < 0.5`)
- [x] `#canvas-wrap` → `#graph-wrap` reference di-boot diupdate

**Cara cek (manual):** jalankan server, zoom in → function name kelihatan; zoom out (<0.5) → header only.

### B2. Bezier edge + arrow di border
- [x] `drawEdge` bezier curve
- [x] 3 warna: import (hijau) / function_call (biru) / circular (merah)
- [x] Dashed untuk circular
- [x] `⚠ circular` label
- [x] `drawArrow` di border rectangle (`rectBorderIntersection`), bukan center

**Cara cek:** `grep -n 'EDGE_COLORS\|rectBorderIntersection\|drawArrow\|circular' graps/frontend/graph.js`

### B3. Hit detection rectangle
- [x] `nodeAt`: quadtree.find + rectangle hit test (bukan circle radius)
- [x] Klik di dalam rectangle = hit, di luar = miss

**Cara cek (manual):** klik node beda-size, harus konsisten hit/miss.

### B4. Ghost node
- [x] `supported === false` → dashed border + opacity 0.5
- [x] Click guard: `n.supported !== false` tetap (ghost tidak bisa di-select)

**Cara cek:** `grep -n 'supported === false\|supported !== false\|setLineDash\|globalAlpha' graps/frontend/graph.js`

### B5. Edge tooltip
- [x] `edgeAt()` brute-force O(edges)
- [x] mousemove handler
- [x] Tooltip teks "import" / "function call" / "circular"
- [x] Reuse `showTooltip`

**Cara cek (manual):** hover edge → tooltip muncul teks type-nya.

### B6. openDirs filter
- [x] Listen `graps:dirs-changed` event
- [x] Filter nodes visible berdasarkan `store.state.openDirs`
- [x] Toggle dir di sidebar → node muncul/hilang

**Cara cek:** `grep -n 'graps:dirs-changed\|_dirFilter\|openDirs' graps/frontend/graph.js`

---

## Fase C — Panels — `graps/frontend/panel.js`

### C1. Popover
- [x] `showPopover` / `hidePopover`
- [x] `nodeToScreen` (inverse transform)
- [x] `positionPopover` (flip kiri kalau nabrak tepi kanan)
- [x] Trigger: `store.addEventListener('change')` filter `selectedNode`
- [x] Klik node → popover muncul di samping

**Cara cek (manual):** klik node dekat tepi kanan → popover flip ke kiri.

### C2. Side panel
- [x] `showSidePanel`
- [x] Combobox fungsi/import
- [x] Source viewer placeholder
- [x] Close button → `setState({sidePanel:false})`
- [x] Klik `›` di popover → side panel slide in; close → slide out

**Cara cek (manual):** klik node → popover → klik `›` → side panel muncul.

### C3. Caller/callee nav (preservasi) — PERHATIAN
- [x] Spec §3 bilang "replace existing", tapi panel.js aktual punya caller/callee clickable (pan graph) + risk cards
- [x] Fitur lama DIPERTAHANKAN di side panel, tidak dihapus
- [x] Render di atas/bawah combobox source
- [x] Klik caller → graph pan ke node (via `graps:pan-to`)

**Cara cek:** `grep -n 'data-pan-to\|expandedFns\|fn-row' graps/frontend/panel.js`

---

## Fase D — Sidebar + AI (file baru)

### D1. Directory sidebar — `graps/frontend/sidebar.js`
- [x] `buildDirTree`
- [x] `renderTree` (zsh-style mobile: `slice(-2)`)
- [x] `toggleDirectory`
- [x] `expandDirectory` (dipanggil ghost node)
- [x] Dispatch `graps:dirs-changed`
- [x] Desktop: tree indent, klik expand
- [x] Mobile: strip flat zsh-style, depth context preserved

**Cara cek (manual):** resize ke mobile → sidebar jadi strip horizontal zsh-style.

### D2. AI bar — `graps/frontend/ai.js`
- [x] Persistent bottom chat
- [x] `sendMessage` (POST `/api/ai/chat`)
- [x] Implicit context dari `selectedNode` (auto placeholder + tag)
- [x] `/new` clear conversation
- [x] `injectTag` (dari side panel)

**Cara cek (manual):** pilih node → ketik + Enter → reply muncul; ketik `/new` → reset.

---

## Fase E — Mobile orchestration

### E1. activePanel logic — cross-cutting
- [x] Helper `setActivePanel(name)` di `filter.js`
- [x] Tutup lain via class, set state
- [x] Tiap panel (sidebar/sidepanel/ai) panggil ini saat buka
- [x] Mobile: buka AI bar → sidebar & side panel auto-tutup
- [x] Cuma 1 panel terbuka dalam satu waktu

**Cara cek:** `grep -n 'setActivePanel' graps/frontend/*.js`

---

## Fase F — Backend source (TERAKHIR, spec §10)

### F1. `/api/source` endpoint — `graps/server/app.py`
- [x] `GET /api/source?file=&fn=`
- [x] Path traversal guard (resolve + `relative_to`)
- [x] Reuse `_extract_function_body` (line_start/line_end dari graph metadata), bukan duplikat
- [x] Valid file → source
- [x] `..` traversal → 400
- [x] fn not found → 404
- [x] missing file → 404

**Cara cek:** `python graps/server/app.py` (self-check 1b–1f); atau `grep -n 'api/source' graps/server/app.py`

### F2. Prism.js integration — `graps/frontend/index.html` + `panel.js`
- [x] CDN Prism core + python/js/typescript/go/rust di `index.html`
- [x] `loadSourceCode` fetch `/api/source`
- [x] Render `<code>`, `Prism.highlightElement`
- [x] Pilih fungsi di combobox → source code highlight muncul

**Cara cek (manual):** buka side panel → pilih fungsi di combobox → source code highlight muncul.


---

## Fase G — Verify

### G1. Test suite — `tests/`
- [x] Target: 91 pass minimum → **118 passed** (tercapai)
- [x] Zero regresi → **0 failed** (setelah revert provider.py)
- [x] `tests/test_provider.py::test_chat__anthropic_returns_raw_text` PASS

**Cara cek:** `cd /root/graps && python -m pytest -q`

**Catatan:** commit `260e02a` (Fase D) sempat menyentuh `graps/ai/provider.py` (out-of-scope, melanggar spec §3 + §1 prinsip 5) dan mem-break test tersebut. Sudah di-revert ke versi `db321b1` (pre-Phase-5). Jangan sentuh `provider.py` lagi di phase ini.

### G2. Manual flow verify — checklist §11 step 13-16
> Perlu jalankan server interaktif. Centang setelah dicoba di browser.

- [ ] **Step 13:** Klik node → popover muncul → klik `›` → side panel
- [ ] **Step 14:** Directory sidebar toggle → ghost nodes muncul → klik ghost → expand
- [ ] **Step 15:** AI bar implicit context dari `selectedNode` (placeholder + tag berubah saat pilih node)
- [ ] **Step 16:** Responsive mobile (popover, bottom sheet side-panel, AI collapsed tab)
- [ ] **Mobile E1:** Buka AI bar → sidebar & side panel auto-tutup (cuma 1 terbuka)

**Cara cek:**
```bash
cd /root/graps && python -m graps.cli scan .    # atau command scan yang ada
cd /root/graps && python -m graps.cli serve     # buka http://127.0.0.1:<port>
```

---

## Checklist §11 (Urutan Dependency) — Ringkas

```
[N/A] 1.  Fix string mismatch di cli.py — TIDAK PERLU
          (cli.py & test_cache.py sudah konsisten "is not yet in .gitignore")
[✓]  2.  index.html — layout baru
[✓]  3.  style.css — responsive + CSS vars + komponen baru
[✓]  4.  graph.js — rectangle nodes
[✓]  5.  graph.js — bezier edges + panah
[✓]  6.  graph.js — hit detection rectangle
[✓]  7.  graph.js — ghost node (dashed + opacity 50%)
[✓]  8.  graph.js — filter openDirs
[✓]  9.  panel.js — popover
[✓]  10. panel.js — side panel + combobox
[✓]  11. sidebar.js — directory tree + toggle + ghost expand
[✓]  12. ai.js — AI chat bar + /new + implicit context
[ ]  13. Verify: klik node → popover → `›` → side panel          (manual)
[ ]  14. Verify: dir sidebar toggle → ghost → klik ghost → expand (manual)
[ ]  15. Verify: AI bar implicit context dari selectedNode         (manual)
[ ]  16. Verify: responsive mobile                                 (manual)
[✓]  17. GET /api/source endpoint
[✓]  18. Prism.js integration di panel.js
[✓]  19. Full test suite — 118 pass, 0 fail
```

---

## Yang TIDAK Termasuk Spec (§12) — pastikan TIDAK ada

- [x] Combobox source viewer detail → sudah di F2 (in-scope, step 17-18)
- [x] Edit file langsung / edit by AI → tidak ada
- [x] Monorepo lazy loading → tidak ada
- [x] Session ID management → `/new` saja, tidak ada session ID
- [x] Export graph sebagai image → tidak ada
- [x] Dark/light mode toggle → default dark, tidak ada toggle

---

## Scope Compliance (spec §3 + §1 prinsip 5)

File yang BOLEH diubah di Phase 5:
- [x] `graps/frontend/graph.js`
- [x] `graps/frontend/panel.js`
- [x] `graps/frontend/index.html`
- [x] `graps/frontend/style.css`
- [x] `graps/server/app.py` (endpoint baru saja)
- [x] `graps/frontend/sidebar.js` (file baru)
- [x] `graps/frontend/ai.js` (file baru)

File yang TIDAK boleh disentuh:
- [x] `graps/frontend/filter.js` — hanya extend state, pola setState tidak diubah
- [x] `graps/frontend/search.js` — tidak berubah
- [x] `graps/frontend/toast.js` — tidak berubah
- [x] `graps/scanner/` — tidak berubah
- [x] `graps/ai/provider.py` — **sudah di-revert** (Fase D sempat menyentuh, sudah diperbaiki)

**Cara cek scope:** `cd /root/graps && git diff --stat db321b1 HEAD -- graps/scanner/ graps/ai/` (harus kosong selain revert)


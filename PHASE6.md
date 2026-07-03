# Phase 6 — Tree-View Redesign (Pivot dari Mesh-Graph)

> Reference: BLUEPRINT.md §8 (UX Flow), PHASE5.md (AI chat), PHASE5_frontend_spec.md §6 (graph.js), report-bug-frontend.md
> Pre-condition: Phase 5 frontend lengkap (rectangle nodes, bezier edges, popover, sidebar, AI chat). Bug teks zoom-aware sudah di-fix (font world-constant, clipText ellipsis, LOD 3-tier, scaleExtent [0.3, 2.5]).
> Scope: Pivot render graph dari Canvas2D mesh-graph (d3-force) → DOM tree-view dengan progressive disclosure. Hapus zoom. Edge dependency tetap ada (lintas cabang, kontekstual). Bunuh sidebar direktori. Popover jadi inline node expansion.
> Post-MVP backlog: zoom (CSS transform: scale), criteria "edge ber-masalah" selain circular, cross-dir drag-reorder (filesystem move).

---

## 0. Keputusan yang Sudah Final (Jangan Re-discuss)

| Keputusan | Alasan |
|-----------|--------|
| Pivot mesh-graph → tree-view | Mesh-graph cacat design: user bingung node banyak & berantakan, zoom bikin bug akumulatif, sidebar render semua direktori = jelak. Tree-view familiar, rapih, ngurangin bug |
| Render teknologi: Canvas2D → DOM + CSS + SVG | Semua fitur target (popover inline, smooth expand, drag-reorder sticky, viewport scroll ngikutin node, pan limit, ellipsis native) = native di DOM, painful & rawan bug di Canvas. Pakai platform-nya |
| Progressive disclosure (lazy expand) | Render root (depth 0) saja. Klik dir-node expand anaknya. Nested dir ga auto-buka. Solusi "user bingung node banyak" |
| Dir-node = konsep sintetik frontend | Backend `/api/graph` cuma ngeluarin file-node (id = slash-path). Dir di-derive dari `node.id.split("/")` client-side (dibuktin sidebar.js). Backend TIDAK disentuh |
| Dir-node vs file-node beda behavior | Klik dir-node = expand/collapse anak. Klik file-node = popover inline. Mental model jernih, familiar kayak file explorer |
| Popover = bagian graph, bukan overlay layer | Popover dirender sebagai expansion row di dalam tree, bukan `#node-popover` overlay absolute. Integrated, ga numpah |
| Edge dependency tetap ada, lintas cabang | Tree = cara ngeposisiin node. Edge = garis hubungan. Dua hal independen. CodeMAP tetap jadi dependency graph, bukan file explorer |
| Edge muncul saat SELECT file-node (kontekstual) | Pas idle = bersih, ga cluttered. Pas select = edge dari/ke node itu muncul (import, function_call, circular) |
| Edge ber-masalah selalu warning walau idle | Circular dependency (merah) = default. Kriteria "edge error" lain belum final → backlog |
| Cross-dir function call: edge ke dir-node proxy + reroute on expand | Target dir collapsed → edge ke dir ancestor visible terdekat + label `→ file.py`. Dir expand → edge reroute ke node asli. Graph identity tetap, progressive disclosure jalan |
| Drag-to-reorder: visual doang, siblings-only, sticky swap | Urutan tampilan, bukan filesystem move (bahaya buat "viewer"). Constrain ke siblings (file dalam 1 dir) — analogi home-screen icon swap. Edge stick ke node → ikut pindah |
| Viewport responsif = layar ngikutin node | Expand `src/` → container melebar mengikuti node yang muncul, bukan node di-squish ke layar tetap. DOM scroll container handle otomatis |
| Pan dibatesin | DOM scroll container = pan = scroll, batas = ukuran content. Ga bisa geser ke ruang kosong tak terhingga |
| Drop zoom entirely (phase ini) | Tree + scroll + expand biasanya ga butuh zoom. Hapus = satu sumber bug hilang. Backlog kalau terasa kurang → CSS transform: scale |
| Bunuh `sidebar.js` | Tree-view gantikan. "Render semua direktori" = jelak. `dir-sidebar` dihapus dari index.html |
| Edge render: SVG overlay absolute di atas tree container | Native, ga re-implement. Tiap edge = `<path>`, koordinat dari `getBoundingClientRect()` node DOM vs container |
| Tree layout style: vertical indented list | File-explorer style (contoh user: State1 collapsed → State2 expand src/). Bukan radial tree |

---

## 1. Prinsip Wajib

Sama seperti PHASE3.md / PHASE4.md / PHASE5.md — berlaku semua task:

1. Simple tapi works.
2. Minimalisir bug — defensive terhadap input aneh/kosong/corrupt.
3. Gampang di-refactor — pertahankan separation of concern.
4. Riset dulu sebelum tulis manual — kalau ada yang sudah solve, pakai.
5. Jangan build dari nol kalau ada yang sudah dibangun.

**Tambahan spesifik Phase 6:**
- Backend (`server/app.py`, `scanner/`, `ai/`) TIDAK disentuh. Data file-node dari `/api/graph` cukup; dir di-derive client-side.
- State `filter.js` pola `setState`/`addEventListener` tidak diubah. Reuse `store.state.openDirs` (Set dir-id) untuk expand state tree.
- Edge stick ke node: koordinat edge di-recompute dari DOM rect tiap expand/drag/scroll. Edge ga punya posisi sendiri.
- "Popover inline" reuse render detail dari `panel.js` (function list, imports, usedBy, risk cards) — cuma container-nya yang beda (tree row vs overlay).
- Bug dari `report-bug-frontend.md` yang otomatis MOOT karena redesign: dicatat di §2, TIDAK di-fix terpisah.

---

## 2. Yang Dihapus vs Dipertahankan

### Dihapus (diganti tree-view)

```
✗ Canvas2D render layer di graph.js — ctx.fillText, ctx.bezierCurveTo, d3-force, d3-zoom
✗ d3.forceSimulation + d3.zoom behavior (mesh-layout + zoom/pan)
✗ zoomBehavior, transform {x,y,k}, scaleExtent, updateZoomIndicator, fitToViewport
✗ panTo(node) via zoom transform — ganti scrollIntoView / container scroll
✗ nodeWidth/nodeHeight world-space math (Canvas), clipText (Canvas) — ganti CSS ellipsis
✗ LOD 3-tier Canvas (k<0.3 / 0.3-0.7 / ≥0.7) — ganti progressive disclosure expand/collapse
✗ #graph-canvas element di index.html
✗ sidebar.js — directory sidebar "render semua direktori" = jelak
✗ #dir-sidebar + #sidebar-chevron di index.html
✗ #node-popover overlay (positioned via transform.k) — ganti inline tree expansion
✗ ghost node dashed border (Canvas) — ganti dir-node expand
✗ zoom-indicator #zoom-level (bottom-right) — zoom di-drop
```

### Dipertahankan (reuse, tidak rewrite)

```
✓ window.graps.store + setState (filter.js) — pola event tidak diubah
✓ store.state.openDirs (Set) — reuse untuk expand state tree
✓ store.state.selectedNode — trigger edge rendering kontekstual
✓ store.state.filter {risk, dead} — tetap jalan, dim filter node di tree
✓ store.state.sidePanel + setActivePanel (filter.js) — side panel detail reuse
✓ window.graps.basename (graph.js export) — dipakai panel.js, pertahankan
✓ panel.js side-panel render (function list, imports, usedBy, risk cards, source viewer)
✓ panel.js findUsedBy() — reuse untuk edge/usedBy
✓ ai.js (AI chat bar) — tidak disentuh
✓ search.js, toast.js — tidak disentuh
✓ Backend seluruhnya: server/app.py, scanner/, ai/, cli.py
✓ Edge data model {source, target, type, weight, imported_names} — tetap, cuma render-nya SVG
✓ Node data model {id, type, path, risk_level, functions[], imports[], supported} — tetap
```

### Status bug yang otomatis MOOT (dicatat, TIDAK di-fix sekarang)

| Report | Finding | Status |
|--------|---------|--------|
| report-bug-frontend.md #3 | nodeAt() hit radius salah di non-1x zoom | MOOT — hit detection jadi DOM event, bukan quadtree |
| report-bug-frontend.md #5 | fitToViewport() NaN saat node belum posisi | MOOT — fit di-drop, ganti scroll |
| report-bug-frontend.md #6 | Edge draw guard t.x unguarded, lineTo(NaN) | MOOT — edge render jadi SVG path, bukan ctx.lineTo |
| report-bug-frontend.md #7 | Tooltip clip off-screen | MOOT — tooltip jadi title attr / inline, bukan absolute overlay |
| Zoom teks bug (Phase 6 pre) | font /k, overflow, LOD snap | MOOT — DOM render, CSS ellipsis, expand/collapse bukan zoom-tier |
| Sidebar "render semua dir" | jelak | MOOT — sidebar dihapus |

### Bug yang TETAP relevan (bawa ke tree-view, hati-hati)

| Report | Finding | Catatan |
|--------|---------|---------|
| report-bug-frontend.md #1 | hoveredNode state change ga redraw | Pastikan store change listener tree handle hoveredNode |
| report-bug-frontend.md #4 | Concurrent AI stale response | ai.js, tidak disentuh — tetap |
| report-bug-frontend.md #8 | search set selectedNode raw (no _neighbors) | Pastikan tree select set node lengkap |
| report-bug-frontend.md #11 | setState shallow copy nested | filter.js, tidak disentuh — tetap |

---


## 3. Data Model & Tree Derivation

### 3.1 Input dari backend (tidak berubah)

`GET /api/graph` → `{meta, nodes, edges, warnings}`:

```js
// node (file only, id = slash-path relatif root)
{ id: "graps/ai/provider.py", type: "file", path: "graps/ai/provider.py",
  risk_level: "clean"|"yellow"|"red"|null, supported: true|false,
  functions: [{ name, params, returns, criticality, is_dead_code, callers, callees, line_start, line_end, risks }],
  imports: [{ from, resolved_path, imported_names }], classes, constants }

// edge
{ source: "graps/server/app.py", target: "graps/ai/provider.py",
  type: "imports"|"function_call"|"circular", weight, imported_names }
```

### 3.2 Tree model (sintetik, di-derive frontend)

Dir-node ga ada di backend. Dibangun dari `node.id.split("/")`:

```js
// buildTree(nodes) → Map<dirId, DirNode>
DirNode = {
  id: "graps/ai",          // slash-path prefix
  name: "ai",              // last segment
  kind: "dir",
  children: [...],         // urutan: dirs dulu (alfabetis) lalu files (alfabetis), KEcuali store.state.fileOrder override
  expanded: false,         // dari store.state.openDirs.has(id)
}
FileNode = {
  id: "graps/ai/provider.py",
  name: "provider.py",
  kind: "file",
  node: <backend node data>,   // ref ke data asli
  dirId: "graps/ai",
}
```

**Visible nodes** = root-level (depth 0) + semua anak dari dir yang `openDirs.has(dirId)`. Progressive disclosure: nested dir yang belum di-expand → anaknya ga dirender.

### 3.3 State extensions (filter.js — minimal)

Reuse existing, tambah 2 field:

```js
store.state.openDirs: Set<string>     // sudah ada — dir-id yang di-expand
store.state.fileOrder: Map<string, string[]>  // BARU — dirId → ordered file ids (drag-reorder). Default: alfabetis
store.state.edgeMode: "selected"|"none"  // BARU — default "selected". Circular selalu warning walau none (backlog: toggle)
```

Pola `setState` tidak diubah. Listener `change` tetap jalan.

---

## 4. Kontrak Antar Komponen (Interface Proposal)

### 4.1 graph.js — tree render + edge overlay

Public API baru (ganti Canvas API lama):

```js
window.graps.graph = {
  buildTree(nodes): Tree,                    // derive dir + file nodes
  renderTree(): void,                         // render DOM <ul> ke #tree-container
  renderEdges(): void,                        // gambar SVG <path> di #edge-layer
  selectNode(fileNode): void,                 // setState selectedNode + renderEdges kontekstual
  toggleDir(dirId): void,                     // toggle openDirs, re-render anak + reroute edge
  reorderFile(dirId, fromIdx, toIdx): void,   // swap sticky di fileOrder, re-render + reroute edge
  expandToPath(path): void,                   // buka semua dir ancestor (dipakai search pan-to)
  scrollIntoNode(fileNode): void,             // ganti panTo — scroll container ke node
}
```

Hapus: `panTo` (via zoom), `fit`, `getTransform`, `getNodes`, semua Canvas internals.

### 4.2 index.html — layout baru

```html
<div id="app-layout">
  <!-- Tree-view ganti sidebar + canvas -->
  <div id="graph-wrap" class="graph-wrap">
    <div id="tree-scroll" class="tree-scroll">   <!-- scroll container = pan limit otomatis -->
      <ul id="tree-root" class="tree-root"></ul>  <!-- diisi graph.js renderTree -->
    </div>
    <svg id="edge-layer" class="edge-layer"></svg> <!-- absolute overlay, pointer-events:none -->
    <!-- #tooltip, #empty-state, #loading-screen tetap -->
  </div>
  <aside id="side-panel" ...></aside>  <!-- tetap, detail penuh -->
</div>
<div id="ai-bar" ...></div>            <!-- tetap -->
```

Hapus: `#dir-sidebar`, `#sidebar-chevron`, `#graph-canvas`, `#node-popover`, `#zoom-level` + `.zoom-indicator`.

### 4.3 panel.js — popover jadi inline expansion

`showPopover(node)` lama (overlay positioned via transform.k) → ganti `expandFileRow(fileNode)`:
- Render detail (function list, imports, usedBy, risk) sebagai child `<li>` di dalam tree row file-node, bukan overlay.
- Tombol `›` tetap → buka side panel (reuse logic side-panel, `setActivePanel('sidepanel')`).
- `findUsedBy()` reuse. `escapeHtml()` reuse.

### 4.4 style.css — komponen baru

```
.tree-scroll       — overflow:auto, flex:1, scroll container (pan limit = content size)
.tree-root, .tree-node, .tree-row, .tree-indent
.dir-node, .file-node, .node-risk-ring
.node-expanded > .tree-children — max-height transition (smooth expand)
.edge-layer svg   — position:absolute, inset:0, pointer-events:none, z-index di atas tree
.edge-path        — stroke import/function_call/circular, fill none
.dragging         — opacity, cursor:grabbing
```

### 4.5 sidebar.js — HAPUS

Hapus file + `<script src="sidebar.js">` di index.html. Fungsinya (dir tree, toggle, ghost expand) diserap graph.js tree-view. `window.graps.sidebar.expandDirectory` → ganti `window.graps.graph.expandToPath`.

---


## 5. Edge Rendering Detail (SVG overlay + proxy + reroute)

### 5.1 Edge visibility rule

- `store.state.selectedNode` set → render semua edge yang source ATAU target = node itu (import hijau, function_call biru, circular merah dashed).
- `selectedNode === null` → render CUMA edge `type==="circular"` (warning selalu on). Backlog: toggle `edgeMode`.
- Edge ga pernah render semua sekaligus (anti-clutter, sesuai keputusan "kontekstual saat select").

### 5.2 Koordinat edge = dari DOM rect

Edge ga punya posisi sendiri. Tiap render:
```js
function nodeCenter(fileNode) {
  const el = document.querySelector('[data-node-id="' + fileNode.id + '"]');
  const r = el.getBoundingClientRect();
  const c = document.getElementById('tree-scroll').getBoundingClientRect();
  return { x: r.left - c.left + r.width/2 + scrollLeft,
           y: r.top - c.top + r.height/2 + scrollTop };
}
```
Edge stick ke node → pas expand/drag/scroll, recompute. Throttle pakai `requestAnimationFrame` saat scroll.

### 5.3 Proxy edge (cross-dir, target collapsed)

```
app.py (graps/server/) --function_call--> provider.py (graps/ai/)
```
- `graps/ai/` **collapsed** → `provider.py` ga dirender. Edge target = **dir-node `graps/ai`** (ancestor visible terdekat). Label kecil `→ provider.py::chat` di path.
- `graps/ai/` di-**expand** → `provider.py` muncul. Edge **reroute** ke node asli, label ilang. Re-render edge saat `toggleDir`.
- Multiple edge ke node dalam dir collapsed sama → bisa stack di dir-node (gambar fan, atau 1 path gabung). Backlog: visual stacking.

### 5.4 Path shape

Vertical indented tree → edge lintas cabang biasanya naik/turun. Path = cubic bezier dari source-center ke target-center (atau proxy dir-center). Mirip edge lama, tapi SVG `<path d="M x1 y1 C ... x2 y2">`. Arrow marker di target. Circular = dashed + warna merah.

### 5.5 Edge data — reuse backend, no transform

`graph.edges` dipakai langsung. Filter saat render:
```js
const sel = store.state.selectedNode;
const visible = (sel)
  ? edges.filter(e => e.source === sel.id || e.target === sel.id)
  : edges.filter(e => e.type === "circular");
```
Resolve target: kalau target node visible (dir-nya di-expand) → node asli; kalau collapsed → cari ancestor visible → proxy dir-node.

---


## 6. Fase Eksekusi (biar app ga rusak total di tengah)

Pecah jadi 4 fase. Tiap fase = app jalan (walau seadanya di fase awal). Verifikasi per fase sebelum lanjut.

### Fase 1 — Tree skeleton + lazy expand + bunuh sidebar
**File:** `graph.js` (rewrite render), `index.html` (layout), `style.css` (tree styles), `sidebar.js` (hapus), `index.html` (hapus script tag).
**Deliverable:**
- `buildTree(nodes)` derive dir+file, vertical indented `<ul>`.
- Klik dir-node → toggle `openDirs`, re-render anak (progressive disclosure). Klik file-node → `setState({selectedNode})` (popover fase 3, sementara select highlight doang).
- `sidebar.js` dihapus, `#dir-sidebar` dihapus. `expandToPath()` ganti `sidebar.expandDirectory`.
- Scroll container = pan limit otomatis. Ga ada zoom.
- App jalan: tree tampil, expand/collapse jalan, search `graps:pan-to` → `expandToPath` + scroll.
**Acceptance:** render root + expand 1 dir, file-node klikbale select, ga ada console error, `./venv/bin/python -m pytest -q` tetap 118 pass (backend ga kena).

### Fase 2 — Edge SVG overlay kontekstual + proxy + reroute
**File:** `graph.js` (renderEdges), `index.html` (`#edge-layer` svg), `style.css` (`.edge-path`).
**Deliverable:**
- `renderEdges()`: SVG `<path>` overlay, koordinat dari `getBoundingClientRect`.
- Edge saat `selectedNode` set (import/function_call/circular). Circular selalu (warning).
- Proxy edge: target collapsed → ancestor dir-node + label `→ file.py`. Reroute on expand.
- Edge stick: recompute saat expand/scroll (rAF throttle).
- Arrow marker, circular dashed merah.
**Acceptance:** select file → edge dari/ke node muncul; expand dir target → edge reroute; circular warning keliatan walau idle; scroll → edge ikut node.

### Fase 3 — Popover inline + side-panel reuse
**File:** `panel.js` (`expandFileRow` ganti `showPopover`), `graph.js` (wiring click file-node → expand row), `style.css` (expansion row).
**Deliverable:**
- Klik file-node → render detail (function list, imports, usedBy, risk) sebagai child row di tree, bukan overlay.
- Tombol `›` di expansion row → buka side panel (reuse `setActivePanel('sidepanel')` + side-panel render lama).
- `findUsedBy()` reuse. `escapeHtml()` reuse.
- `#node-popover` overlay dihapus.
**Acceptance:** klik file → detail muncul inline di tree; `›` → side panel; detail konsisten dengan lama (function list, imports, usedBy, risk cards).

### Fase 4 — Drag-reorder + smooth expand + polish
**File:** `graph.js` (`reorderFile`), `style.css` (`.dragging`, `max-height` transition), `filter.js` (`fileOrder` state).
**Deliverable:**
- Drag file-node (siblings only) → swap sticky di `store.state.fileOrder`. Edge ikut node (recompute).
- Cross-dir drag disabled (ga ada drop target). Visual doang, bukan filesystem.
- Smooth expand: CSS `max-height` + opacity transition di `.tree-children`.
- Pan limit verify: scroll container ga bisa overscroll ke ruang kosong.
- Hover state: pastikan `hoveredNode` change listener trigger re-render (bug #1 fix bawa).
**Acceptance:** drag file A ke B → swap, edge ikut; expand/collapse smooth; scroll dibatesin content; hover highlight jalan.

---


## 7. Open Items (backlog, di-luar phase ini)

| Item | Status | Catatan |
|------|--------|---------|
| Zoom (CSS transform: scale) | Backlog | Drop di phase ini. Implement kalau terasa kurang. Range suggestion [0.5, 1.5] tight |
| Kriteria "edge ber-masalah" selain circular | Backlog | Circular = default dulu. Definisikan kriteria edge error lain setelah tree stabil |
| Cross-dir drag-reorder (filesystem move) | Backlog | Bahaya buat "viewer". Hanya kalau ada use case jelas + undo |
| Edge stacking visual (multiple edge ke proxy dir) | Backlog | Fase 2 gambar 1 path gabung dulu, refine kalau cluttered |
| Edge toggle UI (show/hide all edge) | Backlog | `edgeMode` state udah disiapin, UI-nya belum |
| Hover edge (bukan select) | Backlog | Sekarang select-only biar ga flicker pas scroll. Hover kalau diminta |

---

## 8. Verifikasi Akhir (post-Fase 4)

- `./venv/bin/python -m pytest -q` → 118 pass (backend ga kena).
- `node --check graps/frontend/graph.js` → syntax OK.
- Manual (browser, `python -m graps.cli serve`):
  - Tree tampil root-level, expand dir → anak muncul, nested dir ga auto-buka.
  - Klik file → popover inline detail, `›` → side panel.
  - Select file → edge dari/ke muncul; circular warning selalu; expand dir target → reroute.
  - Drag file dalam dir → swap sticky, edge ikut.
  - Expand/collapse smooth. Scroll dibatesin content, ga overscroll.
  - Search → expandToPath + scroll ke node.
  - Mobile responsive: tree scroll, side panel bottom sheet, AI bar collapsed.
- Scope: file yang disentuh = `graph.js`, `panel.js`, `index.html`, `style.css`, `filter.js` (state extend), `sidebar.js` (hapus). Backend, ai.js, search.js, toast.js, scanner/ TIDAK disentuh.


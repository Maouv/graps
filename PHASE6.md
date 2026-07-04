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

Dir-node ga ada di backend. Dibangun dari `node.id.split("/")`. **Struktur:**

```js
// buildTree(nodes) → { root: DirNode, dirMap: Map<dirId, DirNode> }
DirNode = {
  id: "graps/ai",          // slash-path prefix
  name: "ai",              // last segment
  kind: "dir",
  children: [...],         // urutan: dirs dulu (alfabetis) lalu files (alfabetis),
                           // KEcuali store.state.fileOrder.get(dirId) override urutan file
  expanded: false,         // dari store.state.openDirs.has(id)
}
FileNode = {
  id: "graps/ai/provider.py",
  name: "provider.py",
  kind: "file",
  node: <backend node data>,   // ref ke data asli (functions, imports, risk_level, supported)
  dirId: "graps/ai",
}
```

**Algoritma `buildTree(nodes)` (konkret, anti-halusinasi):**

```js
function buildTree(nodes) {
  const dirMap = new Map();   // dirId → DirNode
  const root = { id: "", name: "", kind: "dir", children: [], expanded: true };

  function ensureDir(dirId) {
    if (dirMap.has(dirId)) return dirMap.get(dirId);
    const parts = dirId.split("/");
    const name = parts[parts.length - 1];
    const parentDirId = parts.slice(0, -1).join("/");
    const parent = parentDirId === "" ? root : ensureDir(parentDirId);
    const d = { id: dirId, name: name, kind: "dir", children: [], expanded: false };
    dirMap.set(dirId, d);
    parent.children.push(d);
    return d;
  }

  // Pass 1: buat semua dir dari node.id prefix
  nodes.forEach((n) => {
    const parts = n.id.split("/");
    for (let i = 1; i < parts.length; i++) ensureDir(parts.slice(0, i).join("/"));
  });

  // Pass 2: attach file ke dir parent-nya
  nodes.forEach((n) => {
    const parts = n.id.split("/");
    const fileDirId = parts.slice(0, -1).join("/");
    const parent = fileDirId === "" ? root : dirMap.get(fileDirId);
    if (!parent) return;  // defensive: node dengan id aneh
    parent.children.push({
      id: n.id, name: parts[parts.length - 1], kind: "file",
      node: n, dirId: fileDirId,
    });
  });

  // Pass 3: sort children tiap dir — dirs dulu (alfabetis by name), files lalu (alfabetis by name),
  // KECUALI store.state.fileOrder.get(dir.id) ada → files ikut order itu (drag-reorder)
  const fileOrder = store.state.fileOrder || new Map();
  function sortChildren(d) {
    const order = fileOrder.get(d.id);
    d.children.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind === "dir" ? -1 : 1;  // dirs first
      if (a.kind === "file" && order) {
        return order.indexOf(a.id) - order.indexOf(b.id);       // manual order
      }
      return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;    // alfabetis
    });
    d.children.forEach((c) => c.kind === "dir" && sortChildren(c));
  }
  sortChildren(root);

  return { root: root, dirMap: dirMap };
}
```

**Visible nodes** = root-level (depth 0) + semua anak dari dir yang `openDirs.has(dirId)`. Progressive disclosure: nested dir yang belum di-expand → anaknya ga dirender (di DOM, `children` di-render kosong/hidden, bukan dihilangkan dari model — biar re-render cepat pas expand).

**Resolusi ancestor visible (dipakai proxy edge §5.3):**

```js
// Cari ancestor dir-node yang VISIBLE terdekat dari node id.
// Visible = dir itu sendiri expanded ATAU node ada di root.
function nearestVisibleDir(fileId, dirMap) {
  const parts = fileId.split("/");
  for (let i = parts.length - 1; i >= 1; i--) {
    const dirId = parts.slice(0, i).join("/");
    const d = dirMap.get(dirId);
    if (d && (i === 1 || store.state.openDirs.has(parts.slice(0, i - 1).join("/")))) {
      return d;  // dir ini visible (parent-nya expanded)
    }
  }
  return null;
}
```

### 3.3 State extensions (filter.js — minimal)

Reuse existing, tambah 2 field. **State aktual sekarang (filter.js line 17-25):**

```js
store.state = {
  graph: null,        // {meta, nodes, edges, warnings}
  selectedNode: null, // node object (bukan id)
  hoveredNode: null,
  filter: { risk: null, dead: false },
  sidePanel: false,
  openDirs: new Set(),   // SUDAH ADA — reuse untuk expand state tree
  aiHistory: [],
  activePanel: null,
}
```

**Tambah 2 field (jangan ubah yang lain, jangan ubah pola setState):**

```js
  fileOrder: new Map(),          // BARU — dirId → ordered file ids (drag-reorder). Default: alfabetis
  edgeMode: "selected",          // BARU — "selected"|"none". Default "selected". Circular selalu warning walau none
```

`setState({ openDirs: nextSet })` tetap jalan (sidebar.js pakai pola ini, tree-view reuse). `setState({ fileOrder: nextMap })` baru. Listener `change` tetap dispatch `e.detail.keys`.



---

## 4. Kontrak Antar Komponen (Interface Proposal)

### 4.1 graph.js — tree render + edge overlay

**Public API baru (ganti Canvas API lama). Signature + body inti:**

```js
window.graps.graph = {
  buildTree, renderTree, renderEdges, selectNode,
  toggleDir, reorderFile, expandToPath, scrollIntoNode,
};

// State internal (ganti transform/zoom lama)
let tree = null;          // { root, dirMap } dari buildTree
let treeEl = null;        // #tree-root <ul>
let edgeLayer = null;     // #edge-layer <svg>
let scrollEl = null;      // #tree-scroll

function renderTree() {
  if (!treeEl || !tree) return;
  // Re-build dari nodes terbaru + state, render ulang seluruh <ul>.
  // ponytail: full re-render tiap change. <500 file OK. Diff DOM kalau jank.
  tree = buildTree(store.state.graph.nodes);
  treeEl.innerHTML = renderDirChildren(tree.root);
  wireRowEvents();
}

// Render children satu dir jadi HTML string (recursive)
function renderDirChildren(dir) {
  return '<ul class="tree-children">' +
    dir.children.map(function (c) {
      if (c.kind === "dir") {
        const exp = store.state.openDirs.has(c.id);
        return '<li class="tree-node dir-node' + (exp ? " expanded" : "") + '" data-dir-id="' + esc(c.id) + '">' +
          '<div class="tree-row" data-dir-id="' + esc(c.id) + '">' +
            '<span class="dir-icon">' + (exp ? "▾" : "▸") + "</span>" +
            '<span class="dir-name">' + esc(c.name) + "/</span>" +
          "</div>" +
          (exp ? renderDirChildren(c) : "") +  // progressive disclosure: anak cuma jika expanded
          "</li>";
      }
      const n = c.node;
      const risk = n.risk_level || "clean";
      const sel = store.state.selectedNode && store.state.selectedNode.id === c.id;
      return '<li class="tree-node file-node' + (sel ? " selected" : "") + '" data-node-id="' + esc(c.id) + '">' +
        '<div class="tree-row file-row" data-node-id="' + esc(c.id) + '">' +
          '<span class="node-risk-ring ring-' + risk + '"></span>' +
          '<span class="file-name" title="' + esc(c.name) + '">' + esc(c.name) + "</span>" +
        "</div>" +
        // Popover inline expansion (Fase 3): child row detail diisi saat select
        "</li>";
    }).join("") +
  "</ul>";
}

function toggleDir(dirId) {
  const cur = store.state.openDirs || new Set();
  const next = new Set(cur);
  if (next.has(dirId)) next.delete(dirId); else next.add(dirId);
  setState({ openDirs: next });   // trigger renderTree via store change listener
  // reroute edge (Fase 2)
  renderEdges();
}

function selectNode(fileNode) {
  setState({ selectedNode: fileNode });  // listener renderTree (highlight) + renderEdges
}

function expandToPath(path) {
  // Buka semua dir ancestor dari path — dipakai search pan-to
  const parts = path.split("/");
  const cur = store.state.openDirs || new Set();
  const next = new Set(cur);
  for (let i = 1; i < parts.length; i++) next.add(parts.slice(0, i).join("/"));
  setState({ openDirs: next });
  // scroll ke node setelah render
  requestAnimationFrame(() => scrollIntoNodeById(path));
}

function scrollIntoNode(fileNode) { scrollIntoNodeById(fileNode.id); }
function scrollIntoNodeById(id) {
  const el = treeEl.querySelector('[data-node-id="' + CSS.escape(id) + '"]');
  if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
}
```

**Hapus dari graph.js lama:** `panTo` (via zoom), `fit`/`fitToViewport`, `getTransform`, `getNodes`, `transform`, `zoomBehavior`, `ctx`, `canvas`, `draw()`, `drawNode`, `drawArrow`, `nodeWidth`/`nodeHeight`/`clipText` (Canvas), `nodeAt`/`edgeAt` (hit), `quadtree`, `simulation` (d3-force), `initZoom`/`initSim`, `updateZoomIndicator`, semua `ctx.*` & `d3.zoom`/`d3.force*`. **Pertahankan:** `window.graps.basename` (export, dipakai panel.js line 24), `escapeHtml` (reuse), `loadGraph` (fetch + setState graph).

### 4.2 index.html — layout baru (diff dari aktual)

**index.html aktual sekarang (line 58-101) — region yang berubah:**

```html
<!-- AKTUAL: -->
<div id="app-layout">
  <aside id="dir-sidebar" class="dir-sidebar" role="navigation" aria-label="Directory tree">
    <button id="sidebar-chevron" class="panel-chevron sidebar-chevron" aria-label="Toggle sidebar">›</button>
  </aside>
  <div id="graph-wrap" class="graph-wrap">
    <canvas id="graph-canvas" role="img" aria-label="Dependency graph" tabindex="0"></canvas>
    <div id="tooltip" class="tooltip" role="status" aria-live="polite"></div>
    <div id="node-popover" class="node-popover hidden"></div>
    <div class="zoom-indicator"><span id="zoom-level">100%</span></div>
    <div id="empty-state" class="empty-state"></div>
    <div id="loading-screen" class="loading-screen">...</div>
  </div>
  <aside id="side-panel" class="side-panel" role="complementary" aria-label="File detail" aria-hidden="true"></aside>
</div>
```

```html
<!-- BARU (Phase 6): -->
<div id="app-layout">
  <div id="graph-wrap" class="graph-wrap">
    <div id="tree-scroll" class="tree-scroll" role="tree" aria-label="Project file tree">
      <ul id="tree-root" class="tree-root"></ul>            <!-- diisi graph.js renderTree -->
    </div>
    <svg id="edge-layer" class="edge-layer" aria-hidden="true"></svg>  <!-- absolute overlay, pointer-events:none -->
    <div id="tooltip" class="tooltip" role="status" aria-live="polite"></div>  <!-- tetap (edge tooltip) -->
    <div id="empty-state" class="empty-state"></div>        <!-- tetap -->
    <div id="loading-screen" class="loading-screen">...</div>  <!-- tetap -->
  </div>
  <aside id="side-panel" class="side-panel" role="complementary" aria-label="File detail" aria-hidden="true"></aside>
</div>
```

**Hapus elemen:** `#dir-sidebar`, `#sidebar-chevron`, `#graph-canvas`, `#node-popover`, `.zoom-indicator` + `#zoom-level`.
**Script tag (line 133-139 aktual):** hapus `<script src="sidebar.js"></script>`. Urutan lain tetap: toast → filter → graph → panel → ai → search.



### 4.3 panel.js — popover jadi inline expansion

`showPopover(node)` lama (overlay positioned via transform.k, line 40-106) → ganti `expandFileRow(fileNode)`. **Bedanya container, bukan content:**

```js
// showPopover lama: el = #node-popover (overlay absolute), positioned via transform.k.
// expandFileRow baru: el = child <li> di dalam tree row file-node, inline.

function expandFileRow(fileNode) {
  const row = treeEl.querySelector('[data-node-id="' + CSS.escape(fileNode.id) + '"]');
  if (!row) return;
  // Toggle: kalau udah expanded, collapse
  const existing = row.querySelector(".file-detail");
  if (existing) { existing.remove(); row.classList.remove("expanded"); return; }

  const fns = fileNode.functions || [];
  const imports = fileNode.imports || [];
  const usedBy = findUsedBy(fileNode);  // reuse panel.js findUsedBy() line 113-120

  const detail = document.createElement("div");
  detail.className = "file-detail";
  // Reuse template HTML dari showPopover lama (line 69-97) — function list, imports, usedBy, risk.
  // Ganti header: ga perlu popover-filename (nama udah di tree row), ganti dengan tombol › side panel.
  detail.innerHTML =
    '<div class="popover-section">' +
      '<div class="popover-label">Functions (' + fns.length + ")</div>" +
      fns.slice(0, 5).map((f) =>
        '<div class="popover-fn">' + (f.is_dead_code ? "⚫" : "ƒ") + " " + esc(f.name) + "</div>"
      ).join("") +
      (fns.length > 5 ? '<div class="popover-more">+' + (fns.length - 5) + " more</div>" : "") +
    "</div>" +
    '<div class="popover-section">' +
      '<div class="popover-label">Imports (' + imports.length + ")</div>" +
      imports.slice(0, 3).map((i) =>
        '<div class="popover-import">↳ ' + esc(i.from || i.resolved_path || "?") + "</div>"
      ).join("") +
      (imports.length > 3 ? '<div class="popover-more">+' + (imports.length - 3) + " more</div>" : "") +
    "</div>" +
    (usedBy.length > 0 ?
      '<div class="popover-section"><div class="popover-label">Dipakai oleh</div>' +
      usedBy.map((f) => '<div class="popover-used">' + esc(f) + "</div>").join("") + "</div>" : "") +
    '<button class="popover-expand" title="Open detail">›</button>';
  row.appendChild(detail);
  row.classList.add("expanded");

  // Tombol › → side panel (reuse logic lama line 100-105)
  detail.querySelector(".popover-expand")?.addEventListener("click", (e) => {
    e.stopPropagation();
    setState({ sidePanel: true });
    panelEl?.classList.add("open");
    panelEl?.setAttribute("aria-hidden", "false");
    if (window.graps.setActivePanel) window.graps.setActivePanel("sidepanel");
    // Side panel render reuse: renderSidePanel(fileNode) dari panel.js lama
  });
}
```

**Reuse:** `findUsedBy()` (line 113-120), `esc()`/`escapeHtml()` (line 18-22), `basename` (window.graps.basename), side-panel render logic. **Hapus:** `showPopover`/`hidePopover` (overlay), `getTransform()` dependency (ga ada zoom), `#node-popover` element. Wiring: graph.js click file-row → panggil `expandFileRow` (expose `window.graps.expandFileRow` atau via store listener di panel.js yang watch `selectedNode`).



### 4.4 style.css — komponen baru (rules konkret, sinkron token warna graph.js lama)

Token warna dari graph.js RING/INK (hardcoded di Canvas karena ga baca CSS var — sekarang pindah ke `:root` CSS var biar reusable di DOM):

```css
:root {
  --ring-clean:  oklch(52% 0.02 250);
  --ring-yellow: oklch(76% 0.15 75);
  --ring-red:    oklch(58% 0.22 25);
  --node-fill:   oklch(18% 0.008 75);
  --ink-primary: oklch(94% 0.006 75);
  --ink-secondary: oklch(65% 0.008 75);
  --ink-muted:   oklch(42% 0.006 75);
  --edge-import: oklch(52% 0.15 145);   /* hijau */
  --edge-call:   oklch(55% 0.18 280);   /* biru/ungu */
  --edge-circular: oklch(58% 0.22 25); /* merah */
}
```

```css
/* Scroll container — pan limit = content size, ga bisa overscroll ke ruang kosong */
.tree-scroll { overflow: auto; flex: 1; position: relative; padding: 8px; scrollbar-width: thin; }
.tree-root, .tree-children { list-style: none; margin: 0; padding: 0; }
.tree-children { padding-left: 20px; }  /* indent per depth */

.tree-node { position: relative; }
.tree-row {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px; border-radius: 6px; cursor: pointer; white-space: nowrap;
}
.tree-row:hover { background: oklch(28% 0.008 75); }
.file-row.selected { background: oklch(30% 0.02 250); }

.dir-icon { width: 1em; color: var(--ink-secondary); }
.dir-name { font-weight: 600; font-family: Sora, sans-serif; color: var(--ink-primary); }
.file-name {
  font-family: "JetBrains Mono", monospace; color: var(--ink-primary);
  overflow: hidden; text-overflow: ellipsis;  /* NATIVE ellipsis — fix bug teks keluar node */
}

.node-risk-ring { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; border: 2px solid var(--ring-clean); }
.ring-yellow { border-color: var(--ring-yellow); }
.ring-red    { border-color: var(--ring-red); }

/* Smooth expand: max-height transition (Fase 4). ponytail: max-height 1000px ceiling. */
.dir-node.expanded > .tree-children,
.file-node.expanded > .file-detail { max-height: 1000px; opacity: 1; transition: max-height 200ms ease, opacity 200ms ease; }
.dir-node:not(.expanded) > .tree-children { max-height: 0; opacity: 0; overflow: hidden; }
.file-detail { padding: 8px 12px; margin: 4px 0 4px 14px; border-left: 2px solid var(--ink-muted); }

/* Edge SVG overlay — absolute di atas tree, ga block clicks */
.edge-layer { position: absolute; inset: 0; pointer-events: none; z-index: 1; width: 100%; height: 100%; }
.edge-path { fill: none; stroke-width: 1.5; }
.edge-path.import   { stroke: var(--edge-import); }
.edge-path.call     { stroke: var(--edge-call); }
.edge-path.circular { stroke: var(--edge-circular); stroke-dasharray: 6 3; }
.edge-label { font: 500 10px Sora, sans-serif; fill: var(--ink-secondary); }

.dragging { opacity: 0.5; cursor: grabbing; }
```

**Hapus dari style.css lama:** `.dir-sidebar`, `.sidebar-chevron`, `.depth-N`, `.node-popover` (overlay), `.zoom-indicator`, `#graph-canvas` rules. **Pertahankan:** `.top-bar`, `.side-panel`, `.ai-bar`, `.tooltip`, `.search-overlay`, `.loading-screen`, `.empty-state`, `.warning-banner`, responsive `@media (max-width: 768px)`.

### 4.5 sidebar.js — HAPUS

Hapus file + `<script src="sidebar.js">` di index.html. Fungsinya (dir tree, toggle, ghost expand) diserap graph.js tree-view. `window.graps.sidebar.expandDirectory` → ganti `window.graps.graph.expandToPath`.

---


## 5. Edge Rendering Detail (SVG overlay + proxy + reroute)

### 5.1 Edge visibility rule

- `store.state.selectedNode` set → render semua edge yang source ATAU target = node itu (import hijau, function_call biru, circular merah dashed).
- `selectedNode === null` → render CUMA edge `type==="circular"` (warning selalu on). Backlog: toggle `edgeMode`.
- Edge ga pernah render semua sekaligus (anti-clutter, sesuai keputusan "kontekstual saat select").

### 5.2 Koordinat edge = dari DOM rect + renderEdges konkret

Edge ga punya posisi sendiri. Tiap render, koordinat dihitung dari `getBoundingClientRect()` node DOM vs scroll container:

```js
function nodeCenter(id) {
  // id = file-node id ATAU dir-node id (proxy)
  const el = treeEl.querySelector('[data-node-id="' + CSS.escape(id) + '"]');
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const c = scrollEl.getBoundingClientRect();
  return {
    x: r.left - c.left + scrollEl.scrollLeft + r.width / 2,
    y: r.top - c.top + scrollEl.scrollTop + r.height / 2,
  };
}

function renderEdges() {
  if (!edgeLayer || !store.state.graph) return;
  const edges = store.state.graph.edges || [];
  const sel = store.state.selectedNode;
  // Filter: saat select → edge dari/ke node itu; idle → cuma circular (warning)
  const visible = (sel)
    ? edges.filter((e) => e.source === sel.id || e.target === sel.id)
    : edges.filter((e) => e.type === "circular");
  if (!visible.length) { edgeLayer.innerHTML = ""; return; }

  const dirMap = tree.dirMap;
  const parts = visible.map((e) => {
    // Resolve target: node visible? → node asli. Collapsed → proxy dir ancestor visible.
    const sC = nodeCenter(e.source);
    const tVisible = isNodeVisible(e.target, dirMap);
    const tId = tVisible ? e.target : (nearestVisibleDir(e.target, dirMap) || {}).id;
    const tC = nodeCenter(tId);
    if (!sC || !tC) return "";
    const cls = e.type === "circular" ? "circular" : (e.type === "function_call" ? "call" : "import");
    // Cubic bezier vertical-aware (mirip edge lama): kontrol point di tengah-Y
    const my = (sC.y + tC.y) / 2;
    const d = "M " + sC.x + " " + sC.y + " C " + sC.x + " " + my + ", " + tC.x + " " + my + ", " + tC.x + " " + tC.y;
    let html = '<path class="edge-path ' + cls + '" d="' + d + '" />';
    if (!tVisible) {
      // Proxy label: tunjukin nama file target yang hidden
      const fname = e.target.split("/").pop();
      html += '<text class="edge-label" x="' + tC.x + '" y="' + (tC.y - 6) + '">→ ' + esc(fname) + "</text>";
    }
    return html;
  }).join("");
  edgeLayer.innerHTML =
    '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">' +
    '<path d="M0,0 L8,4 L0,8 Z" fill="currentColor" /></marker></defs>' + parts;
}

function isNodeVisible(fileId, dirMap) {
  // Node visible = semua dir ancestor-nya di-expand (atau root-level)
  const parts = fileId.split("/");
  for (let i = 1; i < parts.length; i++) {
    const dirId = parts.slice(0, i).join("/");
    if (!store.state.openDirs.has(dirId)) return false;
  }
  return true;
}
```

**Edge stick ke node:** `renderEdges()` di-panggil ulang tiap `toggleDir` (reroute), `reorderFile` (drag), dan scroll. Scroll handler:

```js
let rafPending = false;
scrollEl.addEventListener("scroll", () => {
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(() => { renderEdges(); rafPending = false; });
});
```

### 5.3 Proxy edge (cross-dir, target collapsed)

```
app.py (graps/server/) --function_call--> provider.py (graps/ai/)
```
- `graps/ai/` **collapsed** → `provider.py` ga dirender. Edge target = **dir-node `graps/ai`** (ancestor visible terdekat, via `nearestVisibleDir()` §3.2). Label `→ provider.py` di path.
- `graps/ai/` di-**expand** → `provider.py` muncul. `isNodeVisible()` return true → edge **reroute** ke node asli, label ilang. `renderEdges()` dipanggil ulang di `toggleDir`.
- Multiple edge ke node dalam dir collapsed sama → stack di dir-node (backlog: visual stacking/fan-out. Sekarang: 1 path per edge, overlap di titik yang sama — acceptable kalau sedikit).

**Resolusi proxy pakai `nearestVisibleDir()` dari §3.2** (sudah konkret di sana). Tidak ada kode tambahan di sini — reuse.



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

---

## 9. Render Flow & State Transitions (anti-halusinasi wiring)

**Trigger → re-render mapping.** Ini yang harus diketik presis — tanpa ini AI bisa salah wiring event & call function di waktu salah.

| Event / Trigger | Handler | Panggil | Side effect |
|-----------------|---------|---------|-------------|
| `DOMContentLoaded` / boot | `graph.js boot()` | `loadGraph()` → fetch `/api/graph` → `setState({graph})` | store `change` event ke `graph` |
| store `change` key=`graph` | `graph.js` listener | `renderTree()` + `renderEdges()` | tree render awal |
| store `change` key=`openDirs` | `graph.js` listener | `renderTree()` + `renderEdges()` | reroute edge (proxy→asli) |
| store `change` key=`selectedNode` | `graph.js` listener | `renderTree()` (highlight) + `renderEdges()` | edge kontekstual muncul |
| store `change` key=`selectedNode` | `panel.js` listener | `expandFileRow(node)` | inline detail muncul |
| store `change` key=`hoveredNode` | `graph.js` listener | `renderTree()` (hover class) | **Bug #1 fix: WAJIB handle, ga boleh skip** |
| store `change` key=`filter` | `graph.js` listener | `renderTree()` (dim/sembunyi node) | risk/dead filter |
| store `change` key=`fileOrder` | `graph.js` listener | `renderTree()` + `renderEdges()` | drag-reorder → edge ikut |
| click `.tree-row[data-dir-id]` | `graph.js wireRowEvents` | `toggleDir(dirId)` | setState openDirs → listener |
| click `.tree-row[data-node-id]` | `graph.js wireRowEvents` | `selectNode(fileNode)` | setState selectedNode → listener |
| click `.popover-expand` (di detail) | `panel.js` | `setState({sidePanel:true})` + `setActivePanel('sidepanel')` | side panel buka |
| `window:graps:pan-to` (search.js dispatch) | `graph.js` listener | `expandToPath(id)` + `scrollIntoNode(id)` | buka ancestor + scroll |
| `scroll` on `#tree-scroll` | `graph.js` | `renderEdges()` (rAF throttle) | edge ikut node saat pan |
| drag file-row (Fase 4) | `graph.js` drag handler | `reorderFile(dirId, from, to)` | setState fileOrder → listener |

**Listener yang ada sekarang di graph.js (line 673-690 aktual) & harus di-rewrite:**

```js
// graph.js aktual — listener yang ada:
store.addEventListener("change", (e) => {
  if (e.detail.keys.includes("filter") || e.detail.keys.includes("selectedNode") || e.detail.keys.includes("hoveredNode")) {
    draw();  // LAMA: draw() Canvas
  }
});
window.addEventListener("graps:dirs-changed", () => draw());  // LAMA: dari sidebar.js
window.addEventListener("graps:pan-to", (ev) => { /* panTo via zoom */ });

// BARU Phase 6:
store.addEventListener("change", (e) => {
  const k = e.detail.keys;
  if (k.includes("graph")) { renderTree(); renderEdges(); }
  if (k.includes("openDirs")) { renderTree(); renderEdges(); }  // reroute
  if (k.includes("selectedNode")) { renderTree(); renderEdges(); }
  if (k.includes("hoveredNode")) { renderTree(); }  // bug #1: WAJIB handle
  if (k.includes("filter")) { renderTree(); renderEdges(); }
  if (k.includes("fileOrder")) { renderTree(); renderEdges(); }
});
// graps:dirs-changed dihapus (sidebar.js dihapus)
window.addEventListener("graps:pan-to", (ev) => { expandToPath(ev.detail.id); });
```

**`expandToPath` ganti `sidebar.expandDirectory`** — panel.js line 472 aktual manggil `window.graps.sidebar.expandDirectory(dirName)` → ganti `window.graps.graph.expandToPath(path)`.

---

## 10. Kode Referensi Aktual (anchor anti-halusinasi)

Kutipan kode yang ADA SEKARANG (pre-Phase 6). Implementasi Phase 6 harus konsisten dengan ini. Baca file asli kalau butuh konteks lebih.

### 10.1 graph.js — draw() inti (Canvas, yang dihapus)
```js
// graph.js line 178-185 (aktual) — yang diganti renderTree/renderEdges
function draw() {
  if (!ctx) return;
  const k = transform.k;
  ctx.save();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.translate(transform.x, transform.y);
  ctx.scale(k, k);
  // ... edges + nodes loop, ctx.fillText, dst (DIHAPUS Phase 6)
}
```

### 10.2 graph.js — export yang dipertahankan
```js
// graph.js line 531 (aktual)
window.graps.basename = basename;  // dipakai panel.js line 24 — PERTAHANKAN

// graph.js line 745-748 (aktual) — DIHAPUS, ganti API baru §4.1
window.graps.graph = { panTo, fit: fitToViewport, getNodes, getTransform };
```

### 10.3 panel.js — showPopover yang diganti (line 40-106 aktual)
```js
function showPopover(node) {
  const el = document.getElementById("node-popover");  // overlay — DIHAPUS
  const transform = graph.getTransform();              // zoom — DIHAPUS
  const screenX = rect.left + node.x * transform.k + transform.x;  // DIHAPUS
  // ... innerHTML function list/imports/usedBy (REUSE template, ganti container) §4.3
}
```

### 10.4 filter.js — state + setState (line 17-49 aktual, pola dipertahankan)
```js
store.state = {
  graph: null, selectedNode: null, hoveredNode: null,
  filter: { risk: null, dead: false }, sidePanel: false,
  openDirs: new Set(), aiHistory: [], activePanel: null,
};
// setState = Object.assign + dispatch 'change' dengan detail.keys
// setActivePanel(name) — mobile orchestration, dipertahankan
```

### 10.5 sidebar.js — yang diserap graph.js (line 49-77 aktual, lalu DIHAPUS)
```js
function buildDirTree(nodes) {        // REUSE algoritma di buildTree §3.2
  const dirs = new Set();
  nodes.forEach((n) => {
    const parts = n.id.split("/");
    for (let i = 1; i < parts.length; i++) dirs.add(parts.slice(0, i).join("/"));
  });
  return Array.from(dirs).sort();
}
function toggleDirectory(dir) {       // REUSE pola di toggleDir §4.1
  const current = store.state.openDirs || new Set();
  const next = new Set(current);
  if (next.has(dir)) next.delete(dir); else next.add(dir);
  setState({ openDirs: next });
  window.dispatchEvent(new CustomEvent("graps:dirs-changed"));  // DIHAPUS (sidebar.js ilang)
}
```

### 10.6 index.html — script tag order (line 131-139 aktual)
```html
<script src="toast.js"></script>
<script src="filter.js"></script>
<script src="graph.js"></script>
<script src="panel.js"></script>
<script src="sidebar.js"></script>   <!-- DIHAPUS Phase 6 -->
<script src="ai.js"></script>
<script src="search.js"></script>
```

### 10.7 Backend — `/api/graph` response shape (tidak berubah, dari test_api.py + graph_builder)
```python
# graph = {meta, nodes, edges, warnings}
# node: {id, type:"file", path, risk_level, functions[], imports[], classes, constants, supported}
#   function: {name, params, returns, criticality, is_dead_code, callers, callees,
#              line_start, line_end, risks, decorators, is_private, ai_summary}
# edge: {source, target, type:"imports"|"function_call"|"circular", weight, imported_names}
# Backend TIDAK disentuh Phase 6 — dir di-derive client-side dari node.id
```

---

## 11. Catatan Implementasi untuk AI/Dev Lain

1. **Baca file aktual sebelum ngubah.** Doc ini kutip kode yang ada, tapi bisa drift kalau repo berubah. Selalu `read_files` graph.js/panel.js/filter.js/index.html/sidebar.js sebelum mulai fase.
2. **Konsisten dengan §9 (Render Flow).** Salah wiring event = bug halus (state berubah tapi UI ga update). Ikuti tabel trigger→handler persis.
3. **Reuse sebelum tulis baru.** `buildTree` algoritma §3.2 = turunan `buildDirTree` sidebar.js §10.5. `expandFileRow` §4.3 = `showPopover` template §10.3 ganti container. `nearestVisibleDir` §3.2 fungsi baru tapi simple.
4. **Jangan sentuh backend.** `/api/graph` shape §10.7 cukup. Dir = client concept. Kalau "butuh" dir dari backend = salah arah, re-read §0 baris "Dir-node = konsep sintetik frontend".
5. **Ponytail: full re-render `renderTree()` tiap change.** <500 file OK. Diff DOM cuma kalau jank terbukti. Cache `measureText`/coordinate cuma kalau frame drop.
6. **Tiap fase = app jalan.** Jangan mulai Fase 2 sebelum Fase 1 acceptance lulus. Lihat §6 acceptance per fase.
7. **Bug #1 (hoveredNode ga redraw) WAJIB di-handle** di listener baru §9 — jangan ulang skip kayak Phase 5.


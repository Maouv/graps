# PLAN: Lazy-Render Tree Layout untuk Graph Canvas

**Repo:** `Maouv/graps`, branch `development`
**File utama:** `graps/frontend/graph.js`
**Branch kerja:** `feature/lazy-render-graph` (buat baru dari `development`, jangan commit ke `development` langsung)

Dokumen ini self-contained — ditulis untuk dieksekusi oleh AI coding agent lain tanpa
akses ke history diskusi asal. Semua keputusan sudah final, jangan tanya ulang ke user
kecuali menemukan kontradiksi nyata dengan kode aktual saat implementasi.

---

## 1. PROBLEM

`graph.js` saat ini me-layout dan me-render **seluruh** node (file + folder yang di-synthesize
dari path) sekaligus setiap kali graph di-load, menyebabkan seluruh tree tervisualisasi flat
dari atas ke bawah, kolom tidak rapi, tidak ada hierarki yang dapat dibaca.

Root cause (sudah diverifikasi baca kode langsung, bukan asumsi):

1. `loadGraph()` (baris ~858-890) memanggil `computeTreeLayout()` sekali di awal load, atas
   SEMUA node hasil `synthesizeDirNodes()` (yang men-generate node folder untuk SETIAP prefix
   path yang ada — total node = semua file + semua folder di seluruh tree).
2. Ada logic filter visibility `_dirFilter` di dalam `draw()` (baris ~523-533) yang baca
   `store.state.openDirs`, TAPI:
   - Default `openDirs` adalah `new Set()` (kosong) → `_dirFilter = _openDirs && _openDirs.size > 0`
     jadi **false** saat kosong → artinya "belum ada folder dibuka" = "tampilkan SEMUA node
     tanpa filter". Logic ini terbalik dari yang seharusnya.
   - Filter ini HANYA skip `drawNode()` (cat-nya doang). Node tetap ikut dihitung di
     `computeTreeLayout()` (makan slot Y di sibling-stack), tetap ada di `quadtree` yang
     dipakai `nodeAt()` untuk hit-detection klik. Jadi bukan lazy-render sungguhan.
3. Edges (garis import/function-call) di `draw()` (baris ~467-520) SAMA SEKALI tidak dicek
   terhadap visibility — garis akan tetap tergambar menyambung ke titik yang node-nya
   tersembunyi.
4. Tidak ada click-handler untuk expand/collapse folder LANGSUNG DI CANVAS. Toggle folder
   yang ada sekarang cuma lewat sidebar (`sidebar.js: toggleDirectory()`), dan sidebar itu
   pakai state `store.state.openDirs` yang SAMA dengan yang dibaca `_dirFilter` di atas.

Backend hanya punya 1 endpoint: `GET /api/graph` (full dump sekali fetch, semua node+edges).
Tidak ada endpoint per-folder. **Keputusan: solusi ini LAZY-RENDER, bukan lazy-fetch** — semua
data tetap di-fetch sekaligus di awal (browser sudah punya semua node di memory), yang di-gate
hanya proses layout + render + hit-detection. Backend TIDAK disentuh sama sekali.

---

## 2. SCOPE

**In scope:**
- Root load: hanya node depth-0 (top-level folder + file langsung di root) yang di-layout & di-render.
- Klik folder node di canvas → expand: children folder tersebut (folder-dulu-baru-file urutannya)
  langsung muncul instant di kolom depth+1. TIDAK ada animasi transisi.
- Klik folder yang sudah expand → collapse: folder itu DAN SEMUA descendant-nya (termasuk
  folder cucu yang sempat di-expand user) di-reset ke collapsed. Tidak ada "diingat" state.
- State baru `graphOpenDirs` (lihat §4) — dipakai HANYA oleh canvas, terpisah total dari
  `openDirs` milik sidebar. Toggle di sidebar TIDAK mempengaruhi canvas, dan sebaliknya —
  ini disengaja (independen), bukan bug.
- Search (Cmd+K, `search.js`) dan klik cross-reference link di detail panel (`panel.js`,
  event `graps:pan-to`) yang mengarah ke node yang sedang tersembunyi → HARUS auto-expand
  semua folder ancestor node tersebut, baru pan ke sana.
- Fix: edges ke/dari node yang hidden ikut tidak digambar.
- Fix: kalau `selectedNode` (node yang detail panel-nya lagi kebuka) jadi hidden karena
  ancestor folder-nya di-collapse user, auto `setState({selectedNode: null})`.
- Hapus total: `runCollisionOnly()` dan pemakaian `d3.forceSimulation` di file ini. Layout
  kolom sudah deterministik (X = depth, Y = sibling stack), tidak butuh physics collision lagi.

**Out of scope (jangan dikerjakan):**
- Lazy-fetch / endpoint backend baru.
- Sinkronisasi state sidebar ↔ canvas.
- Animasi expand/collapse.
- Perubahan visual card style (header/imports/functions/label section tetap sama persis).
- Optimisasi apapun di luar yang disebut di atas.

---

## 3. FILES YANG DISENTUH

1. `graps/frontend/graph.js` — perubahan utama (lihat §5)
2. `graps/frontend/filter.js` — tambah 1 field state (lihat §4)
3. `graps/frontend/sidebar.js` — **TIDAK diubah sama sekali**, dicek dulu untuk memastikan
   tidak ada dependency tersembunyi ke variabel/fungsi yang di-refactor di graph.js sebelum
   mulai (grep `window.graps.graph.` dan `window.graps.dirDepth` usage across semua file
   frontend sebelum edit, pastikan tidak ada yang break).

Tidak ada perubahan backend/Python/schema/API.

---

## 4. DATA STRUCTURES

Di `filter.js`, dalam `store.state` (cari objek yang punya `openDirs: new Set()`), tambahkan
field baru **persis di sebelahnya**, JANGAN reuse `openDirs` yang sudah ada:

```js
store.state = {
  // ...existing fields tetap...
  openDirs: new Set(),        // EXISTING — milik sidebar.js, JANGAN disentuh
  graphOpenDirs: new Set(),   // BARU — milik graph.js SAJA, canvas expand/collapse state
  // ...
};
```

Tidak ada perubahan schema node/edge dari backend. Field `is_directory` / `type === "directory"`
pada node sudah cukup dan sudah dipakai konsisten di `drawNode()` (baris ~285: `const isDir = n.is_directory || n.type === "directory"`) — JANGAN diubah, ini sudah benar.

---

## 5. IMPLEMENTASI DETAIL — `graph.js`

### 5.1 Fungsi baru: `isNodeVisible(node, openDirsSet)`

```js
function isNodeVisible(node, openDirsSet) {
  const depth = dirDepth(node.id);
  if (depth === 0) return true;
  // cek apakah ADA ancestor prefix dari node.id yang ada di openDirsSet.
  // PENTING: gunakan boundary "/" eksplisit untuk hindari false-positive
  // (contoh: id "src2/app.py" TIDAK BOLEH match openDir "src").
  const parts = node.id.split("/");
  for (let i = 1; i < parts.length; i++) {
    const ancestor = parts.slice(0, i).join("/");
    if (openDirsSet.has(ancestor)) return true;
  }
  return false;
}
```

Taruh dekat `dirDepth()` (sekitar baris 76-77), karena dependency-nya sama.

### 5.2 Fungsi baru: `visibleNodeList()`

```js
let visibleNodesCache = [];  // deklarasi di top-level closure, dekat `let nodes = [], edges = [];`

function visibleNodeList() {
  const openDirsSet = store.state.graphOpenDirs || new Set();
  return nodes.filter(n => isNodeVisible(n, openDirsSet));
}
```

### 5.3 Ubah `computeTreeLayout()` — terima parameter, jangan pakai `nodes` global

Signature lama:
```js
function computeTreeLayout() {
  if (!nodes.length) return;
  ...pakai `nodes` langsung dari closure...
}
```

Ubah jadi terima parameter eksplisit:
```js
function computeTreeLayout(nodeList) {
  if (!nodeList.length) return;
  const byDepth = new Map();
  nodeList.forEach(n => {
    const d = dirDepth(n.id);
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d).push(n);
  });
  [...byDepth.keys()].sort((a, b) => a - b).forEach(d => {
    // sibling order: folder DULU, baru file — lexicographic dalam tiap grup.
    // (requirement eksplisit: "folder dulu baru fungsi/file")
    const col = byDepth.get(d).sort((a, b) => {
      const aDir = a.is_directory || a.type === "directory";
      const bDir = b.is_directory || b.type === "directory";
      if (aDir !== bDir) return aDir ? -1 : 1;
      return a.id.localeCompare(b.id);
    });
    let stack = -TREE_ROW_GAP;
    col.forEach(n => { stack += nodeHeight(n, 1) + TREE_ROW_GAP; });
    let y = -stack / 2;
    col.forEach(n => {
      const h = nodeHeight(n, 1);
      n.x = colX(d);
      n.y = y + h / 2;
      y += h + TREE_ROW_GAP;
    });
  });
}
```

Catatan: sorting folder-dulu-baru-file ini BARU (kode lama cuma `localeCompare` polos di
baris ~124) — ini implementasi requirement eksplisit dari user, bukan opsional.

### 5.4 Fungsi baru: `relayout()` — orchestrator, dipanggil setiap kali visibility berubah

```js
function relayout() {
  visibleNodesCache = visibleNodeList();
  computeTreeLayout(visibleNodesCache);
  buildQuadtree();       // lihat §5.5, harus baca visibleNodesCache
  draw();
}
```

### 5.5 Ubah `buildQuadtree()` — pakai `visibleNodesCache`, bukan `nodes` penuh

```js
function buildQuadtree() {
  quadtree = d3.quadtree()
    .x(d => d.x)
    .y(d => d.y)
    .addAll(visibleNodesCache);
}
```

### 5.6 Ubah `fitToViewport()` — iterate `visibleNodesCache`

Ganti `for (const n of nodes)` (baris ~679) jadi `for (const n of visibleNodesCache)`.
Guard awal juga: `if (!visibleNodesCache.length) return;`

### 5.7 Ubah `draw()` — filter edges by visibility

Di loop edges (baris ~467), tambahkan check di awal loop:

```js
const visibleIds = new Set(visibleNodesCache.map(n => n.id));
for (const e of edges) {
  const s = e.source, t = e.target;
  if (!s || !t || typeof s.x !== "number") continue;
  if (!visibleIds.has(s.id) || !visibleIds.has(t.id)) continue;   // BARU
  ...sisanya tetap sama...
}
```

Di loop nodes (baris ~522-535), HAPUS SELURUH blok `_dirFilter`/`_openDirs` (logic lama yang
salah, baca `store.state.openDirs` — itu punya sidebar, bukan buat ini lagi) dan ganti dengan
iterasi langsung atas `visibleNodesCache`:

```js
for (const n of visibleNodesCache) {
  drawNode(n, focus, k);
}
```

### 5.8 Hapus total `runCollisionOnly()` (baris ~160-170)

Hapus fungsi ini seluruhnya. Hapus juga variabel `simulation` kalau setelah dicek tidak
dipakai di tempat lain (grep dulu — ada di `window.graps.graph` public API? Cek baris ~985-990,
kalau tidak ada reference, aman dihapus juga deklarasinya di baris ~24).

### 5.9 Tambah click-handler folder di `setupInteractions()` (baris ~924-927)

Ganti handler klik existing:
```js
canvas.addEventListener("click", ev => {
  const n = nodeAt(ev.clientX, ev.clientY);
  if (n && n.supported !== false) setState({ selectedNode: n });
});
```

Jadi:
```js
canvas.addEventListener("click", ev => {
  const n = nodeAt(ev.clientX, ev.clientY);
  if (!n) return;

  const isDir = n.is_directory || n.type === "directory";
  if (isDir) {
    toggleFolder(n.id);
    return;
  }
  if (n.supported !== false) setState({ selectedNode: n });
});
```

Tambah fungsi baru `toggleFolder`:
```js
function toggleFolder(dirId) {
  const current = store.state.graphOpenDirs || new Set();
  const next = new Set(current);

  if (next.has(dirId)) {
    // COLLAPSE — reset folder ini DAN semua descendant-nya (keputusan final: no memory)
    next.delete(dirId);
    for (const id of Array.from(next)) {
      if (id.startsWith(dirId + "/")) next.delete(id);
    }
    // auto-deselect kalau selectedNode sekarang jadi hidden
    const sel = store.state.selectedNode;
    if (sel && (sel.id === dirId || sel.id.startsWith(dirId + "/"))) {
      setState({ graphOpenDirs: next, selectedNode: null });
      relayout();
      return;
    }
  } else {
    // EXPAND — cuma buka level ini, TIDAK cascade buka semua descendant
    next.add(dirId);
  }

  setState({ graphOpenDirs: next });
  relayout();
}
```

### 5.10 Fungsi baru: `expandPathTo(nodeId)` — untuk search & pan-to-hidden-node

```js
function expandPathTo(nodeId) {
  const parts = nodeId.split("/");
  const current = store.state.graphOpenDirs || new Set();
  const next = new Set(current);
  for (let i = 1; i < parts.length; i++) {
    next.add(parts.slice(0, i).join("/"));
  }
  setState({ graphOpenDirs: next });
  relayout();
}
```

### 5.11 Ubah listener `graps:pan-to` (baris ~951-954)

Kode lama:
```js
window.addEventListener("graps:pan-to", ev => {
  const node = nodes.find(n => n.id === ev.detail.id || n.path === ev.detail.id);
  if (node) { panTo(node); setState({ selectedNode: node }); }
});
```

PENTING: `nodes.find(...)` di sini harus tetap cari di `nodes` (FULL data, bukan
`visibleNodesCache`) — karena target belum tentu visible saat ini, itu justru kasus yang
mau di-handle. Ubah jadi:

```js
window.addEventListener("graps:pan-to", ev => {
  const node = nodes.find(n => n.id === ev.detail.id || n.path === ev.detail.id);
  if (!node) return;
  expandPathTo(node.id);   // buka semua ancestor folder-nya dulu
  panTo(node);
  setState({ selectedNode: node });
});
```

### 5.12 Ubah `loadGraph()` (baris ~858-890)

Kode lama (bagian relevan):
```js
synthesizeDirNodes();
precomputeNeighbors();
computeTreeLayout();
runCollisionOnly();
resolveEdges();
buildQuadtree();

initZoom();
fitToViewport();
draw();
```

Ganti jadi:
```js
synthesizeDirNodes();       // TETAP generate semua dir node (data lengkap di memory — lazy RENDER bukan lazy FETCH)
precomputeNeighbors();
resolveEdges();
setState({ graphOpenDirs: new Set() });  // default: semua collapsed
relayout();                 // ganti computeTreeLayout() + runCollisionOnly() + buildQuadtree()

initZoom();
fitToViewport();
```

(Hapus `draw()` di baris paling akhir — sudah dipanggil di dalam `relayout()`.)

### 5.13 Public API (`window.graps.graph`, baris ~985-990)

Tidak wajib diubah, tapi kalau ada modul lain yang butuh akses `visibleNodesCache` untuk
debugging, boleh tambah:
```js
window.graps.graph = {
  panTo,
  fit: fitToViewport,
  getNodes: () => nodes,                    // TETAP full data, jangan diubah (dipakai search.js? cek dulu — actually search.js pakai store.state.graph.nodes langsung, bukan ini)
  getVisibleNodes: () => visibleNodesCache, // BARU, opsional
  getTransform: () => transform,
};
```

---

## 6. EDGE CASES & MITIGASI (WAJIB DICEK SAAT IMPLEMENTASI)

| # | Kasus | Mitigasi |
|---|---|---|
| 1 | False-positive prefix match (`src2/x.py` ke-match sebagai child `src`) | `isNodeVisible` HARUS pakai `ancestor === parts.slice(0,i).join("/")` exact match per segment (lihat §5.1), BUKAN `.startsWith()` string mentah tanpa boundary |
| 2 | Folder kosong (0 file sama sekali di subtree) | Non-issue — `synthesizeDirNodes()` cuma generate dir node dari prefix path file yang benar-benar ada, folder kosong tidak akan pernah muncul sebagai node |
| 3 | Spam klik folder cepat | Non-issue — semua synchronous, JS event loop jamin `relayout()` selesai sebelum event berikutnya diproses |
| 4 | `expandPathTo` dipanggil untuk folder yang sebagian sudah expand | Non-issue — `Set.add()` idempotent |
| 5 | `selectedNode` hidden karena ancestor collapse | HARUS auto `setState({selectedNode: null})` — lihat §5.9 |
| 6 | `fitToViewport()` dengan cuma 1 node visible | Sudah di-handle kode existing (zoom cap `Math.min(..., 2)` di baris ~688), tidak perlu perubahan tambahan |
| 7 | Lupa panggil `relayout()` setelah state berubah | Silent failure paling berbahaya — canvas tidak update, terlihat seperti klik "tidak ngapa-ngapain". WAJIB manual-test setiap toggle path sebelum selesai |

---

## 7. MANUAL TEST CHECKLIST (jalankan browser lokal sebelum push)

Jalankan `server/app.py` lokal, buka browser, cek satu-satu:

1. [ ] Fresh load → hanya node depth-0 muncul, rapi kolom
2. [ ] Klik 1 folder → children muncul instant di kolom depth+1, folder-dulu-baru-file
3. [ ] Klik folder yang sama lagi → collapse, semua children+grandchildren hilang
4. [ ] Expand `src/` → expand `src/utils/` → collapse `src/` → `src/utils/` ikut ter-collapse
5. [ ] Klik file (bukan folder) → behavior lama tetap: `selectedNode` set, panel buka, TIDAK toggle
6. [ ] Cmd+K search ke file di folder collapsed → semua ancestor auto-expand + pan ke sana
7. [ ] Klik cross-ref link "called by X" di panel ke file di folder collapsed → sama seperti #6
8. [ ] Select file → collapse folder parent-nya → panel auto-close
9. [ ] Edge (garis import) antara file visible ↔ file di folder collapsed → garis TIDAK tergambar
10. [ ] Zoom/pan setelah toggle folder tetap smooth, tidak error walau cuma 1 node visible
11. [ ] Sidebar toggle folder TIDAK mempengaruhi canvas, canvas toggle TIDAK mempengaruhi sidebar
12. [ ] Filter pill "high risk" / "dead code" tetap jalan independen dari expand/collapse

Unit test opsional (pure function, no framework, jalanin manual via `node`):
```js
// test_visibility.js
const assert = require("assert");
// copy-paste isNodeVisible() function dari graph.js ke sini untuk test standalone
assert.strictEqual(isNodeVisible({id: "app.py"}, new Set()), true);
assert.strictEqual(isNodeVisible({id: "src/app.py"}, new Set(["src"])), true);
assert.strictEqual(isNodeVisible({id: "src2/app.py"}, new Set(["src"])), false);
assert.strictEqual(isNodeVisible({id: "src/utils/x.py"}, new Set(["src"])), false);
assert.strictEqual(isNodeVisible({id: "src/utils/x.py"}, new Set(["src", "src/utils"])), true);
console.log("all visibility tests passed");
```

---

## 8. SEBELUM MULAI — PRE-FLIGHT CHECK

Jalankan grep ini dulu untuk pastikan tidak ada dependency tersembunyi yang ke-break:
```bash
cd graps/frontend
grep -rn "window.graps.graph\.\|window.graps.dirDepth\|\.runCollisionOnly\|simulation\b" *.js
grep -rn "store.state.openDirs\|store.state.graphOpenDirs" *.js
```
Pastikan `openDirs` (sidebar) dan `graphOpenDirs` (canvas, baru) benar-benar tidak saling
baca satu sama lain di file manapun setelah selesai implementasi.

---

## 9. ROLLBACK

Pure frontend, tidak ada migrasi data/schema. Rollback = `git revert` commit di branch
`feature/lazy-render-graph`, atau `git checkout development -- graps/frontend/graph.js
graps/frontend/filter.js`.

---

## 10. RESOURCE IMPACT (expected, bukan target optimisasi)

- CPU/RAM turun: `computeTreeLayout()` dan quadtree build sekarang atas subset visible saja,
  bukan seluruh tree. `d3.forceSimulation` (120 iterasi tick tiap load) dihapus total.
- Initial fetch (`/api/graph`) TIDAK berubah — tetap fetch semua data sekaligus (lazy-render,
  bukan lazy-fetch, sesuai scope §2). Kalau codebase yang di-scan sangat besar dan initial
  load lambat, bottleneck ada di fetch/parse ini, BUKAN di kode yang diubah plan ini — jangan
  salah diagnosa saat debugging performa nanti.

**Estimasi waktu implementasi:** ~2.5–3 jam termasuk manual testing checklist §7.


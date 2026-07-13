# PLAN: Edge Direction Arrow/Marker

**Repo:** `Maouv/graps`, branch dasar: `feature/lazy-render-graph`
**File utama:** `graps/frontend/graph.js`

---

## Phase 0 — Context Intake

- **Branch baru:** `feature/edge-direction-arrow` (dari `feature/lazy-render-graph`, JANGAN dari `development` — kita butuh lazy-render + edge-visibility-filter yang udah ada di situ)
- **File yang kena dampak:** `graps/frontend/graph.js` SAJA. Tidak ada file lain (tidak ada perubahan HTML/CSS/backend).
- **Fungsi yang akan diedit:**
  - `draw()` (baris 535-...) — spesifik blok EDGES (baris 548-585+), tambah pemanggilan fungsi arrowhead baru setelah `ctx.stroke()` per edge
- **Fungsi baru yang akan dibuat:**
  - `drawArrowhead(ctx, tipX, tipY, angleRad, size, color)` — helper standalone, digambar di endpoint target tiap edge
- **Tanggal mulai:** 2026-07-12

---

## Phase 1 — Definition

**Problem statement:** Edge/tali sekarang digambar sebagai kurva polos (`bezierCurveTo` + `stroke`) tanpa indikator arah. User tidak bisa membedakan "file ini yang meng-import" vs "file ini yang di-import" tanpa mengklik/hover salah satu endpoint dan membaca detail panel secara manual.

**Done criteria (draft — koreksi/tambah kalau ada yang kurang):**
- Setiap edge yang ter-render punya marker visual (arrowhead) tepat di titik masuk ke node **target** (searah aliran import: source → target)
- Marker mengikuti warna edge yang sudah ada (`EDGE_COLORS.imports/circular/function_call` — tidak ada warna baru)
- Marker ikut ter-scale mengikuti zoom level `k` (tidak jadi raksasa saat zoom-in, tidak hilang saat zoom-out) — konsisten dengan `ctx.lineWidth = 1.5 / k` yang sudah ada
- Marker ikut ter-filter alpha yang sama seperti garis-nya (focus/dimmed state yang sudah ada di baris 563-566 tidak berubah)

**Out of scope (konfirmasi — ini TIDAK dikerjakan di task ini):**
- Tidak mengubah bentuk garis (tetap bezier elbow-connector seperti sekarang)
- Tidak mengubah `edgeAt()` hit-detection logic (baris 851+) — area klik/hover edge tetap sama, arrowhead murni visual, tidak menambah target klik baru
- Tidak menyentuh `nearestVisibleAncestor()`/approach-B (edge snap-to-ancestor) — itu task terpisah (#3), akan dikerjakan setelah ini, arrowhead harus tetap kompatibel dengan endpoint hasil snap nanti (karena cuma baca `s.x/s.y/t.x/t.y` final, tidak peduli asal node aslinya)
- Tidak menambah tooltip `imported_names` (itu task terpisah, disebut sebagai nice-to-have di planning sebelumnya)

**Consumer — kenapa ini bagus untuk UX (minimal 3 alasan):**
1. **Mengurangi cognitive load saat membaca dependency graph.** Tanpa arah, user harus infer arah dari posisi X (kiri=source diasumsikan) — asumsi itu rapuh begitu layout jadi non-linear (misal setelah approach-B snap-to-ancestor, garis bisa datang dari arah manapun). Arrowhead menghilangkan kebutuhan inferensi itu.
2. **Sesuai mental model standar** yang sudah dikenal luas dari tools sejenis (flowchart, UML, dependency graph tools) — user tidak perlu belajar konvensi baru, langsung paham begitu lihat.
3. **Membedakan "siapa yang bergantung ke siapa" krusial untuk keputusan refactor** — kalau user mau tau "kalau saya ubah `utils.py`, siapa yang kepengaruh", arah panah langsung jawab pertanyaan itu tanpa perlu klik satu-satu node buat baca `imported_names` di panel.

---

## Phase 2 — System Impact Analysis

**File yang kena detail:**
- `graps/frontend/graph.js` — 1 fungsi baru (`drawArrowhead`), 1 blok kode diedit di `draw()` (tambah pemanggilan setelah `ctx.stroke()` existing)

**Konflik dengan kode existing:** Tidak ada. Ini pure-additive — tidak ada fungsi yang dihapus, tidak ada signature yang berubah, tidak ada state baru yang bentrok dengan apapun (lihat Phase 3, state ownership — feature ini stateless).

**Bug tambahan yang ditemukan (di luar scope, dicatat saja):** Tidak ada temuan baru selama investigasi task ini.

**Race condition / edge case / bad path:**
- Edge dengan panjang sangat pendek (source dan target berdempetan, misal 2 file bersebelahan langsung tanpa jarak) — arrowhead bisa overlap dengan body node target kalau size-nya tidak proporsional. Mitigasi di Phase 4.
- Edge yang di-dim (alpha rendah, `focus` aktif tapi edge ini bukan yang di-fokus) — arrowhead harus ikut alpha yang sama, kalau lupa di-set bisa jadi "solid gelap" yang menonjol aneh di antara garis-garis yang di-dim.
- Setelah zoom-out ekstrem, arrowhead terlalu kecil untuk terlihat/dibaca — perlu cek apakah perlu minimum-size clamp (lihat Phase 4).

**Breaking changes:** Tidak ada. Murni penambahan visual, tidak ada API/data/state yang berubah untuk konsumen lain.

---

## Phase 3 — Design & Architecture

**Data structures (state baru):** TIDAK ADA. Tidak ada field baru di `store.state`, tidak ada field baru di data node/edge dari backend. Arrowhead dihitung 100% dari `s.x, s.y, t.x, t.y` yang sudah ada saat render — tidak perlu persistent state apapun.

**Interface contracts:**

| Fungsi | Input | Output | Catatan |
|---|---|---|---|
| `drawArrowhead(ctx, tipX, tipY, angleRad, size, color)` | `ctx`: CanvasRenderingContext2D; `tipX, tipY`: koordinat UJUNG LANCIP segitiga — titik ini HARUS berimpit persis dengan endpoint garis (`t.x - NODE_W/2, t.y`), BUKAN titik tengah segitiga; `angleRad`: arah lancip mengarah (radian, lihat catatan tangent di bawah); `size`: panjang sisi segitiga, sudah di-scale oleh `k` oleh caller; `color`: string warna (reuse `EDGE_COLORS.*` yang sudah ada) | void (langsung `ctx.fill()` di context yang di-pass) | Segitiga solid (`ArrowClosed` style). **Anchoring presisi:** base segitiga melebar ke arah `angleRad + π` (menjauh dari node, BUKAN simetris di sekitar `tipX,tipY`) — kalau salah anchor, separuh segitiga akan menembus body node target. Implementasi: `p1 = (tipX, tipY)` (lancip), `p2 = tipX - size*cos(angle-0.4), tipY - size*sin(angle-0.4)`, `p3 = tipX - size*cos(angle+0.4), tipY - size*sin(angle+0.4)` (2 titik base, sudut ±0.4 rad dari arah utama). Tidak mengubah `ctx.globalAlpha`/`ctx.strokeStyle` milik caller. |
| `draw()` (diedit) | — (baca `edges`, `visibleNodesCache`, `transform` seperti sekarang) | void | Setelah blok `ctx.stroke()` existing per edge (baris ~585 area), hitung `angleRad = Math.atan2(t.y - s.y, t.x - s.x - NODE_W/2)` dari titik kontrol bezier terakhir (BUKAN dari s ke t langsung — garisnya bezier, arah masuk ke target harus mengikuti tangent kurva di titik akhir, bukan garis lurus source-target, supaya visual konsisten dengan lengkungan) |

**State ownership:** Independen total. Tidak menyentuh `store.state` apapun, tidak menyentuh `graphOpenDirs`, tidak menyentuh visibility logic. Fungsi murni tambahan di render pass yang sudah ada.

**Catatan geometri (ditemukan saat review, penting untuk implementasi benar):**
- Karena control point kedua bezier (`midX, t.y`) Y-nya sama persis dengan endpoint (`t.x-NODE_W/2, t.y`), tangent kurva di titik akhir **selalu murni horizontal** (angle = 0 atau π, tidak pernah diagonal). Ini properti bawaan desain elbow-connector yang sudah ada.

**REVISI FINAL (menggantikan catatan "bug laten" versi sebelumnya):** Fixed-port (`source` selalu keluar dari sisi KANAN node, `target` selalu masuk dari sisi KIRI node, apapun posisi X relatifnya) **BUKAN bug — ini disengaja sebagai bahasa visual.** Semantik yang disepakati:
  - **Sisi KIRI node** = "import" — ada garis nempel di sini berarti node ini meng-import dari node lain.
  - **Sisi KANAN node** = "used by / export" — ada garis nempel di sini berarti node ini di-import oleh node lain.
  - **HANYA SATU arrowhead per edge**, dipasang di ujung KIRI (endpoint target/importer). Ujung KANAN (endpoint source/exporter) **tetap flat, TIDAK diberi marker apapun** — makna "used by" sudah cukup terbaca dari posisi port-nya sendiri (nempel di kanan), tidak perlu marker tambahan di situ.
  - Ini konsisten dengan pattern fixed-input/output-port yang umum di node-editor/dataflow diagram (mis. Node-RED) — bukan sesuatu yang perlu "diperbaiki" jadi dinamis.
  - Tidak ada perubahan kode dari desain awal Phase 3 — `drawArrowhead()` tetap dipanggil sekali per edge, di endpoint target saja. Catatan ini murni dokumentasi rasional, bukan perubahan implementasi.

**Flow (pseudocode):**
```
draw():
  ...(kode existing: hitung visibleIds, loop edges, gambar bezier + stroke seperti sekarang)...
  for setiap edge yang lolos filter visibility (kode existing tidak berubah):
    ...(existing: beginPath, moveTo, bezierCurveTo, strokeStyle, lineWidth, stroke)...

    // BARU — setelah stroke:
    tipX = t.x - NODE_W/2          // titik masuk ke sisi kiri node target (endpoint asli, tidak berubah dari existing)
    tipY = t.y
    // arah tangent bezier di titik akhir (t): vector dari titik kontrol kedua (midX, t.y) ke (tipX, tipY)
    angle = atan2(tipY - t.y, tipX - midX)   // hampir selalu mendekati 0 (horizontal) karena kontrol kedua sejajar Y dengan t
    drawArrowhead(ctx, tipX, tipY, angle, ARROW_SIZE / k, color)
      // color = variabel `color` yang SAMA yang sudah dipakai buat strokeStyle di atas — reuse, tidak hitung ulang
      // ctx.globalAlpha SUDAH di-set dari baris 566 (existing) sebelum loop ini — arrowhead otomatis ikut alpha yang sama karena globalAlpha berlaku ke semua operasi fill/stroke berikutnya sampai diubah lagi
```

---

## Phase 4 — Edge Cases & Failure Modes

| # | Kasus | Mitigasi |
|---|---|---|
| 1 | Edge sangat pendek, arrowhead overlap body node target | Clamp `ARROW_SIZE` ke nilai kecil tetap (misal 6px sebelum di-scale `/k`) — proporsional terhadap `NODE_W`, tidak dinamis mengikuti panjang edge. Kalau edge pendek, garis+panah keduanya pendek tapi tidak saling makan karena arrowhead cuma digambar di titik akhir, bukan sepanjang garis |
| 2 | Arrowhead tidak ikut dim/alpha state | Sudah di-cover di desain (arrowhead pakai `ctx.globalAlpha` yang sudah aktif dari baris 566 sebelum loop stroke — TIDAK reset alpha sebelum panggil `drawArrowhead`) — pastikan urutan kode: set alpha → stroke garis → gambar arrowhead (masih dalam alpha yang sama), BUKAN set alpha → gambar arrowhead → baru stroke garis |
| 3 | Zoom-out ekstrem, arrowhead terlalu kecil | `size = ARROW_SIZE / k` — karena `k` mengecil saat zoom-out, `size` justru membesar secara world-space, tapi visually tetap proporsional di layar (sama seperti `lineWidth = 1.5/k` yang sudah ada). TIDAK perlu clamp tambahan — pattern ini sudah terbukti benar dari `lineWidth` yang sudah eksis |
| 4 | Edge type `circular`/`function_call` yang pakai dashed line (`setLineDash`) | Arrowhead TETAP solid fill (bukan dashed) — dash cuma berlaku untuk `stroke()`, arrowhead pakai `fill()` terpisah, tidak akan ikut dash pattern secara otomatis. Tidak perlu mitigasi tambahan, tapi perlu di-manual-test untuk pastikan visual-nya tidak aneh (dash line masuk ke solid triangle) |
| 5 | Banyak edge menuju node yang sama (banyak arrowhead menumpuk di 1 titik masuk) | Diterima sebagai behavior normal untuk task ini — ini exact scenario yang akan diperbaiki nanti oleh approach-B (edge dedup by ancestor), bukan tanggung jawab task arrowhead ini. Tidak ada mitigasi tambahan di sini |

---

## Phase 5 — Resource & Constraint Check

- **Library baru:** Tidak ada. Pure Canvas2D API (`ctx.moveTo/lineTo/fill`) yang sudah dipakai di seluruh file ini.
- **Performance impact:** Diabaikan (negligible) — nambah 1 `beginPath`+3×`lineTo`+`fill()` per edge yang sudah lolos visibility-filter (jumlah edge visible sudah dibatasi lazy-render). Untuk skala graps sendiri (4-20 edges visible tipikal), ini bukan bottleneck.
- **Environment:** Browser Canvas2D, tidak ada constraint tambahan di luar yang sudah ada.

---

## Phase 6 — Testing Plan

**Unit tests:** Tidak applicable — fungsi ini pure Canvas drawing (side-effect ke `ctx`), tidak ada pure-logic yang bisa di-assert tanpa render pipeline penuh. (Beda dengan `isNodeVisible` kemarin yang pure-function dan bisa di-unit-test standalone.)

**Manual test scenarios:**

| Skenario | Expected |
|---|---|
| Load default (semua collapsed, cuma edge yang endpoint-nya visible di depth-0) | Arrowhead muncul di setiap edge yang ter-render, mengarah ke node target |
| Zoom in jauh (k besar) | Arrowhead tetap proporsional, tidak jadi raksasa |
| Zoom out jauh (k kecil) | Arrowhead tetap terlihat, tidak hilang/terlalu kecil untuk dibaca |
| Klik node → edge yang terhubung ke node itu di-highlight (alpha tinggi), edge lain di-dim | Arrowhead di edge yang di-highlight ikut solid/jelas, arrowhead di edge yang di-dim ikut pudar sama seperti garisnya |
| Edge type `circular`/`function_call` (dashed line) | Garis dashed seperti biasa, arrowhead tetap solid triangle di ujungnya (tidak ikut dashed) |
| Edge sangat pendek (2 node bersebelahan) | Arrowhead tidak menembus/overlap parah ke body node target |
| Banyak edge ke 1 node yang sama | Arrowhead menumpuk di titik yang sama — diterima, sesuai Phase 4 #5 |

**Staging/dev verification:** Jalankan `graps` CLI lokal (`graps <path> --host 127.0.0.1 --port <port> --no-browser`, BUKAN `python -m graps.cli` — itu trigger self-check mode, bukan server beneran), buka browser, jalankan checklist manual di atas.

**Production monitoring:** Tidak applicable (pure client-side visual, tidak ada failure mode yang perlu di-log — kalau `drawArrowhead` error, seluruh `draw()` akan throw dan canvas blank, itu akan langsung kelihatan sendiri saat manual test, tidak perlu instrumentasi tambahan).

---

## Self-check (wajib dijawab sebelum plan ini final)

**Apakah ini desain paling umum? (app yang menggunakannya)**
Ya. Solid-triangle arrowhead (`ArrowClosed`-style) adalah default di **React Flow** (dipakai n8n, banyak workflow-builder tools), **Graphviz**, **Mermaid.js flowchart**, dan UML tooling secara umum. React Flow secara eksplisit expose 2 opsi built-in: `Arrow` (open/chevron) dan `ArrowClosed` (solid) — riset Phase 0 mengonfirmasi solid-triangle adalah opsi default/lebih umum dipakai dibanding chevron terbuka.

**Apakah ini approach terbaik dari yang terbaik?**
Untuk scope sekecil ini (indicator arah doang, bukan interactive edge routing), ya — pendekatan "compute tangent angle di endpoint, gambar triangle kecil" adalah cara paling ringan (tidak butuh library baru, tidak butuh SVG marker system seperti React Flow yang berbasis SVG bukan Canvas). Karena `graps` pakai Canvas2D (bukan SVG), pattern React Flow tidak bisa di-copy 1:1 (mereka pakai `<marker>` SVG def), tapi prinsip visualnya (solid triangle di endpoint, mengikuti tangent garis) tetap sama — cuma implementasi teknisnya disesuaikan ke Canvas2D primitives.

**Apakah sudah melakukan deep research?**
Ya — web search dilakukan terhadap React Flow documentation (`reactflow.dev/examples/edges/markers`, `MarkerType` API reference) sebagai referensi utama karena React Flow adalah library node-graph paling banyak dipakai untuk use-case yang sangat mirip (canvas/interactive node+edge diagram) dengan `graps`.

---

## Catatan di luar 3 kategori pertanyaan yang diizinkan

*(Tidak ada catatan terbuka — temuan geometri sebelumnya soal "sisi kiri/kanan" sudah diklarifikasi dan direvisi di Phase 3: itu bukan bug, melainkan bahasa visual yang disengaja (kiri=import, kanan=used-by), dan tidak mengubah implementasi yang sudah direncanakan.)*

**Status: APPROVED, siap diimplementasikan.**


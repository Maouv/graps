# PLAN: Fix Edge Bezier Curve Overlap dengan Node (Same-Column Siblings)

**Repo:** `Maouv/graps`
**File utama:** `graps/frontend/graph.js`

---

## Phase 0 — Context Intake

- **Branch:** `fix/edge-resolution-tree-sitter` (branch yang sudah ada, ini lanjutan kerjaan di situ — BUKAN branch baru, karena bug ini ketemu SAAT testing hasil kerjaan branch itu)
- **File yang kena dampak:** `graps/frontend/graph.js` SAJA
- **Fungsi yang akan diedit:**
  - `draw()` — blok edge-drawing (~baris 605-611), 1 formula (`midX`) diganti, tidak ada fungsi baru dibuat, tidak ada fungsi dihapus
- **Tanggal mulai:** 2026-07-12

---

## Phase 1 — Definition

**Problem statement:** Bezier curve yang menghubungkan edge antar node menggunakan formula `midX = s.x + (t.x - s.x) * 0.5` untuk control point. Ketika source dan target berada di kolom/depth yang sama (kasus sibling-import-sibling, misal `graph_builder.py → resolver.py` yang sama-sama langsung di bawah `scanner/`), `s.x === t.x` sehingga `midX` kolaps jadi sama dengan `s.x`/`t.x`. Kurva bezier degenerate menjadi garis vertikal lurus yang menembus tepat di tengah setiap node card yang berada di antara posisi Y source dan target — mengaburkan card lain dan membuat graph sulit dibaca.

**Done criteria (draft — koreksi/tambah kalau ada yang kurang):**
- Edge antar node same-column tidak lagi menembus body node lain di antaranya
- Edge cross-column (kasus yang sudah berfungsi benar sebelumnya) tetap terlihat identik — tidak ada regresi visual untuk kasus yang sudah benar
- Fix berlaku otomatis untuk SEMUA edge same-column, tidak hardcode untuk pasangan node tertentu

**Out of scope (konfirmasi — ini TIDAK dikerjakan di task ini):**
- **Tidak mengadopsi library layout dedicated** (Dagre/ELKjs) — riset Phase 0 mengonfirmasi ini ada di ekosistem sebagai solusi "proper", tapi itu perubahan arsitektur besar (dependency baru, kemungkinan perlu re-arsitektur seluruh sistem layout `computeTreeLayout()` yang sudah ada), di luar proporsi untuk bug fix ini
- **Tidak menyelesaikan kasus banyak edge same-column saling tumpuk** (kalau 1 node source punya 3+ sibling-edge, semuanya bulge ke offset X yang sama, berpotensi tumpang tindih SATU SAMA LAIN — bukan lagi menembus node, tapi masih bisa terlihat ramai). Dicatat sebagai known limitation, bukan blocker untuk fix ini.
- **Tidak mengubah bentuk dasar kurva** (tetap elbow-bezier S-curve, bukan orthogonal routing atau garis lurus)

**Consumer — kenapa ini bagus untuk UX (minimal 3 alasan):**
1. **Keterbacaan graph adalah value proposition inti tools ini.** Kalau edge menembus node, user tidak bisa membedakan "garis ini lewat di depan card A" vs "garis ini benar-benar terhubung ke card A" — ambiguitas ini merusak kepercayaan terhadap keakuratan visual seluruh graph.
2. **Kasus ini justru yang PALING SERING terjadi**, bukan edge case langka — sibling-file-mengimpor-sibling-file (dua file dalam folder yang sama saling terhubung) adalah pola paling umum di kebanyakan codebase nyata (helper functions dalam 1 module saling dipanggil).
3. **Konsisten dengan investasi arrow-direction yang baru saja diimplementasikan** — percuma punya arrowhead yang presisi menunjukkan arah kalau garis itu sendiri tidak jelas terlihat kemana dia sebenarnya menuju karena tertutup card lain.

---

## Phase 2 — System Impact Analysis

**File yang kena detail:** `graps/frontend/graph.js` — 1 baris formula diganti jadi 3 baris (lihat Phase 3), tidak ada file lain tersentuh.

**Konflik dengan kode existing:** Tidak ada konflik struktural. Perubahan ini murni menggantikan nilai `midX` yang dipakai oleh `bezierCurveTo()` (baris existing) dan `drawArrow()` (baris existing, sudah pakai `midX` untuk hitung arah panah — lihat catatan penting di Phase 4).

**Bug tambahan yang ditemukan:** Tidak ada temuan baru selama investigasi task ini (di luar yang sudah dilaporkan di task arrow sebelumnya).

**Race condition / edge case / bad path:**
- `drawArrow()` (dari task sebelumnya) menghitung arah panah pakai `Math.sign(tx2 - midX)`. Karena `midX` sekarang berubah formula, arah panah untuk edge same-column HARUS dicek ulang — sebelumnya `midX === tipX` (degenerate, `Math.sign(0) → 0 → fallback ke 1` karena ada `|| 1`), sekarang `midX` bergeser menjauh dari `tipX` sehingga tanda `Math.sign` bisa berubah. Ini BUKAN bug baru dari fix ini, tapi INTERAKSI dengan kode yang sudah ada — harus dicek manual (lihat Phase 6).
- Kalau `NODE_W` dinamis (beberapa card lebih lebar dari yang lain, tergantung isi), `NODE_W * 1.0` yang dipakai sebagai basis minimum bulge itu konstanta GLOBAL, bukan lebar node spesifik yang sedang digambar — ada kemungkinan untuk card yang jauh lebih lebar dari `NODE_W` standar, bulge minimum tetap tidak cukup. Perlu dicek apakah `NODE_W` di file ini konstanta tetap atau dihitung dinamis per-node.

**Breaking changes:** Tidak ada. Murni perubahan visual rendering, tidak ada API/data/state yang berubah.

---

## Phase 3 — Design & Architecture

**Data structures (state baru):** TIDAK ADA. Perubahan murni lokal di dalam fungsi `draw()`, tidak ada field baru di manapun.

**Interface contracts:**

| Fungsi | Input | Output | Catatan |
|---|---|---|---|
| `draw()` (diedit, bukan fungsi baru) | — (baca `s.x, s.y, t.x, t.y, NODE_W` seperti sekarang) | void | Baris `const midX = s.x + (t.x - s.x) * 0.5;` diganti dengan 3 baris (lihat pseudocode). Tidak ada fungsi baru dibuat — perbaikan ini cukup kecil untuk tetap inline, membuat fungsi terpisah untuk 1 kalkulasi 3-baris dianggap over-engineering untuk scope ini. |

**State ownership:** Independen total. Tidak menyentuh `store.state`, tidak menyentuh visibility logic, tidak menyentuh `graphOpenDirs`.

**Flow (pseudocode) — REVISI setelah ditemukan kontradiksi internal saat implementasi:**

Formula awal (`bulge = Math.max(abs(rawGap)*0.5, NODE_W*1.0)`) ternyata menyebabkan
regresi visual untuk edge cross-column 1-kolom (kasus paling umum: folder → direct
child) — melanggar Done Criteria #2 sendiri. Root cause: `colX(depth)` diskrit
(`= 145 + depth*290`), sehingga `rawGap` HANYA BISA persis `0` (same-column) atau
kelipatan pasti `290` (beda kolom) — tidak pernah ada nilai di antaranya. Karena
tidak ada gray-area, guard exact `rawGap === 0` sudah cukup presisi — TIDAK perlu
`Math.max`/interpolasi, dan TIDAK ada trade-off "hampir same-column" yang perlu
di-smooth.

```
draw():
  ...(kode existing sebelum blok edge tidak berubah)...
  for setiap edge yang lolos visibility filter (kode existing, tidak berubah):
    rawGap = t.x - s.x
    midX = (rawGap === 0)
      ? s.x + NODE_W * 1.0          // same-column SAJA — bulge keluar kolom
      : s.x + rawGap * 0.5          // cross-column — formula ASLI, 0 perubahan

    // sisanya IDENTIK dengan kode existing:
    beginPath(); moveTo(s.x+NODE_W/2, s.y)
    bezierCurveTo(midX, s.y, midX, t.y, t.x-NODE_W/2, t.y)
    stroke()
    drawArrow(tx2, ty2, sign(tx2 - midX) || 1, 0, color, k)   // tidak diubah
```

---

## Phase 4 — Edge Cases & Failure Modes

| # | Kasus | Mitigasi |
|---|---|---|
| 1 | Edge same-column (kasus utama bug ini) | Fixed oleh `Math.max(..., NODE_W * 1.0)` — bulge minimum terjamin walau `rawGap === 0` |
| 2 | Interaksi dengan `drawArrow()` yang sudah ada dari task sebelumnya | Tidak perlu ubah `drawArrow()` — dia sudah menerima `midX` sebagai parameter kalkulasi, otomatis dapat nilai baru yang benar. TAPI wajib manual-test ulang arah panah untuk edge same-column spesifik (sebelumnya degenerate ke fallback `|| 1`, sekarang dapat nilai sign yang benar-benar dihitung) |
| 3 | Banyak edge same-column dari 1 source (tumpuk sesama edge, bukan lagi menembus node) | Diterima sebagai known limitation (lihat Phase 1 out-of-scope) — TIDAK dimitigasi di task ini |
| 4 | `NODE_W` mungkin tidak selalu representatif untuk semua card (kalau ada card lebih lebar) | Perlu verifikasi cepat: cek apakah `NODE_W` di kode adalah konstanta fixed atau dihitung dinamis. Kalau fixed konstanta, aman — bulge minimum konsisten. Kalau ternyata beberapa card override lebar sendiri, `NODE_W * 1.0` sebagai basis mungkin kurang untuk card itu — perlu dicek saat implementasi, bukan diasumsikan aman |
| 5 | Edge yang arahnya "mundur" (target secara X ada di kiri source) | Formula `rawGap >= 0 ? s.x+bulge : s.x-bulge` sudah menghandle kedua arah — bulge selalu ke arah yang sesuai dengan sisi target, tidak hardcode satu arah saja |

---

## Phase 5 — Resource & Constraint Check

- **Library baru:** TIDAK ADA untuk fix ini. **Dicatat sebagai alternatif yang SENGAJA tidak dipilih:** Dagre atau ELKjs adalah solusi "proper" untuk masalah kelas ini (dikonfirmasi lewat riset — dipakai luas oleh React Flow, Svelte Flow), tapi itu dependency baru + kemungkinan perlu re-arsitektur `computeTreeLayout()` yang sudah ada — proporsinya jauh lebih besar dari bug yang sedang diperbaiki. Heuristic bulge-offset ini adalah trade-off pragmatis: menyelesaikan kasus paling umum (same-column) dengan biaya minimal, bukan solusi general-purpose untuk semua kasus edge-crossing.
- **Performance impact:** Negligible — perubahan formula matematis sederhana (1 `Math.max`, 1 ternary), dihitung ulang per-edge per-frame seperti kalkulasi lain yang sudah ada di loop yang sama.
- **Environment:** Tidak ada constraint tambahan.

---

## Phase 6 — Testing Plan

**Unit tests:** Tidak applicable — sama seperti task arrow sebelumnya, ini pure Canvas rendering, tidak ada logic yang bisa di-assert tanpa render pipeline penuh.

**Manual test scenarios:**

| Skenario | Expected |
|---|---|
| Edge same-column (`graph_builder.py → resolver.py`, sama-sama di `scanner/`) | Garis melengkung keluar dari kolom (bracket-shape), TIDAK menembus card lain di antaranya |
| Edge cross-column yang sudah benar sebelumnya (misal `cli.py → scanner/graph_builder.py`) | Visual TIDAK berubah dari sebelumnya — tidak ada regresi |
| Arah arrowhead pada edge same-column | Panah tetap mengarah masuk ke target (bukan terbalik) — verifikasi ulang karena `midX` berubah, `drawArrow()` bergantung padanya |
| Node dengan 3+ edge same-column sekaligus | Semua garis clear dari body node (tidak menembus), walau mungkin saling tumpuk sesama garis — ini DITERIMA sesuai Phase 1 out-of-scope, bukan kegagalan test |
| Zoom in/out setelah fix | Bulge tetap proporsional, tidak ada distorsi aneh saat scale berubah |

**Staging/dev verification:** Jalankan `graps <path> --host 127.0.0.1 --port <port> --no-browser` (BUKAN `python -m graps.cli`), scan repo yang punya banyak sibling-import (`graps` sendiri sudah cukup representatif — `scanner/` punya beberapa file saling terhubung), jalankan checklist manual di atas.

**Production monitoring:** Tidak applicable — pure visual, kalau ada error JS di `draw()`, canvas akan blank/error terlihat langsung saat manual test.

---

## Self-check

**Apakah ini desain paling umum? (app yang menggunakannya)**
Sebagian. Bulge-offset minimum untuk menghindari degenerate same-rank edge adalah pola umum di implementasi ringan/manual (non-library) dari elbow-connector diagrams. TAPI riset mengonfirmasi solusi yang lebih "proper"/canonical di ekosistem adalah dedicated layout engine (**Dagre**, dipakai React Flow/Svelte Flow sebagai rekomendasi utama mereka untuk tree layout; **ELKjs** untuk kasus lebih kompleks) — keduanya secara eksplisit menangani masalah sibling-edge-overlap sebagai bagian dari algoritma constraint-solving mereka, bukan heuristic sederhana seperti fix ini.

**Apakah ini approach terbaik dari yang terbaik?**
**Tidak, dan ini jujur perlu diakui.** Solusi terbaik-dari-terbaik untuk edge-routing yang benar-benar menghindari SEMUA obstacle adalah algoritma visibility-graph/obstacle-avoiding routing (riset akademis dikonfirmasi — lihat "Edge Routing with Ordered Bundles", arxiv 1209.4227) atau adopsi Dagre/ELKjs. Fix ini adalah **pragmatic heuristic** yang menyelesaikan kasus paling umum (same-column) dengan biaya implementasi minimal (3 baris, 0 dependency baru), BUKAN solusi general untuk semua kemungkinan edge-crossing. Trade-off ini eksplisit dipilih karena proporsional dengan skala masalah yang dilaporkan — bukan diklaim sebagai solusi definitif.

**Apakah sudah melakukan deep research?**
Ya — web search terhadap Dagre/ELKjs issue trackers (mengonfirmasi ini masalah yang dikenal luas, bahkan library mapan pun struggle dengan sibling-edge-overlap), dan paper akademis edge-routing (arxiv 1209.4227) sebagai referensi upper-bound dari kompleksitas solusi "sempurna" — dipakai untuk secara jujur mengkalibrasi bahwa fix ini adalah trade-off pragmatis, bukan state-of-the-art.

---

## Catatan di luar 3 kategori pertanyaan yang diizinkan

**Revisi pasca-review implementasi:** Formula Phase 3 awal (`Math.max`) diganti jadi
exact guard `rawGap === 0` — root cause & alasan lengkap ada di Phase 3 (revisi).
Verifikasi `NODE_W` (Phase 4 #4) sudah dicek: `const NODE_W = 210;` (baris 57) —
konstanta fixed. `colX(depth) = 145 + depth*290` (baris 93) — diskrit, dikonfirmasi
tidak ada nilai `rawGap` di antara 0 dan 290, sehingga exact-guard valid tanpa
gray-area.

**Status: APPROVED (revisi), siap diimplementasikan.**


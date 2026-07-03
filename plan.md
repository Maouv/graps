   
   file perencaan pengimplentasian PHASE5_frontend.md
   ---

   Fase A — Foundation (harus selesai duluan, semua UI depend)

   A1. State extension — graps/frontend/filter.js
   - Tambah store.state.sidePanel (bool), openDirs (Set), aiHistory (array),
   activePanel (null|'sidebar'|'sidepanel'|'ai').
   - Gak ubah setState / addEventListener pola yang ada.
   - Acceptance: store.state.activePanel === null di boot, setState({activePanel:'ai'})     dispatch change event dengan keys.
   - Dep: none.

   A2. HTML layout — graps/frontend/index.html
   - Struktur baru: #app-layout > #dir-sidebar + #graph-wrap(+#node-popover) + #side-
   panel, plus #ai-bar di bawah.
   - PENTING: preserve ID yang dipakai file lain (#graph-canvas, #tooltip, #search-
   overlay, #toast-container, #loading-screen, #empty-state, #zoom-level, #warning-
   banner, topbar). Ganti #canvas-wrap→#graph-wrap → update semua reference di graph.js/
   search.js juga (di task masing-masing).
   - Tambah script tag sidebar.js + ai.js setelah panel.js.
   - Acceptance: semua ID lama masih ada + ID baru ada. Graph boot gak null.
   - Dep: none.

      A3. CSS — graps/frontend/style.css
   - Define :root { --topbar-height: 48px; --ai-bar-height: 56px; }.
   - Responsive: desktop grid 220px 1fr 0px, side-panel slide kanan, ai-bar bottom
   fixed. Mobile: flex column, sidebar strip 44px, side-panel bottom sheet, ai-bar
   collapsed tab.
   - Komponen baru: .dir-item, .depth-N, .node-popover, .ai-bar, .ai-tag, .ai-message,
   chevron states.
   - prefers-reduced-motion cover animasi baru.
   - Acceptance: gak ada var undefined, layout gak pecah di 320px/768px/1440px.
   - Dep: A2 (butuh struktur DOM).

   ---

   Fase B — Graph rendering (graph.js, urutan internal)                                  
   B1. Rectangle node — graps/frontend/graph.js
   - drawNode rewrite: roundRect + nodeWidth/nodeHeight (zoom-aware), filename header,      function list (max 5), import count.
   - Update #canvas-wrap→#graph-wrap reference di boot.
   - Acceptance: node tampil rectangle, function name kelihatan saat zoom in, header-
   only saat zoom out (<0.5).
   - Dep: A2.

   B2. Bezier edge + arrow di border — graps/frontend/graph.js
   - drawEdge bezier curve, 3 warna (import/circular/function_call), dashed untuk
   circular, ⚠b circular label.
   - drawArrow di border rectangle (pakai rectBorderIntersection), bukan center.
   - Acceptance: arrow kelihatan di tepi node, circular edge merah dashed + label.          - Dep: B1 (butuh nodeWidth/Height).

   B3. Hit detection rectangle — graps/frontend/graph.js
   - nodeAt: quadtree.find initial filter + rectangle hit test (bukan circle radius).
   - Acceptance: klik di dalam rectangle = hit, klik di luar = miss, walau node beda
   size.
   - Dep: B1.

   B4. Ghost node — graps/frontend/graph.js
   - supported === false → dashed border + opacity 0.5. (Sudah ada sebagian, sesuaikan
   ke rectangle.)
   - Acceptance: ghost node kelihatan beda, gak bisa di-select (graph.js click guard n.
   supported !== false tetap).
   - Dep: B1.

   B5. Edge tooltip — graps/frontend/graph.js
   - edgeAt() brute-force O(edges), mousemove handler, tooltip "import"/"function call"/
   "circular". Reuse showTooltip.
   - Acceptance: hover edge → tooltip muncul teks type-nya.
   - Dep: B2.

   B6. openDirs filter — graps/frontend/graph.js
   - Listen graps:dirs-changed event → filter nodes visible berdasarkan store.state.
   openDirs.
   - Acceptance: toggle dir di sidebar → node di graph muncul/hilang.
   - Dep: B1, A1.

   ---

   Fase C — Panels (panel.js)

   C1. Popover — graps/frontend/panel.js                                                    - showPopover/hidePopover, nodeToScreen, positionPopover (flip kiri kalau nabrak).
   Trigger: store.addEventListener('change') filter selectedNode.
   - Acceptance: klik node → popover muncul di samping, flip kalau dekat tepi kanan.
   - Dep: A1, B3 (hit detection).

   C2. Side panel — graps/frontend/panel.js
   - showSidePanel, combobox fungsi/import, source viewer placeholder. Close button →
   setState({sidePanel:false}).
   - Acceptance: klik › di popover → side panel slide in, close → slide out.
   - Dep: C1.
                                                                                            C3. Caller/callee nav (preservasi) — graps/frontend/panel.js
   - PERHATIAN: spec §3 bilang "replace existing", tapi panel.js aktual punya caller/
   callee clickable (pan graph) + risk cards. Keep fitur itu di side panel, jangan
   hapus. Render di atas/bawah combobox source.
   - Acceptance: klik caller di side panel → graph pan ke node itu (via graps:pan-to).
   - Dep: C2.

   ---

   Fase D — Sidebar + AI (file baru)

   D1. Directory sidebar — graps/frontend/sidebar.js (file baru)
   - buildDirTree, renderTree (zsh-style mobile: slice(-2)), toggleDirectory,
   expandDirectory (dipanggil ghost node). Dispatch graps:dirs-changed.                     - Acceptance: desktop: tree indent, klik expand. Mobile: strip flat zsh-style, depth
   context preserved.
   - Dep: A1, A2.

   D2. AI bar — graps/frontend/ai.js (file baru)
   - Persistent bottom chat. sendMessage (POST /api/ai/chat), implicit context dari
   selectedNode, /new clear, injectTag (dari side panel).
   - Acceptance: ketik + Enter → reply muncul, selectedNode otomatis jadi context, /new
   reset.
   - Dep: A1, A2.

   ---

   Fase E — Mobile orchestration

   E1. activePanel logic — cross-cutting (filter.js helper + tiap panel)
   - Helper buka panel: setActivePanel(name) → tutup lain via class, set state. Tiap
   panel (sidebar/sidepanel/ai) panggil ini saat buka.
   - Acceptance: mobile, buka AI bar → sidebar & side panel auto-tutup. Cuma 1 terbuka.     - Dep: D1, D2, C2.

   ---

   Fase F — Backend source (TERAKHIR, spec §10)

   F1. /api/source endpoint — graps/server/app.py
   - GET /api/source?file=&fn=. Path traversal guard (resolve + relative_to). Reuse
   _extract_function_body yang sudah ada (line_start/line_end dari graph metadata),
   jangan duplikat.
   - Acceptance: valid file → source, .. traversal → 400, fn not found → 404.
   - Dep: semua UI selesai.

   F2. Prism.js integration — graps/frontend/index.html + panel.js
   - CDN Prism core + python/js/typescript. loadSourceCode fetch /api/source, render
   <code>, Prism.highlightElement.
   - Acceptance: pilih fungsi di combobox → source code highlight muncul.
   - Dep: F1.

   ---

   Fase G — Verify

   G1. Test suite — tests/
   - Run pytest. Target: 91 pass minimum, zero regresi.                                     - Acceptance: 91/91 pass.
   - Dep: F2.

   G2. Manual flow verify — checklist §11 step 13-16
   - Klik node→popover→›→panel. Dir sidebar toggle→ghost→expand. AI implicit context.
   Responsive mobile.
   - Acceptance: semua flow jalan.
   - Dep: G1.

   ---

   Aturan anti-bentrok

   - 1 file = 1 task di waktu berjalan. Jangan dua orang/two step sentuh graph.js
   bareng.
   - Dependency wajib done sebelum mulai. Cek status tiap mulai.
   - Spec = source of truth. Kalau kode aktual konflik sama spec (misal #canvas-wrap vs
   #graph-wrap), ikut spec + update reference di file terkait di task itu juga.
   - Jangan tambah fitur di luar spec. /new hint, floor auto-expand, drawer mobile =
   out of scope, catat aja.

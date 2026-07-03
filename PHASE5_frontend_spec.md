# Phase 5 — Frontend Rewrite Spec

> Reference: BLUEPRINT.md §8 (UX Flow), PHASE5.md (AI Chat)
> Pre-condition: Bug fixes dari report-cases.md sudah applied — VERIFIED 90/91 pass
> Remaining minor issue: test_cache.py language mismatch (English vs Indonesian) — fix string di cli.py "is not yet in .gitignore" → "belum ada di .gitignore"
> Scope: Rectangle nodes, bezier edges, popover, side panel, directory sidebar, AI chat layout, responsive

---

## 0. Keputusan Final (Jangan Re-discuss)

| Keputusan | Alasan |
|-----------|--------|
| Node shape: rectangle, bukan circle | Lebih informative — filename + function count + import count visible |
| Edge: bezier curves dengan panah | Direction clear (A→B = A import B), natural untuk dependency graph |
| Edge warna: hijau=import, biru=function call, merah=circular/error | Color-coded per relationship type |
| Edge legend: tooltip on hover edge (bukan kotak permanent) | Zero clutter — user tau arti warna tali saat hover, gak ada noise permanent |
| Popover trigger: klik node | Universal — works di mobile (touch) dan desktop (click) |
| Popover → klik `>` → side panel | Progressive disclosure, tidak overwhelm user di awal |
| Side panel: slide in desktop, bottom sheet mobile | Responsive — tidak ada persistent side panel di mobile |
| Directory sidebar: default kosong, user explore sendiri | User autonomy — tidak di-suapin |
| Ghost nodes: dashed border + opacity 50% | Cross-directory edges tidak menggantung, user discover via ghost |
| AI chat: persistent bottom bar desktop, collapsed bottom tab mobile | Cross-file Q&A lebih natural dari AI di side panel |
| selectedNode = implicit AI context | User tidak perlu @tag manual untuk node yang sedang dipilih |
| /new command = clear conversation | Zero server state, stateless fresh session |
| Source code viewer: Prism.js, endpoint GET /api/source | Defer ke TERAKHIR dalam phase ini — implement setelah semua UI selesai |
| Tooltip vanilla JS | No React, no Chakra, no build step |

---

## 1. Prinsip Wajib

1. Simple tapi works — jangan over-engineer komponen UI.
2. Zero build step — vanilla JS, no React, no npm dependency baru kecuali CDN.
3. Responsive first — setiap komponen harus di-design untuk mobile dan desktop sekaligus.
4. selectedNode adalah single source of truth — semua UI yang react terhadap node selection harus listen dari `store.state.selectedNode`, bukan implement state sendiri.
5. Scanner layer TIDAK disentuh — hanya frontend/ dan minimal app.py (endpoint baru).
6. Jangan rewrite store.js atau state management — extend yang sudah ada.

---

## 2. State Yang Sudah Ada (Jangan Diubah)

```javascript
// store.state yang sudah exist dan harus tetap:
store.state.selectedNode    // node yang diklik user — SINGLE SOURCE OF TRUTH
store.state.hoveredNode     // node yang di-hover
store.state.filter          // { risk: "high"|null, dead: bool }
store.state.graph           // full graph data dari /api/graph
```

**Tambahan state baru yang dibutuhkan:**

```javascript
store.state.sidePanel       // bool — apakah side panel terbuka
store.state.openDirs        // Set<string> — directory yang sudah di-expand user
store.state.aiHistory       // array — conversation history untuk session ini
                            // di-clear saat /new command
store.state.activePanel     // null|'sidebar'|'sidepanel'|'ai' — mobile: panel yang
                            // sedang terbuka (cuma 1 boleh terbuka dalam satu waktu)
```

---

## 3. File Yang Diubah

```
graps/frontend/graph.js      — rectangle nodes, bezier edges, ghost nodes, panah
graps/frontend/panel.js      — popover + side panel (replace existing)
graps/frontend/index.html    — layout baru (sidebar + graph + bottom AI bar)
graps/frontend/style.css     — responsive breakpoints, new components
graps/server/app.py          — tambah GET /api/source endpoint (TERAKHIR)

Yang TIDAK disentuh:
graps/frontend/filter.js     — tidak ada perubahan
graps/frontend/search.js     — tidak ada perubahan
graps/frontend/toast.js      — tidak ada perubahan
graps/scanner/               — tidak ada perubahan
```

---

## 4. Layout HTML (index.html)

```html
<body>
  <!-- Top bar: sudah ada, tidak berubah -->
  <div id="topbar">...</div>

  <!-- Warning banner: sudah ada, tidak berubah -->
  <div id="warning-banner">...</div>

  <!-- Main layout -->
  <div id="app-layout">

    <!-- Sidebar kiri: directory tree -->
    <aside id="dir-sidebar">
      <!-- Diisi oleh sidebar.js -->
    </aside>

    <!-- Graph canvas: center -->
    <div id="graph-wrap">
      <canvas id="graph-canvas"></canvas>
      <!-- Popover: absolute positioned, dikelola panel.js -->
      <div id="node-popover" class="hidden"></div>
    </div>

    <!-- Side panel: kanan desktop, bottom sheet mobile -->
    <aside id="side-panel" class="hidden">
      <!-- Diisi oleh panel.js -->
    </aside>

  </div>

  <!-- AI chat bar: persistent bottom -->
  <div id="ai-bar">
    <div id="ai-messages"></div>
    <div id="ai-input-row">
      <div id="ai-tags"></div>
      <input id="ai-input" type="text" placeholder="Tanya tentang @node ini..." />
      <button id="ai-send">↑</button>
    </div>
  </div>

</body>
```

---

## 5. Responsive CSS Breakpoints

```css
:root {
  --topbar-height: 48px;
  --ai-bar-height: 56px;
}

/* Desktop (>768px): sidebar + graph + side panel + bottom AI bar */
@media (min-width: 769px) {
  #app-layout {
    display: grid;
    grid-template-columns: 220px 1fr 0px; /* side panel width = 0 saat closed */
    grid-template-areas: "sidebar graph sidepanel";
  }

  #side-panel {
    /* Slide in dari kanan */
    width: 320px;
    position: fixed;
    right: 0;
    top: var(--topbar-height);
    bottom: var(--ai-bar-height);
    transform: translateX(100%);
    transition: transform 220ms ease;
  }

  #side-panel.open {
    transform: translateX(0);
  }

  #ai-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--ai-bar-height); /* collapsed default */
  }
}

/* Mobile (<768px): stack vertical, bottom sheet */
@media (max-width: 768px) {
  #app-layout {
    display: flex;
    flex-direction: column;
  }

  #dir-sidebar {
    /* Horizontal scrollable strip di atas graph */
    display: flex;
    overflow-x: auto;
    height: 44px;
  }

  #side-panel {
    /* Bottom sheet */
    position: fixed;
    bottom: var(--ai-bar-height);
    left: 0;
    right: 0;
    height: 60vh;
    transform: translateY(100%);
    transition: transform 220ms ease;
    border-radius: 16px 16px 0 0;
  }

  #side-panel.open {
    transform: translateY(0);
  }

  #ai-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    /* Mobile: collapsed = tab kecil, tap untuk expand */
  }
}
```

**Mobile rule (WAJIB):** cuma 2 panel boleh terbuka dalam satu waktu. State `store.state.activePanel` (null | 'sidebar' | 'sidepanel' | 'ai') — buka s2 → tutup lain via `setState`. Tiap panel punya chevron buka/tutup (› ‹ horizontal, ^ v vertikal), transisi 220ms, ikut `prefers-reduced-motion`.

---

## 6. graph.js — Rectangle Nodes + Bezier Edges

### 6.1 Node rendering — ganti `ctx.arc()` ke rectangle

```javascript
const NODE_MIN_WIDTH = 140;   // px, world space
const NODE_HEIGHT_BASE = 44;  // px untuk header saja
const NODE_LINE_HEIGHT = 18;  // px per function/import line
const NODE_PADDING = 10;      // px horizontal padding

function nodeWidth(n) {
  // Lebar berdasarkan panjang filename
  const textWidth = ctx.measureText(n.id.split('/').pop()).width;
  return Math.max(NODE_MIN_WIDTH, textWidth + NODE_PADDING * 2);
}

function nodeHeight(n, zoomK) {
  // Zoom out (k < 0.5): hanya header
  if (zoomK < 0.5) return NODE_HEIGHT_BASE;
  // Zoom in: header + function lines (max 5, sisanya "+N more")
  const fns = (n.functions || []).slice(0, 5);
  return NODE_HEIGHT_BASE + fns.length * NODE_LINE_HEIGHT + 8;
}

function drawNode(n) {
  const k = transform.k;
  const w = nodeWidth(n);
  const h = nodeHeight(n, k);
  const x = n.x - w / 2;
  const y = n.y - h / 2;
  const r = 6; // border radius

  // Background fill
  ctx.fillStyle = n.supported === false ? NODE_FILL_UNSUPPORTED : NODE_FILL;
  roundRect(ctx, x, y, w, h, r);
  ctx.fill();

  // Border — warna berdasarkan risk
  const risk = nodeRisk(n);
  ctx.strokeStyle = RING[risk] || RING.clean;
  ctx.lineWidth = (RING_WIDTH[risk] || 1.5) / k;
  if (n.supported === false) {
    // Ghost node: dashed border
    ctx.setLineDash([4 / k, 4 / k]);
  }
  roundRect(ctx, x, y, w, h, r);
  ctx.stroke();
  ctx.setLineDash([]);

  // Selected: glow effect
  if (store.state.selectedNode === n) {
    ctx.shadowColor = RING[risk] || RING.clean;
    ctx.shadowBlur = 8 / k;
    roundRect(ctx, x, y, w, h, r);
    ctx.stroke();
    ctx.shadowBlur = 0;
  }

  // Opacity untuk ghost nodes
  ctx.globalAlpha = n.supported === false ? 0.5 : 1.0;

  // Filename header
  ctx.fillStyle = INK_PRIMARY;
  ctx.font = `600 ${12 / k}px Sora, sans-serif`;
  ctx.fillText(
    truncate(n.id, w - NODE_PADDING * 2, ctx),
    x + NODE_PADDING,
    y + 16 / k
  );

  // Divider
  if (k >= 0.5) {
    ctx.strokeStyle = BG_BORDER;
    ctx.lineWidth = 1 / k;
    ctx.beginPath();
    ctx.moveTo(x, y + NODE_HEIGHT_BASE - 8);
    ctx.lineTo(x + w, y + NODE_HEIGHT_BASE - 8);
    ctx.stroke();

    // Function list (max 5)
    const fns = (n.functions || []).slice(0, 5);
    ctx.fillStyle = INK_SECONDARY;
    ctx.font = `400 ${10 / k}px JetBrains Mono, monospace`;
    fns.forEach((fn, i) => {
      ctx.fillText(
        `ƒ ${fn.name}`,
        x + NODE_PADDING,
        y + NODE_HEIGHT_BASE + i * NODE_LINE_HEIGHT
      );
    });

    // Import count di bawah
    const importCount = (n.imports || []).length;
    if (importCount > 0) {
      ctx.fillStyle = INK_MUTED;
      ctx.fillText(
        `↳ ${importCount} import${importCount > 1 ? 's' : ''}`,
        x + NODE_PADDING,
        y + h - 6
      );
    }
  }

  ctx.globalAlpha = 1.0;
}

// Helper: rounded rectangle path
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}
```

### 6.2 Edge rendering — bezier curves dengan panah

```javascript
const EDGE_COLORS = {
  imports:       "oklch(52% 0.15 145)",  // hijau
  circular:      "oklch(58% 0.22 25)",   // merah
  function_call: "oklch(55% 0.18 280)",  // biru/ungu
};

function drawEdge(edge, sourceNode, targetNode) {
  if (!sourceNode || !targetNode) return;

  const color = edge.type === "circular"
    ? EDGE_COLORS.circular
    : edge.type === "function_call"
      ? EDGE_COLORS.function_call
      : EDGE_COLORS.imports;

  // Control points untuk bezier — curve ke bawah/atas
  const dx = targetNode.x - sourceNode.x;
  const dy = targetNode.y - sourceNode.y;
  const cx1 = sourceNode.x + dx * 0.4;
  const cy1 = sourceNode.y;
  const cx2 = sourceNode.x + dx * 0.6;
  const cy2 = targetNode.y;

  ctx.beginPath();
  ctx.moveTo(sourceNode.x, sourceNode.y);
  ctx.bezierCurveTo(cx1, cy1, cx2, cy2, targetNode.x, targetNode.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = (edge.weight || 1) * 1.5 / transform.k;

  // Circular: dashed line
  if (edge.type === "circular") {
    ctx.setLineDash([6 / transform.k, 3 / transform.k]);
  }

  ctx.stroke();
  ctx.setLineDash([]);

  // Panah di ujung — di BORDER rectangle target, bukan center (center ketutup node)
  const tw = nodeWidth(targetNode), th = nodeHeight(targetNode, transform.k);
  const { x: ax, y: ay } = rectBorderIntersection(targetNode.x, targetNode.y, tw, th, dx, dy);
  drawArrow(ax, ay, dx, dy, color);

  // Warning label untuk circular
  if (edge.type === "circular") {
    const midX = (sourceNode.x + targetNode.x) / 2;
    const midY = (sourceNode.y + targetNode.y) / 2 - 10 / transform.k;
    ctx.fillStyle = EDGE_COLORS.circular;
    ctx.font = `500 ${10 / transform.k}px Sora, sans-serif`;
    ctx.fillText("⚠ circular", midX, midY);
  }
}

// Helper: titik perpotongan garis (cx,cy)→(cx+dx,cy+dy) dengan border rectangle
// (cx,cy center, w×h size). Return titik di tepi rectangle tempat arrow ditaruh.
function rectBorderIntersection(cx, cy, w, h, dx, dy) {
  const hw = w / 2, hh = h / 2;
  const scale = Math.min(hw / Math.abs(dx || 1e-9), hh / Math.abs(dy || 1e-9));
  return { x: cx + dx * scale, y: cy + dy * scale };
}

function drawArrow(tx, ty, dx, dy, color) {
  const angle = Math.atan2(dy, dx);
  const size = 8 / transform.k;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(tx, ty);
  ctx.lineTo(
    tx - size * Math.cos(angle - Math.PI / 6),
    ty - size * Math.sin(angle - Math.PI / 6)
  );
  ctx.lineTo(
    tx - size * Math.cos(angle + Math.PI / 6),
    ty - size * Math.sin(angle + Math.PI / 6)
  );
  ctx.closePath();
  ctx.fill();
}
```

**Edge legend (tooltip, bukan kotak permanent):** saat mouse hover di atas edge, tampilkan tooltip teks `"import"` / `"function call"` / `"circular"`. Reuse pola `showTooltip` node; tambah `edgeAt()` brute-force O(edges) per mousemove (OK <500 edges; quadtree edge index kalau perlu).

---

### 6.3 Hit detection update — rectangle bukan circle

```javascript
function nodeAt(clientX, clientY) {
  if (!quadtree) return null;
  const rect = canvas.getBoundingClientRect();
  const sx = clientX - rect.left;
  const sy = clientY - rect.top;
  const wx = (sx - transform.x) / transform.k;
  const wy = (sy - transform.y) / transform.k;

  // Cari kandidat via quadtree (radius besar untuk initial filter)
  const found = quadtree.find(wx, wy, 100);
  if (!found) return null;

  // Rectangle hit test
  const w = nodeWidth(found);
  const h = nodeHeight(found, transform.k);
  const nx = found.x - w / 2;
  const ny = found.y - h / 2;

  return (wx >= nx && wx <= nx + w && wy >= ny && wy <= ny + h) ? found : null;
}
```

---

## 7. panel.js — Popover + Side Panel

### 7.1 Popover

Popover di-render sebagai absolutely positioned div di atas canvas. Tidak di Canvas — ini DOM element biasa sehingga bisa ada teks selectable, link clickable, dan icon `>`.

```javascript
// Trigger: klik node (selectedNode berubah). Pakai addEventListener pola yang
// sudah ada di codebase (store.onChange belum exist — lihat filter.js).
store.addEventListener('change', (e) => {
  if (!e.detail.keys.includes('selectedNode')) return;
  const node = store.state.selectedNode;
  if (!node) {
    hidePopover();
    return;
  }
  showPopover(node);
});

function showPopover(node) {
  const el = document.getElementById('node-popover');

  // Position: di sebelah kanan node, atau kiri kalau terlalu dekat tepi
  const { screenX, screenY } = nodeToScreen(node);
  positionPopover(el, screenX, screenY);

  // Content
  const fns = (node.functions || []);
  const imports = (node.imports || []);
  const usedBy = findUsedBy(node, store.state.graph);

  el.innerHTML = `
    <div class="popover-header">
      <span class="popover-filename">${node.id}</span>
      <button class="popover-expand" title="Buka detail">›</button>
    </div>
    <div class="popover-section">
      <div class="popover-label">Fungsi (${fns.length})</div>
      ${fns.slice(0, 5).map(f => `
        <div class="popover-fn">${f.is_dead_code ? '⚫' : 'ƒ'} ${f.name}</div>
      `).join('')}
      ${fns.length > 5 ? `<div class="popover-more">+${fns.length - 5} lagi</div>` : ''}
    </div>
    <div class="popover-section">
      <div class="popover-label">Import (${imports.length})</div>
      ${imports.slice(0, 3).map(i => `
        <div class="popover-import">↳ ${i.from || i.resolved_path || '?'}</div>
      `).join('')}
      ${imports.length > 3 ? `<div class="popover-more">+${imports.length - 3} lagi</div>` : ''}
    </div>
    ${usedBy.length > 0 ? `
    <div class="popover-section">
      <div class="popover-label">Dipakai oleh</div>
      ${usedBy.slice(0, 3).map(f => `
        <div class="popover-used">${f}</div>
      `).join('')}
    </div>` : ''}
    ${node.supported === false ? `
    <div class="popover-ghost-hint">
      📁 ${getDirectory(node.id)} — klik untuk buka direktori
    </div>` : ''}
  `;

  // Ghost node: klik seluruh popover = expand directory
  if (node.supported === false) {
    el.addEventListener('click', () => expandDirectory(getDirectory(node.id)));
  }

  // Expand icon: buka side panel
  el.querySelector('.popover-expand')?.addEventListener('click', (e) => {
    e.stopPropagation();
    setState({ sidePanel: true });
    showSidePanel(node);
  });

  el.classList.remove('hidden');
}

function hidePopover() {
  document.getElementById('node-popover').classList.add('hidden');
}

// Helper: world coord node → screen coord (inverse transform)
function nodeToScreen(node) {
  const rect = canvas.getBoundingClientRect();
  return {
    screenX: rect.left + node.x * transform.k + transform.x,
    screenY: rect.top + node.y * transform.k + transform.y,
  };
}

// Helper: posisi popover kanan node, flip ke kiri kalau nabrak tepi kanan viewport
function positionPopover(el, x, y) {
  el.style.left = (x + 12) + 'px';
  el.style.top = y + 'px';
  requestAnimationFrame(() => {
    const w = el.offsetWidth;
    if (x + 12 + w > window.innerWidth) {
      el.style.left = (x - 12 - w) + 'px';
    }
  });
}

// Helper: cari file yang import node ini
function findUsedBy(node, graph) {
  return (graph.edges || [])
    .filter(e => e.target === node.id)
    .map(e => e.source)
    .slice(0, 5);
}
```

### 7.2 Side Panel

```javascript
function showSidePanel(node) {
  const panel = document.getElementById('side-panel');
  panel.innerHTML = `
    <div class="panel-header">
      <span class="panel-filename">${node.id}</span>
      <button class="panel-close">✕</button>
    </div>

    <div class="panel-section">
      <div class="panel-label">Fungsi & Import</div>
      <select class="panel-combobox" id="fn-select">
        <option value="">Pilih fungsi atau import...</option>
        <optgroup label="Fungsi">
          ${(node.functions || []).map(f => `
            <option value="fn:${f.name}">${f.name}</option>
          `).join('')}
        </optgroup>
        <optgroup label="Import">
          ${(node.imports || []).map(i => `
            <option value="im:${i.from}">${i.from || i.resolved_path}</option>
          `).join('')}
        </optgroup>
      </select>

      <!-- Source code viewer: muncul saat fungsi dipilih -->
      <div id="source-viewer" class="hidden">
        <pre><code class="language-python" id="source-code"></code></pre>
      </div>
    </div>

    <div class="panel-section panel-ai">
      <div class="panel-label">AI Chat</div>
      <div id="panel-ai-hint">
        Context aktif: <span class="panel-tag">@${node.id}</span>
        <button id="open-ai-bar">Buka AI chat ↓</button>
      </div>
    </div>
  `;

  // Combobox handler
  document.getElementById('fn-select')?.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val.startsWith('fn:')) {
      const fnName = val.slice(3);
      loadSourceCode(node.id, fnName);
    }
  });

  // Close handler
  panel.querySelector('.panel-close')?.addEventListener('click', () => {
    panel.classList.remove('open');
    setState({ sidePanel: false });
  });

  // "Buka AI chat" — inject @tag ke AI bar
  document.getElementById('open-ai-bar')?.addEventListener('click', () => {
    injectAITag(node.id);
    scrollToAIBar();
  });

  panel.classList.add('open');
}
```

---

## 8. Directory Sidebar (sidebar.js — file baru)

```javascript
// graps/frontend/sidebar.js

(function () {
  'use strict';
  window.graps = window.graps || {};
  const store = window.graps.store;
  const setState = window.graps.setState;

  let sidebarEl;

  function init() {
    sidebarEl = document.getElementById('dir-sidebar');
    store.addEventListener('change', (e) => {
      if (e.detail.keys.includes('graph') || e.detail.keys.includes('openDirs')) {
        renderSidebar();
      }
    });
  }

  function renderSidebar() {
    const graph = store.state.graph;
    if (!graph || !graph.nodes) {
      sidebarEl.innerHTML = '<div class="sidebar-empty">Scan project untuk mulai</div>';
      return;
    }

    // Build directory tree dari node paths
    const tree = buildDirTree(graph.nodes);
    sidebarEl.innerHTML = renderTree(tree);

    // Attach click handlers
    sidebarEl.querySelectorAll('.dir-item').forEach(el => {
      el.addEventListener('click', () => {
        const dir = el.dataset.dir;
        toggleDirectory(dir);
      });
    });
  }

  function buildDirTree(nodes) {
    const dirs = new Set();
    nodes.forEach(n => {
      const parts = n.id.split('/');
      // Collect semua parent directories
      for (let i = 1; i < parts.length; i++) {
        dirs.add(parts.slice(0, i).join('/'));
      }
    });
    return Array.from(dirs).sort();
  }

  function renderTree(dirs) {
    const openDirs = store.state.openDirs || new Set();
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    return dirs.map(dir => {
      const parts = dir.split('/');
      const depth = parts.length - 1;
      // Mobile strip horizontal: indent hilang → render zsh-style, 2 segmen terakhir
      // (graps/graps/ai → "graps/ai"). Preserve depth context tanpa komponen baru.
      const name = isMobile
        ? parts.slice(-2).join('/') + '/'
        : parts[parts.length - 1] + '/';
      const isOpen = openDirs.has(dir);
      return `
        <div class="dir-item depth-${depth}" data-dir="${dir}">
          <span class="dir-icon">${isOpen ? '▾' : '▸'}</span>
          <span class="dir-name">${name}</span>
        </div>
      `;
    }).join('');
  }

  function toggleDirectory(dir) {
    const current = store.state.openDirs || new Set();
    const next = new Set(current);
    if (next.has(dir)) {
      next.delete(dir);
    } else {
      next.add(dir);
    }
    setState({ openDirs: next });
    updateGraphVisibility();
  }

  function updateGraphVisibility() {
    // Notify graph.js untuk filter visible nodes
    // berdasarkan openDirs
    const event = new CustomEvent('graps:dirs-changed');
    document.dispatchEvent(event);
  }

  window.graps.sidebar = { init, expandDirectory: (dir) => {
    const current = store.state.openDirs || new Set();
    const next = new Set(current);
    next.add(dir);
    setState({ openDirs: next });
    updateGraphVisibility();
  }};

  document.addEventListener('DOMContentLoaded', init);
})();
```

---

## 9. AI Bar (ai.js — file baru)

```javascript
// graps/frontend/ai.js — persistent bottom AI chat

(function() {
  'use strict';
  window.graps = window.graps || {};
  const store = window.graps.store;
  const setState = window.graps.setState;

  let inputEl, messagesEl, tagsEl;

  function init() {
    inputEl = document.getElementById('ai-input');
    messagesEl = document.getElementById('ai-messages');
    tagsEl = document.getElementById('ai-tags');

    document.getElementById('ai-send')?.addEventListener('click', sendMessage);
    inputEl?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-inject selectedNode sebagai implicit context
    store.addEventListener('change', (e) => {
      if (!e.detail.keys.includes('selectedNode')) return;
      const node = store.state.selectedNode;
      if (node) {
        setImplicitTag(node.id);
      }
    });

    // /new command handler
    inputEl?.addEventListener('input', (e) => {
      if (e.target.value.trim() === '/new') {
        e.target.value = '';
        clearConversation();
      }
    });
  }

  function setImplicitTag(nodeId) {
    // Update placeholder — bukan hard inject ke input
    // User bisa override dengan @tag manual
    if (inputEl) {
      inputEl.placeholder = `Tanya tentang @${nodeId}...`;
    }
    renderTags([nodeId]);
  }

  function renderTags(tags) {
    if (!tagsEl) return;
    tagsEl.innerHTML = tags.map(t => `
      <span class="ai-tag">@${t}</span>
    `).join('');
  }

  async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message || message.startsWith('/')) return;

    const selectedNode = store.state.selectedNode;
    const tagged = selectedNode ? [selectedNode.id] : [];

    // Extract manual @tags dari message
    const manualTags = (message.match(/@[\w./]+/g) || [])
      .map(t => t.slice(1));
    const allTagged = [...new Set([...tagged, ...manualTags])];

    appendMessage('user', message);
    inputEl.value = '';

    const history = store.state.aiHistory || [];

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          tagged: allTagged,
          history,
        }),
      });

      const data = await res.json();

      if (data.error_type) {
        appendMessage('error', data.detail || 'AI error');
        return;
      }

      appendMessage('assistant', data.reply);

      // Update history untuk next turn
      setState({
        aiHistory: [
          ...history,
          { role: 'user', content: message },
          { role: 'assistant', content: data.reply },
        ]
      });

      // Show warnings kalau ada
      if (data.warnings && data.warnings.length > 0) {
        data.warnings.forEach(w => {
          window.graps.toast?.show(w, 'warning');
        });
      }

    } catch (err) {
      appendMessage('error', 'Tidak bisa reach server');
    }
  }

  function appendMessage(role, content) {
    if (!messagesEl) return;
    const el = document.createElement('div');
    el.className = `ai-message ai-${role}`;
    el.textContent = content;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function clearConversation() {
    setState({ aiHistory: [] });
    if (messagesEl) messagesEl.innerHTML = '';
    window.graps.toast?.show('Sesi baru dimulai', 'info');
  }

  // Public: inject tag dari side panel
  function injectTag(nodeId) {
    if (inputEl) {
      const current = inputEl.value;
      if (!current.includes(`@${nodeId}`)) {
        inputEl.value = current + ` @${nodeId}`;
      }
      inputEl.focus();
    }
  }

  window.graps.ai = { init, injectTag };
  document.addEventListener('DOMContentLoaded', init);
})();
```

---

## 10. GET /api/source — Endpoint Baru (TERAKHIR)

**Implement ini SETELAH semua UI selesai dan verified.**

```python
# graps/server/app.py — tambahkan setelah endpoint yang ada

@app.get("/api/source")
async def get_source(
    file: str,
    fn: str | None = None,
):
    """
    Return source code untuk file atau function tertentu.
    
    Query params:
      file: relative path dari scan root (e.g. "services/user_service.py")
      fn:   nama function (optional) — kalau ada, return hanya function body
            kalau tidak ada, return seluruh file
    
    Security:
      - Path traversal prevention: file harus dalam scan_root
      - Tidak ada absolute path yang di-expose
    """
    if scan_root is None:
        return JSONResponse({"error": "scan_root not set"}, status_code=500)

    # Security: prevent path traversal
    try:
        target = (scan_root / file).resolve()
        target.relative_to(scan_root.resolve())  # raises ValueError kalau escape
    except ValueError:
        return JSONResponse({"error": "Invalid path"}, status_code=400)

    if not target.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    try:
        source = target.read_text(errors="replace")
    except OSError as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    if fn:
        # Extract function body — pakai ast untuk Python, line range untuk lainnya
        extracted = extract_function(source, fn, target.suffix)
        if extracted is None:
            return JSONResponse({"error": f"Function '{fn}' not found"}, status_code=404)
        return {"file": file, "fn": fn, "source": extracted, "language": get_language(target.suffix)}

    return {"file": file, "fn": None, "source": source, "language": get_language(target.suffix)}
```

Frontend load source dan render via Prism.js:

```javascript
// panel.js — dipanggil saat combobox pilih fungsi
async function loadSourceCode(fileId, fnName) {
  const viewer = document.getElementById('source-viewer');
  const codeEl = document.getElementById('source-code');

  viewer.classList.remove('hidden');
  codeEl.textContent = 'Loading...';

  try {
    const res = await fetch(`/api/source?file=${encodeURIComponent(fileId)}&fn=${encodeURIComponent(fnName)}`);
    const data = await res.json();

    if (data.error) {
      codeEl.textContent = `Error: ${data.error}`;
      return;
    }

    codeEl.textContent = data.source;
    codeEl.className = `language-${data.language}`;
    Prism.highlightElement(codeEl);

  } catch (err) {
    codeEl.textContent = 'Gagal load source code';
  }
}
```

Prism.js di-include via CDN di index.html:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-typescript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-go.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-rust.min.js"></script>
```

---

## 11. Checklist Implementasi (Urutan Dependency)

```
[ ] 1. Fix string language mismatch di cli.py (test_cache minor fix)
[ ] 2. index.html — layout baru (sidebar + graph-wrap + side-panel + ai-bar)
[ ] 3. style.css — responsive breakpoints, CSS vars baru, komponen baru
[ ] 4. graph.js — rectangle nodes (roundRect, drawNode rewrite)
[ ] 5. graph.js — bezier edges dengan panah (drawEdge rewrite)
[ ] 6. graph.js — hit detection update untuk rectangle
[ ] 7. graph.js — ghost node rendering (dashed border, opacity 50%)
[ ] 8. graph.js — filter visible nodes berdasarkan openDirs
[ ] 9. panel.js — popover (showPopover, hidePopover, findUsedBy)
[ ] 10. panel.js — side panel (showSidePanel, combobox handler)
[ ] 11. sidebar.js — file baru (directory tree, toggle, ghost node expand)
[ ] 12. ai.js — file baru (AI chat bar, /new command, implicit context)
[ ] 13. Verify: klik node → popover muncul → klik > → side panel
[ ] 14. Verify: directory sidebar toggle → ghost nodes muncul → klik ghost → expand
[ ] 15. Verify: AI bar implicit context dari selectedNode
[ ] 16. Verify: responsive di mobile (popover, bottom sheet, AI collapsed)
[ ] 17. GET /api/source endpoint (TERAKHIR)
[ ] 18. Prism.js integration di panel.js (TERAKHIR, setelah endpoint ada)
[ ] 19. Full test suite verify — 91 pass minimum, zero regresi
```

---

## 12. Yang TIDAK Termasuk Spec Ini

```
✗ Combobox source code viewer detail — sudah di-spec di step 17-18, implement terakhir
✗ Edit file langsung / edit by AI — future feature, tidak dibahas
✗ Monorepo lazy loading — post-MVP
✗ Session ID management — /new command sudah cukup
✗ Export graph sebagai image — backlog
✗ Dark/light mode toggle — default dark, tidak ada toggle
```

---

*PHASE5_FRONTEND_SPEC.md — reference BLUEPRINT.md dan PHASE5.md*
*Dibuat: 2026-07-03*

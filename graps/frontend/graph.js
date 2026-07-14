/* graps — Canvas2D graph renderer.
 *
 * Public API: window.graps.graph
 *   .panTo(node)  — center viewport ke node
 *   .fit()        — fit-to-viewport
 *
 * CHANGES v3:
 *   - Layout: directory-depth columns (X = depth ONLY, Y = sibling order).
 *     Edges are visual-only curves; force sim re-enabled for collision only.
 *   - Zoom: fix pinch-to-zoom di mobile (touch events manual)
 *   - Visual: card-style node (header / imports / functions / label section)
 *   - Semua state, API, interactions, backend, events TIDAK BERUBAH
 */
(function () {
  "use strict";
  window.graps = window.graps || {};
  const store = window.graps.store;
  const setState = window.graps.setState;
  const toast = window.graps.toast;

  let canvas, ctx, wrap;
  let width = 0, height = 0, dpr = 1;
  let nodes = [], edges = [];
  let visibleNodesCache = []; // subset of `nodes` yang sedang visible (lazy-render)
  let quadtree = null;
  let transform = { x: 0, y: 0, k: 1 };
  let zoomBehavior = null;

  // ── DESIGN TOKENS ────────────────────────────────────────────────────────
  const RING = {
    clean:  "oklch(52% 0.02 250)",
    yellow: "oklch(76% 0.15 75)",
    red:    "oklch(58% 0.22 25)",
  };
  const RING_WIDTH = { clean: 1.5, yellow: 2, red: 2.5 };

  const NODE_BG            = "oklch(18% 0.008 75)";
  const NODE_BG_UNSUPPORT  = "oklch(14% 0.005 75)";
  const NODE_HEADER_BG     = "oklch(22% 0.010 75)";
  const NODE_HEADER_BG_DIR = "oklch(20% 0.04 250)";
  const NODE_SECTION_DIV   = "oklch(26% 0.008 75)";
  const NODE_BORDER        = "oklch(30% 0.012 75)";

  const INK_PRIMARY   = "oklch(94% 0.006 75)";
  const INK_SECONDARY = "oklch(65% 0.008 75)";
  const INK_MUTED     = "oklch(42% 0.006 75)";

  const CONNECTOR_COLOR = "oklch(55% 0.12 250)";

  const EDGE_COLORS = {
    imports:       "oklch(94.38% 0 70.27)",
    circular:      "oklch(58% 0.22 25)",
    function_call: "oklch(55% 0.18 280)",
  };

  // ── NODE SIZING ───────────────────────────────────────────────────────────
  const NODE_W          = 210;
  const NODE_HEADER_H   = 34;
  const NODE_SECTION_PAD= 8;
  const NODE_LABEL_H    = 13;
  const NODE_CONTENT_H  = 15;
  const NODE_FN_MAX     = 4;
  const NODE_SECTION_GAP= 1;
  const NODE_RADIUS     = 8;
  const NODE_PADDING_X  = 12;
  const CONNECTOR_R     = 4;

  // Tree layout spacing
  const TREE_COL_GAP    = 80;   // horizontal gap between columns
  const TREE_ROW_GAP    = 28;   // vertical gap between cards in same column

  // ponytail: depth = path-segment count - 1 (same formula as sidebar.js
  // buildDirTree — "the function that knows the depth, written before").
  // Drives X column for BOTH dirs and files: a file's depth equals its parent
  // dir depth + 1, so files land one column right of their parent folder.
  function dirDepth(id) { return id.split("/").length - 1; }
  window.graps.dirDepth = dirDepth;

  // ponytail: lazy-render visibility gate. depth-0 selalu visible; node lebih
  // dalam cuma visible kalau DIRECT PARENT-nya di-expand. Bukan "any ancestor"
  // — kalau any ancestor, expand src langsung render seluruh subtree (cascade
  // visual), kontradiksi §2 "cuma buka level ini". Exact parent string match
  // juga sekalian solve §6 #1 (src2/x.py nggak ke-match openDir src).
  function isNodeVisible(node, openDirsSet) {
    const depth = dirDepth(node.id);
    if (depth === 0) return true;
    const parts = node.id.split("/");
    const parent = parts.slice(0, parts.length - 1).join("/");
    return openDirsSet.has(parent);
  }

  // X for a given depth — fixed column grid (architectural blueprint, rule 1/2).
  function colX(depth) { return 40 + NODE_W / 2 + depth * (NODE_W + TREE_COL_GAP); }

  function nodeWidth() { return NODE_W; }

  function nodeHeight(n, zoomK) {
    const k = zoomK || 1;
    if (k < 0.45) return NODE_HEADER_H + 8;
    if (k < 0.75) {
      return NODE_HEADER_H + NODE_SECTION_GAP +
             NODE_SECTION_PAD * 2 + NODE_LABEL_H + NODE_CONTENT_H;
    }
    const fnCount = Math.min((n.functions || []).length, NODE_FN_MAX);
    const importSec = NODE_SECTION_PAD * 2 + NODE_LABEL_H + NODE_CONTENT_H;
    const fnSec     = NODE_SECTION_PAD * 2 + NODE_LABEL_H + Math.max(1, fnCount) * NODE_CONTENT_H;
    const labelSec  = NODE_SECTION_PAD * 2 + NODE_CONTENT_H;
    return NODE_HEADER_H + NODE_SECTION_GAP + importSec +
           NODE_SECTION_GAP + fnSec + NODE_SECTION_GAP + labelSec;
  }

  function clipText(text, maxWidth) {
    if (!text) return "";
    if (ctx.measureText(text).width <= maxWidth) return text;
    const ell = "…";
    if (ctx.measureText(ell).width >= maxWidth) return ell;
    let i = text.length;
    while (i > 0 && ctx.measureText(text.slice(0, i) + ell).width > maxWidth) i--;
    return i > 0 ? text.slice(0, i) + ell : ell;
  }

  // ── TREE LAYOUT (directory hierarchy, NOT import graph) ───────────────────
  // Rules: X = directory depth ONLY (rule 1). Same depth → same X (rule 2).
  // Y = sibling order inside the dir tree (rule 3). Edges never move nodes
  // (rule 4). No force determines hierarchy (rule 5). Parent-child stays
  // hierarchical via columns (rule 6). Empty space > overlap (rule 9).
  function visibleNodeList() {
    const openDirsSet = store.state.graphOpenDirs || new Set();
    return nodes.filter(n => isNodeVisible(n, openDirsSet));
  }

  function computeTreeLayout(nodeList) {
    if (!nodeList.length) return;
    const byDepth = new Map();
    nodeList.forEach(n => {
      const d = dirDepth(n.id);
      if (!byDepth.has(d)) byDepth.set(d, []);
      byDepth.get(d).push(n);
    });
    [...byDepth.keys()].sort((a, b) => a - b).forEach(d => {
      // sibling order: folder DULU, baru file — lexicographic dalam tiap grup
      // (requirement eksplisit plan §5.3: "folder dulu baru file")
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
        n.x = colX(d);       // X fixed by depth (rule 1)
        n.y = y + h / 2;     // Y by sibling stack (rule 3)
        y += h + TREE_ROW_GAP;
      });
    });
  }

  // Synthesize directory nodes so the filesystem hierarchy is visible.
  // Backend only emits file nodes; dirs derived from id prefixes — same
  // algorithm as sidebar.js buildDirTree. Renderer already handles isDir.
  function synthesizeDirNodes() {
    const dirIds = new Set();
    nodes.forEach(n => {
      const parts = n.id.split("/");
      for (let i = 1; i < parts.length; i++) dirIds.add(parts.slice(0, i).join("/"));
    });
    const have = new Set(nodes.map(n => n.id));
    const dirNodes = Array.from(dirIds).filter(d => !have.has(d)).map(d => ({
      id: d, type: "directory", is_directory: true, path: d,
      functions: [], imports: [], classes: [], constants: [],
      supported: true, risk_level: "clean", risk_summary: null,
    }));
    nodes = nodes.concat(dirNodes);
  }

  // ponytail: lazy-render orchestrator. Dipanggil tiap kali visibility
  // (graphOpenDirs) berubah. Silent-failure guard §6 #7: kalau lupa panggil ini
  // setelah setState graphOpenDirs, canvas nggak update — wajib di tiap toggle.
  function relayout() {
    visibleNodesCache = visibleNodeList();
    computeTreeLayout(visibleNodesCache);
    buildQuadtree();
    draw();
  }

  // ── QUADTREE (rebuilt per relayout, atas visible subset only) ───────────────
  function buildQuadtree() {
    quadtree = d3.quadtree()
      .x(d => d.x)
      .y(d => d.y)
      .addAll(visibleNodesCache);
  }

  // ── FOLDER TOGGLE (canvas expand/collapse, independen dari sidebar) ────────
  // ponytail: collapse reset folder + SEMUA descendant (no memory, §5.9).
  // Auto-deselect kalau selectedNode jadi hidden karena ancestor collapse (§6 #5).
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

  // §5.10: expand semua ancestor folder node target — dipakai search & pan-to
  // ke node yang sedang hidden. Set.add idempotent, aman walau sebagian sudah expand.
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


  // ── HIT DETECTION ────────────────────────────────────────────────────────
  function nodeAt(clientX, clientY) {
    if (!quadtree) return null;
    const rect = canvas.getBoundingClientRect();
    const sx = clientX - rect.left;
    const sy = clientY - rect.top;
    const wx = (sx - transform.x) / transform.k;
    const wy = (sy - transform.y) / transform.k;
    const found = quadtree.find(wx, wy, 200);
    if (!found) return null;
    const w = nodeWidth(found);
    const h = nodeHeight(found, transform.k);
    const nx = found.x - w / 2;
    const ny = found.y - h / 2;
    return (wx >= nx && wx <= nx + w && wy >= ny && wy <= ny + h) ? found : null;
  }

  // ── SHARED NODE INTERACTION ───────────────────────────────────────────────
  // ponytail: dipakai "click" (mouse) DAN tap-detection (touch). Di touch device,
  // touchstart manggil preventDefault() buat nyegah native scroll pas pan/pinch —
  // efek samping: synthesized "click" gak di-fire, jadi node interaction (toggleFolder
  // / selectNode) yang cuma listen "click" gak pernah kepanggil di Mises. Solusi:
  // tap di-handle eksplisit di touchend lewat sini, bukan lewat click.
  function handleNodeInteraction(clientX, clientY) {
    const n = nodeAt(clientX, clientY);
    if (!n) return;
    const isDir = n.is_directory || n.type === "directory";
    if (isDir) { toggleFolder(n.id); return; }
    if (n.supported !== false) {
      // Edge visibility: draw() skips edges whose endpoint is hidden. Expanding
      // the ancestor folders of a node's edge-neighbors makes those neighbors
      // visible so the import edges/arrows render when the node is selected.
      expandForSelection(n);
      setState({ selectedNode: n });
    }
  }

  // ponytail: select a node → expand ancestor folders of itself + every edge
  // neighbor (source or target) so the import edges render. lazy-render §7 #9
  // keeps edge-draw gated on visible endpoints; this makes them visible.
  // Collects all ancestor ids first, one setState + one relayout (no N redraws).
  function expandForSelection(node) {
    if (!node) return;
    const current = store.state.graphOpenDirs || new Set();
    const next = new Set(current);
    const ids = new Set([node.id]);
    for (const e of edges) {
      const s = typeof e.source === "object" ? e.source && e.source.id : e.source;
      const t = typeof e.target === "object" ? e.target && e.target.id : e.target;
      if (s === node.id && t) ids.add(t);
      else if (t === node.id && s) ids.add(s);
    }
    let changed = false;
    ids.forEach(id => {
      if (!id) return;
      const parts = id.split("/");
      for (let i = 1; i < parts.length; i++) {
        const ancestor = parts.slice(0, i).join("/");
        if (!next.has(ancestor)) { next.add(ancestor); changed = true; }
      }
    });
    if (changed) {
      setState({ graphOpenDirs: next });
      relayout();
    }
  }

  // ── DRAW HELPERS ──────────────────────────────────────────────────────────
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

  function roundRectTop(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h);
    ctx.lineTo(x, y + h);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function roundRectBottom(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y);
    ctx.closePath();
  }

  function rectBorderIntersection(cx, cy, w, h, dx, dy) {
    const hw = w / 2, hh = h / 2;
    const scale = Math.min(hw / Math.abs(dx || 1e-9), hh / Math.abs(dy || 1e-9));
    return { x: cx + dx * scale, y: cy + dy * scale };
  }

  function drawArrow(tx, ty, dx, dy, color, k) {
    const angle = Math.atan2(dy, dx);
    const size = 7 / k;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(tx, ty);
    ctx.lineTo(tx - size * Math.cos(angle - Math.PI / 6), ty - size * Math.sin(angle - Math.PI / 6));
    ctx.lineTo(tx - size * Math.cos(angle + Math.PI / 6), ty - size * Math.sin(angle + Math.PI / 6));
    ctx.closePath();
    ctx.fill();
  }

  function drawConnectorDots(x, y, w, h, k) {
    const cy = y + h / 2;
    ctx.fillStyle = CONNECTOR_COLOR;
    ctx.strokeStyle = NODE_BG;
    ctx.lineWidth = 1.5 / k;
    ctx.beginPath(); ctx.arc(x, cy, CONNECTOR_R / k, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(x + w, cy, CONNECTOR_R / k, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }

  // ── NODE CARD RENDERER ────────────────────────────────────────────────────
  function nodeRisk(n) { return n.risk_level || "clean"; }

  function isDimmed(node) {
    const f = store.state.filter;
    const hov = store.state.hoveredNode;
    const sel = store.state.selectedNode;
    if (f.risk === "high" && nodeRisk(node) !== "red") return true;
    if (f.dead) {
      const fns = node.functions || [];
      if (fns.length === 0) return false;
      if (!fns.every(fn => fn.is_dead_code)) return true;
    }
    const focus = sel || hov;
    if (focus && focus !== node) {
      const neigh = focus._neighbors;
      if (neigh && !neigh.has(node.id)) return true;
    }
    return false;
  }

  function drawNode(n, focus, k) {
    const w = nodeWidth(n);
    const h = nodeHeight(n, k);
    const x = n.x - w / 2;
    const y = n.y - h / 2;
    const risk       = nodeRisk(n);
    const ring       = RING[risk] || RING.clean;
    const rw         = RING_WIDTH[risk] || 1.5;
    const unsupported = n.supported === false;
    const isDir      = n.is_directory || n.type === "directory";
    const selected   = focus && n === focus;
    const dim        = isDimmed(n);

    let opacity = 0.85;
    if (dim)         opacity = 0.08;
    else if (unsupported) opacity = 0.45;
    else if (selected)    opacity = 1.0;
    else if (focus)       opacity = 0.75;
    ctx.globalAlpha = opacity;

    // ── Card body
    ctx.fillStyle = unsupported ? NODE_BG_UNSUPPORT : NODE_BG;
    roundRect(ctx, x, y, w, h, NODE_RADIUS);
    ctx.fill();

    // ── Card border
    const borderColor = risk !== "clean" ? ring : NODE_BORDER;
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = rw / k;
    if (unsupported) ctx.setLineDash([4 / k, 4 / k]);
    roundRect(ctx, x, y, w, h, NODE_RADIUS);
    ctx.stroke();
    ctx.setLineDash([]);

    // ── Selected glow
    if (selected && !dim) {
      ctx.shadowColor = ring; ctx.shadowBlur = 10 / k;
      roundRect(ctx, x, y, w, h, NODE_RADIUS); ctx.stroke();
      ctx.shadowBlur = 0;
    }
    // ── Red glow
    if (risk === "red" && !dim && !selected) {
      ctx.shadowColor = RING.red; ctx.shadowBlur = 14 / k;
      roundRect(ctx, x, y, w, h, NODE_RADIUS);
      ctx.strokeStyle = ring; ctx.lineWidth = rw / k; ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // LOD: silhouette only
    if (k < 0.45) { drawConnectorDots(x, y, w, h, k); return; }

    // ── HEADER ────────────────────────────────────────────────────────────
    ctx.fillStyle = isDir ? NODE_HEADER_BG_DIR : NODE_HEADER_BG;
    roundRectTop(ctx, x, y, w, NODE_HEADER_H, NODE_RADIUS);
    ctx.fill();

    // Header divider
    ctx.strokeStyle = NODE_SECTION_DIV;
    ctx.lineWidth = 1 / k;
    ctx.beginPath();
    ctx.moveTo(x, y + NODE_HEADER_H);
    ctx.lineTo(x + w, y + NODE_HEADER_H);
    ctx.stroke();

    // Icon dot
    const iconX = x + NODE_PADDING_X + 5;
    const iconY = y + NODE_HEADER_H / 2;
    ctx.fillStyle = isDir ? "oklch(62% 0.14 250)" : INK_MUTED;
    ctx.beginPath();
    ctx.arc(iconX, iconY, 4 / k < 4 ? 4 : 4, 0, Math.PI * 2);
    ctx.fill();

    // Filename
    ctx.fillStyle = INK_PRIMARY;
    ctx.font = "600 11px 'Sora', sans-serif";
    const fname = n.id.split("/").pop() || n.id;
    ctx.fillText(clipText(fname, w - NODE_PADDING_X * 2 - 16), iconX + 10, y + NODE_HEADER_H / 2 + 4);

    // LOD: compact (header + import count)
    if (k < 0.75) {
      const secY = y + NODE_HEADER_H + NODE_SECTION_GAP + NODE_SECTION_PAD;
      const importCount = (n.imports || []).length;
      ctx.fillStyle = INK_MUTED;
      ctx.font = "400 9px 'JetBrains Mono', monospace";
      ctx.fillText(
        clipText("↳ " + importCount + " import" + (importCount !== 1 ? "s" : ""), w - NODE_PADDING_X * 2),
        x + NODE_PADDING_X, secY + NODE_LABEL_H
      );
      drawConnectorDots(x, y, w, h, k);
      return;
    }

    // ── FULL CARD ─────────────────────────────────────────────────────────
    let curY = y + NODE_HEADER_H + NODE_SECTION_GAP;

    // — IMPORTS section —
    const importSecH = NODE_SECTION_PAD * 2 + NODE_LABEL_H + NODE_CONTENT_H;
    ctx.fillStyle = INK_MUTED;
    ctx.font = "700 8px 'Sora', sans-serif";
    ctx.fillText("IMPORTS", x + NODE_PADDING_X, curY + NODE_SECTION_PAD + NODE_LABEL_H - 1);

    const imports = n.imports || [];
    const importStr = imports.length > 0
      ? imports.slice(0, 3).map(im =>
          (typeof im === "string" ? im : (im.name || "?")).split("/").pop()
        ).join(", ") + (imports.length > 3 ? " +" + (imports.length - 3) : "")
      : "—";
    ctx.fillStyle = INK_SECONDARY;
    ctx.font = "400 9px 'JetBrains Mono', monospace";
    ctx.fillText(
      clipText(importStr, w - NODE_PADDING_X * 2),
      x + NODE_PADDING_X,
      curY + NODE_SECTION_PAD + NODE_LABEL_H + NODE_CONTENT_H
    );

    curY += importSecH + NODE_SECTION_GAP;
    // divider
    ctx.strokeStyle = NODE_SECTION_DIV; ctx.lineWidth = 1 / k;
    ctx.beginPath(); ctx.moveTo(x, curY); ctx.lineTo(x + w, curY); ctx.stroke();

    // — FUNCTIONS section —
    const fns = (n.functions || []).slice(0, NODE_FN_MAX);
    const fnSecH = NODE_SECTION_PAD * 2 + NODE_LABEL_H + Math.max(1, fns.length) * NODE_CONTENT_H;

    ctx.fillStyle = INK_MUTED;
    ctx.font = "700 8px 'Sora', sans-serif";
    ctx.fillText("FUNCTIONS", x + NODE_PADDING_X, curY + NODE_SECTION_PAD + NODE_LABEL_H - 1);

    if (fns.length === 0) {
      ctx.fillStyle = INK_MUTED;
      ctx.font = "400 9px 'JetBrains Mono', monospace";
      ctx.fillText("—", x + NODE_PADDING_X, curY + NODE_SECTION_PAD + NODE_LABEL_H + NODE_CONTENT_H);
    } else {
      fns.forEach((fn, i) => {
        const dead = fn.is_dead_code;
        ctx.fillStyle = dead ? INK_MUTED : INK_PRIMARY;
        ctx.font = (dead ? "italic 400" : "400") + " 9px 'JetBrains Mono', monospace";
        ctx.fillText(
          clipText((dead ? "ø " : "ƒ ") + fn.name, w - NODE_PADDING_X * 2),
          x + NODE_PADDING_X,
          curY + NODE_SECTION_PAD + NODE_LABEL_H + (i + 1) * NODE_CONTENT_H
        );
      });
      if ((n.functions || []).length > NODE_FN_MAX) {
        ctx.fillStyle = INK_MUTED;
        ctx.font = "400 8px 'Sora', sans-serif";
        ctx.fillText(
          "+" + ((n.functions || []).length - NODE_FN_MAX) + " more",
          x + NODE_PADDING_X,
          curY + NODE_SECTION_PAD + NODE_LABEL_H + (NODE_FN_MAX + 1) * NODE_CONTENT_H
        );
      }
    }

    curY += fnSecH + NODE_SECTION_GAP;
    // divider
    ctx.strokeStyle = NODE_SECTION_DIV; ctx.lineWidth = 1 / k;
    ctx.beginPath(); ctx.moveTo(x, curY); ctx.lineTo(x + w, curY); ctx.stroke();

    // — LABEL / meta section —
    const labelSecH = NODE_SECTION_PAD * 2 + NODE_CONTENT_H;
    ctx.fillStyle = "oklch(16% 0.008 75)";
    roundRectBottom(ctx, x, curY, w, labelSecH, NODE_RADIUS);
    ctx.fill();

    const riskText = n.risk_summary
      ? clipText(n.risk_summary, w - NODE_PADDING_X * 2)
      : (isDir ? "directory" : risk === "red" ? "high risk" : risk === "yellow" ? "warning" : "clean");
    ctx.fillStyle = risk === "red" ? RING.red : risk === "yellow" ? RING.yellow : INK_MUTED;
    ctx.font = "500 8px 'Sora', sans-serif";
    ctx.fillText(riskText, x + NODE_PADDING_X, curY + NODE_SECTION_PAD + NODE_CONTENT_H - 1);

    // Connector dots
    drawConnectorDots(x, y, w, h, k);
  }

  // ── DRAW ──────────────────────────────────────────────────────────────────
  function draw() {
    if (!ctx) return;
    const k = transform.k;
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.translate(transform.x, transform.y);
    ctx.scale(k, k);

    const hov = store.state.hoveredNode;
    const sel = store.state.selectedNode;
    const focus = sel || hov;

    // ── EDGES ─────────────────────────────────────────────────────────────
    const visibleIds = new Set(visibleNodesCache.map(n => n.id));
    for (const e of edges) {
      const s = e.source, t = e.target;
      if (!s || !t || typeof s.x !== "number") continue;
      // lazy-render: skip edge kalau source/target sedang hidden (§5.7)
      if (!visibleIds.has(s.id) || !visibleIds.has(t.id)) continue;

      const edgeType = e.type || "imports";
      const color = edgeType === "circular"
        ? EDGE_COLORS.circular
        : edgeType === "function_call"
          ? EDGE_COLORS.function_call
          : EDGE_COLORS.imports;

      let alpha = 0.18;
      if (focus && (s.id === focus.id || t.id === focus.id)) alpha = 0.80;
      else if (focus) alpha = 0.04;
      ctx.globalAlpha = alpha;

      const dx = t.x - s.x, dy = t.y - s.y;
      // Elbow connector: horizontal then vertical (tree style)
      // ponytail: colX(depth) is discrete (depth*290) → dx is exactly 0 (same-column) or a
      // multiple of 290, never in between. Exact guard, no Math.max/interpolation needed.
      const midX = dx === 0
        ? s.x + NODE_W              // same-column: bulge out of the column to clear siblings
        : s.x + dx * 0.5;           // cross-column: original formula, zero regression
      ctx.beginPath();
      ctx.moveTo(s.x + NODE_W / 2, s.y);          // from right edge of source
      ctx.bezierCurveTo(
        midX, s.y,
        midX, t.y,
        t.x - NODE_W / 2, t.y                      // to left edge of target
      );
      ctx.strokeStyle = color;
      ctx.lineWidth = 2 / k;

      if (edgeType === "circular" || edgeType === "function_call") {
        ctx.setLineDash([5 / k, 4 / k]);
      } else {
        ctx.setLineDash([]);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrow at target left edge
      if (alpha >= 0.18) {
        const tx2 = t.x - NODE_W / 2;
        const ty2 = t.y;
        drawArrow(tx2, ty2, Math.sign(tx2 - midX) || 1, 0, color, k);
      }

      // Circular warning label
      if (edgeType === "circular" && alpha >= 0.18 && k >= 0.35) {
        const midX2 = (s.x + t.x) / 2;
        const midY2 = (s.y + t.y) / 2 - 10;
        ctx.fillStyle = EDGE_COLORS.circular;
        ctx.font = "500 10px Sora, sans-serif";
        ctx.fillText("⚠ circular", midX2, midY2);
      }
    }
    ctx.globalAlpha = 1;

    // ── NODES ─────────────────────────────────────────────────────────────
    // lazy-render: iterasi visible subset aja (§5.7). Filter lama baca
    // store.state.openDirs (milik sidebar) — salah state, sudah dihapus.
    for (const n of visibleNodesCache) {
      drawNode(n, focus, k);
    }

    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function precomputeNeighbors() {
    const byId = new Map(nodes.map(n => [n.id, n]));
    nodes.forEach(n => { n._neighbors = new Set([n.id]); n._degree = 0; });
    edges.forEach(e => {
      const s = typeof e.source === "object" ? e.source.id : e.source;
      const t = typeof e.target === "object" ? e.target.id : e.target;
      const sn = byId.get(s), tn = byId.get(t);
      if (sn && tn) {
        sn._neighbors.add(t); tn._neighbors.add(s);
        sn._degree++; tn._degree++;
      }
    });
  }

  // After tree layout, resolve edge source/target to node objects
  function resolveEdges() {
    const byId = new Map(nodes.map(n => [n.id, n]));
    edges.forEach(e => {
      if (typeof e.source === "string") e.source = byId.get(e.source) || e.source;
      if (typeof e.target === "string") e.target = byId.get(e.target) || e.target;
    });
  }

  // ── ZOOM (d3 + manual touch pinch) ────────────────────────────────────────
  function initZoom() {
    zoomBehavior = d3.zoom()
      .scaleExtent([0.15, 3])
      .filter(event => {
        // Allow wheel zoom; allow mouse drag; skip touch (handled manually below)
        return !event.type.startsWith("touch");
      })
      .on("zoom", (event) => {
        transform = { x: event.transform.x, y: event.transform.y, k: event.transform.k };
        draw();
        updateZoomIndicator();
      });
    d3.select(canvas).call(zoomBehavior);

    // ── Manual touch handling for mobile pan + pinch-zoom + tap-to-select ────
    let lastTouches = null;
    let lastDist = null;
    let lastMid = null;
    // tap detection: hanya single-touch yang gak bergerak + cepat = tap node.
    let touchStartPos = null;
    let touchStartTime = 0;
    const TAP_MOVE_THRESHOLD = 10; // px — geser lebih dari ini = pan, bukan tap
    const TAP_MAX_DURATION = 400;  // ms — tekan lama = bukan tap

    function getTouchDist(t1, t2) {
      const dx = t1.clientX - t2.clientX;
      const dy = t1.clientY - t2.clientY;
      return Math.sqrt(dx * dx + dy * dy);
    }
    function getTouchMid(t1, t2) {
      return { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 };
    }

    canvas.addEventListener("touchstart", ev => {
      ev.preventDefault();
      lastTouches = ev.touches;
      if (ev.touches.length === 1) {
        // calon tap — cat posisi + waktu, di-invalidate di touchmove kalau geser.
        touchStartPos = { x: ev.touches[0].clientX, y: ev.touches[0].clientY };
        touchStartTime = Date.now();
      } else {
        touchStartPos = null; // multi-touch = pinch, bukan tap
        if (ev.touches.length === 2) {
          lastDist = getTouchDist(ev.touches[0], ev.touches[1]);
          lastMid  = getTouchMid(ev.touches[0], ev.touches[1]);
        }
      }
    }, { passive: false });

    canvas.addEventListener("touchmove", ev => {
      ev.preventDefault();
      const touches = ev.touches;

      // invalidate tap kalau geser signifikan / jadi multi-touch
      if (touchStartPos && touches.length === 1) {
        const dx = touches[0].clientX - touchStartPos.x;
        const dy = touches[0].clientY - touchStartPos.y;
        if (Math.hypot(dx, dy) > TAP_MOVE_THRESHOLD) touchStartPos = null;
      } else if (touches.length !== 1) {
        touchStartPos = null;
      }

      if (touches.length === 1 && lastTouches && lastTouches.length === 1) {
        // Single finger pan
        const dx = touches[0].clientX - lastTouches[0].clientX;
        const dy = touches[0].clientY - lastTouches[0].clientY;
        const newT = d3.zoomIdentity
          .translate(transform.x + dx, transform.y + dy)
          .scale(transform.k);
        d3.select(canvas).call(zoomBehavior.transform, newT);

      } else if (touches.length === 2 && lastTouches && lastTouches.length >= 2) {
        // Two-finger pinch zoom
        const dist = getTouchDist(touches[0], touches[1]);
        const mid  = getTouchMid(touches[0], touches[1]);
        const rect = canvas.getBoundingClientRect();

        if (lastDist && dist > 0) {
          const scale = dist / lastDist;
          const newK = Math.min(3, Math.max(0.15, transform.k * scale));

          // Zoom toward pinch midpoint
          const mx = mid.x - rect.left;
          const my = mid.y - rect.top;
          const wx = (mx - transform.x) / transform.k;
          const wy = (my - transform.y) / transform.k;
          const newX = mx - wx * newK;
          const newY = my - wy * newK;

          const newT = d3.zoomIdentity.translate(newX, newY).scale(newK);
          d3.select(canvas).call(zoomBehavior.transform, newT);
        }

        // Also pan with two-finger drag
        if (lastMid) {
          const pdx = mid.x - lastMid.x;
          const pdy = mid.y - lastMid.y;
          if (Math.abs(pdx) > 0.1 || Math.abs(pdy) > 0.1) {
            const panT = d3.zoomIdentity
              .translate(transform.x + pdx, transform.y + pdy)
              .scale(transform.k);
            d3.select(canvas).call(zoomBehavior.transform, panT);
          }
        }

        lastDist = dist;
        lastMid  = mid;
      }

      lastTouches = touches;
    }, { passive: false });

    canvas.addEventListener("touchend", ev => {
      ev.preventDefault();
      // tap valid: single-touch start, gak ke-invalidate di touchmove, cepat, semua jari lepas.
      if (touchStartPos && ev.touches.length === 0 &&
          (Date.now() - touchStartTime) < TAP_MAX_DURATION) {
        handleNodeInteraction(touchStartPos.x, touchStartPos.y);
      }
      touchStartPos = null;
      lastTouches = ev.touches;
      if (ev.touches.length < 2) { lastDist = null; lastMid = null; }
    }, { passive: false });
  }

  function updateZoomIndicator() {
    const el = document.getElementById("zoom-level");
    if (el) el.textContent = Math.round(transform.k * 100) + "%";
  }

  function fitToViewport() {
    if (!visibleNodesCache.length) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of visibleNodesCache) {
      const w = nodeWidth(n), h = nodeHeight(n, 1);
      if (n.x - w/2 < minX) minX = n.x - w/2;
      if (n.y - h/2 < minY) minY = n.y - h/2;
      if (n.x + w/2 > maxX) maxX = n.x + w/2;
      if (n.y + h/2 > maxY) maxY = n.y + h/2;
    }
    const pad = 40;
    const tw = (maxX - minX) || 1, th = (maxY - minY) || 1;
    const k = Math.min(width / (tw + pad * 2), height / (th + pad * 2), 2);
    const tx = width / 2 - ((minX + maxX) / 2) * k;
    const ty = height / 2 - ((minY + maxY) / 2) * k;
    d3.select(canvas).transition().duration(300)
      .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  }

  function panTo(node) {
    if (!node || typeof node.x !== "number") return;
    const k = Math.max(transform.k, 0.8);
    const tx = width / 2 - node.x * k;
    const ty = height / 2 - node.y * k;
    d3.select(canvas).transition().duration(280)
      .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  }

  // ── RESIZE ────────────────────────────────────────────────────────────────
  function resize() {
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    width = Math.max(rect.width, 100);
    height = Math.max(rect.height, 100);
    dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    draw();
  }

  // ── TOOLTIP ───────────────────────────────────────────────────────────────
  function showTooltip(node, ev) {
    const tip = document.getElementById("tooltip");
    if (!tip || !node) return;
    if (node.supported === false) {
      tip.innerHTML =
        '<div class="tooltip-filename">' + escapeHtml(basename(node.path || node.id)) + "</div>" +
        '<div class="tooltip-path">' + escapeHtml(node.path || node.id) + "</div>" +
        '<div class="tooltip-divider"></div>' +
        '<div class="tooltip-meta">⚠ ' + escapeHtml(node.unsupported_reason || "unsupported") + "</div>";
      tip.style.display = "block";
      tip.style.left = (ev.clientX + 14) + "px";
      tip.style.top  = (ev.clientY + 14) + "px";
      return;
    }
    const risk = node.risk_summary || "";
    const fns  = (node.functions || []).length;
    tip.innerHTML =
      '<div class="tooltip-filename">' + escapeHtml(basename(node.path || node.id)) + "</div>" +
      '<div class="tooltip-path">' + escapeHtml(node.path || node.id) + "</div>" +
      '<div class="tooltip-divider"></div>' +
      '<div class="tooltip-meta">' + escapeHtml(risk || (fns + " functions")) + "</div>";
    tip.style.display = "block";
    tip.style.left = (ev.clientX + 14) + "px";
    tip.style.top  = (ev.clientY + 14) + "px";
  }

  function hideTooltip() {
    const tip = document.getElementById("tooltip");
    if (tip) tip.style.display = "none";
  }

  function edgeAt(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const wx = (clientX - rect.left - transform.x) / transform.k;
    const wy = (clientY - rect.top  - transform.y) / transform.k;
    const threshold = 8 / transform.k;
    for (const e of edges) {
      const s = e.source, t = e.target;
      if (!s || !t || typeof s.x !== "number") continue;
      const sx = s.x + NODE_W / 2, sy = s.y;
      const tx2 = t.x - NODE_W / 2, ty2 = t.y;
      const midX = (sx + tx2) / 2;
      const cx1 = midX, cy1 = sy, cx2 = midX, cy2 = ty2;
      for (let i = 0; i <= 10; i++) {
        const ti = i / 10, u = 1 - ti;
        const px = u*u*u*sx + 3*u*u*ti*cx1 + 3*u*ti*ti*cx2 + ti*ti*ti*tx2;
        const py = u*u*u*sy + 3*u*u*ti*cy1 + 3*u*ti*ti*cy2 + ti*ti*ti*ty2;
        if (Math.sqrt((wx-px)**2 + (wy-py)**2) < threshold) return e;
      }
    }
    return null;
  }

  function showEdgeTooltip(edge, ev) {
    const tip = document.getElementById("tooltip");
    if (!tip || !edge) return;
    const type = edge.type || "imports";
    const label = type === "circular" ? "circular dependency"
      : type === "function_call" ? "function call" : "import";
    tip.innerHTML = '<div class="tooltip-filename">' + escapeHtml(label) + '</div>';
    tip.style.display = "block";
    tip.style.left = (ev.clientX + 14) + "px";
    tip.style.top  = (ev.clientY + 14) + "px";
  }

  // ── UTILITIES ─────────────────────────────────────────────────────────────
  function basename(p) {
    if (!p) return "";
    const i = p.lastIndexOf("/");
    return i >= 0 ? p.slice(i + 1) : p;
  }
  window.graps.basename = basename;

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function showWarnings(warnings) {
    const banner  = document.getElementById("warning-banner");
    const summary = document.getElementById("warning-summary");
    if (!banner || !summary) return;
    if (!warnings || warnings.length === 0) { banner.style.display = "none"; return; }
    banner.style.display = "";
    summary.textContent = warnings.length + " warning" + (warnings.length === 1 ? "" : "s") +
      " (" + summarizeWarningTypes(warnings) + ")";
  }

  function summarizeWarningTypes(warnings) {
    const counts = {};
    warnings.forEach(w => { counts[w.type] = (counts[w.type] || 0) + 1; });
    return Object.entries(counts).map(([t, c]) => t + "×" + c).join(", ");
  }

  function showEmpty(graph) {
    const empty = document.getElementById("empty-state");
    if (!empty) return true;
    const nNodes = (graph.nodes || []).length;
    let totalFns = 0;
    (graph.nodes || []).forEach(n => { totalFns += (n.functions || []).length; });
    if (nNodes === 0) {
      empty.innerHTML = emptyTpl("◇", "No Python files found",
        "graps scanned " + escapeHtml((graph.meta && graph.meta.root) || ".") +
        " and found 0 .py files to analyze.", "graps ./src");
      empty.style.display = ""; return false;
    }
    if (totalFns === 0) {
      empty.innerHTML = emptyTpl("◇", "Files found, no functions detected",
        "Your Python files may contain only constants, imports, or module-level code.", null);
      empty.style.display = ""; return false;
    }
    if (nNodes === 1 && (graph.edges || []).length === 0) {
      empty.innerHTML = emptyTpl("◉", "Single file (no imports)",
        "This file has no import relationships with other files.", null);
      empty.style.display = ""; return true;
    }
    empty.style.display = "none"; return true;
  }

  function emptyTpl(icon, title, desc, cmd) {
    return '<div class="empty-icon">' + icon + "</div>" +
      '<div class="empty-title">' + escapeHtml(title) + "</div>" +
      '<div class="empty-desc">' + escapeHtml(desc) + "</div>" +
      (cmd ? '<div class="empty-cmd">' + escapeHtml(cmd) + "</div>" : "");
  }

  function updateTopBarStats(meta) {
    const el = document.getElementById("topbar-stats");
    if (!el || !meta) return;
    el.textContent = (meta.total_files || 0) + " files  " + (meta.total_functions || 0) + " fns";
  }

  function debounce(fn, ms) {
    let t = null;
    return function () { const a = arguments; clearTimeout(t); t = setTimeout(() => fn.apply(null, a), ms); };
  }

  // ── GRAPH LOAD ────────────────────────────────────────────────────────────
  async function loadGraph() {
    try {
      const r = await fetch("/api/graph");
      if (!r.ok) throw new Error("HTTP " + r.status);
      const graph = await r.json();
      setState({ graph });

      hideLoading();
      updateTopBarStats(graph.meta);
      showWarnings(graph.warnings);

      const shouldRender = showEmpty(graph);
      if (!shouldRender) return;

      nodes = (graph.nodes || []).map(n => Object.assign({}, n));
      edges = (graph.edges || []).map(e => Object.assign({}, e));

      synthesizeDirNodes();       // TETAP generate semua dir node (data lengkap di memory — lazy RENDER bukan lazy FETCH)
      precomputeNeighbors();      // atas full nodes — _neighbors dipakai isDimmed saat select
      resolveEdges();             // resolve string ids → node objects (atas full nodes)
      setState({ graphOpenDirs: new Set() });  // default: semua collapsed
      relayout();                 // layout + quadtree + draw atas visible subset (§5.12)

      initZoom();
      fitToViewport();
      // draw() dipanggil di dalam relayout() — tidak perlu panggil lagi di sini.
    } catch (err) {
      hideLoading();
      if (toast) toast("Failed to load graph: " + err.message, "error");
      console.error(err);
    }
  }

  function hideLoading() {
    const s = document.getElementById("loading-screen");
    if (s) s.style.display = "none";
  }

  // ── INTERACTIONS ──────────────────────────────────────────────────────────
  function setupInteractions() {
    canvas.addEventListener("mousemove", ev => {
      const n = nodeAt(ev.clientX, ev.clientY);
      if (n) {
        if (n !== store.state.hoveredNode) setState({ hoveredNode: n });
        showTooltip(n, ev);
        canvas.style.cursor = n.supported !== false ? "pointer" : "default";
      } else {
        const edge = edgeAt(ev.clientX, ev.clientY);
        if (edge) {
          if (store.state.hoveredNode) setState({ hoveredNode: null });
          showEdgeTooltip(edge, ev);
          canvas.style.cursor = "default";
        } else {
          if (store.state.hoveredNode) setState({ hoveredNode: null });
          hideTooltip();
          canvas.style.cursor = "grab";
        }
      }
    });

    canvas.addEventListener("mouseleave", () => {
      setState({ hoveredNode: null });
      hideTooltip();
    });

    canvas.addEventListener("click", ev => {
      // jalur mouse — di touch device click synthesized gak di-fire karena
      // touchstart preventDefault(), tap di-handle eksplisit di touchend.
      handleNodeInteraction(ev.clientX, ev.clientY);
    });

    document.addEventListener("keydown", ev => {
      const tag = (ev.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      if (ev.key === "Escape") { setState({ selectedNode: null }); hideTooltip(); }
      else if (ev.key === "f" || ev.key === "F") { fitToViewport(); }
      else if (ev.key === "h" || ev.key === "H") {
        const cur = store.state.filter;
        setState({ filter: Object.assign({}, cur, { risk: cur.risk === "high" ? null : "high" }) });
      } else if (ev.key === "d" || ev.key === "D") {
        const cur = store.state.filter;
        setState({ filter: Object.assign({}, cur, { dead: !cur.dead }) });
      }
    });

    store.addEventListener("change", e => {
      if (e.detail.keys.includes("filter") ||
          e.detail.keys.includes("selectedNode") ||
          e.detail.keys.includes("hoveredNode")) draw();
    });

    window.addEventListener("graps:dirs-changed", () => draw());

    window.addEventListener("graps:pan-to", ev => {
      // §5.11: cari di FULL data (nodes) — target belum tentu visible,
      // itu justru kasus yang di-handle: expand ancestor dulu, baru pan.
      const node = nodes.find(n => n.id === ev.detail.id || n.path === ev.detail.id);
      if (!node) return;
      expandPathTo(node.id);        // expand ancestors of the target node itself
      expandForSelection(node);     // expand ancestors of edge-neighbors → edges render
      panTo(node);
      setState({ selectedNode: node });
    });

    const toggle = document.getElementById("warning-toggle");
    const banner = document.getElementById("warning-banner");
    if (toggle && banner) {
      toggle.addEventListener("click", () => {
        const expanded = banner.classList.toggle("expanded");
        banner.classList.toggle("collapsed", !expanded);
        toggle.textContent = expanded ? "Hide" : "Show all";
      });
    }
  }

  // ── BOOT ──────────────────────────────────────────────────────────────────
  function boot() {
    wrap   = document.getElementById("graph-wrap");
    canvas = document.getElementById("graph-canvas");
    if (!canvas || !wrap) return;
    ctx = canvas.getContext("2d");
    resize();
    window.addEventListener("resize", debounce(resize, 100));
    setupInteractions();
    loadGraph();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.graps.graph = {
    panTo,
    fit: fitToViewport,
    getNodes: () => nodes,                      // TETAP full data
    getVisibleNodes: () => visibleNodesCache,   // BARU — subset visible (lazy-render)
    getTransform: () => transform,
  };
})();


/* graps — Canvas2D graph renderer + D3 force simulation.
 *
 * Public API: window.graps.graph
 *   .panTo(node)  — center viewport ke node (pakai zoom transform)
 *   .fit()        — fit-to-viewport
 *
 * ponytail: rebuild quadtree tiap tick (O(n)). Cukup untuk <500 nodes;
 * 2000+ butuh throttle atau static index. Upgrade kalau frame drop terasa.
 * ponytail: source code raw belum di-fetch (parser belum ekstrak) — AI
 * dipanggil dengan source="".
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
  let simulation = null;
  let quadtree = null;
  let transform = { x: 0, y: 0, k: 1 };
  let zoomBehavior = null;

  // Risk → ring color (sinkron dengan CSS tokens, hardcoded karena ctx tidak
  // bisa baca CSS custom prop dengan murah; ponytail: copy dari ui-ux §1.1).
  const RING = {
    clean:  "oklch(52% 0.02 250)",
    yellow: "oklch(76% 0.15 75)",
    red:    "oklch(58% 0.22 25)",
  };
  const RING_WIDTH = { clean: 1.5, yellow: 2, red: 2.5 };
  const NODE_FILL = "oklch(18% 0.008 75)";
  const NODE_FILL_UNSUPPORTED = "oklch(35% 0.005 75)";
  const EDGE_DEFAULT = "oklch(65% 0.008 75)";
  const EDGE_ACTIVE = "oklch(94% 0.006 75)";

  // Phase B: edge colors
  const EDGE_COLORS = {
    imports:       "oklch(52% 0.15 145)",   // hijau
    circular:      "oklch(58% 0.22 25)",    // merah
    function_call: "oklch(55% 0.18 280)",   // biru/ungu
  };

  // Phase B: rectangle node sizing
  const NODE_MIN_WIDTH = 140;
  const NODE_HEIGHT_BASE = 44;
  const NODE_LINE_HEIGHT = 18;
  const NODE_PADDING = 10;
  const BG_BORDER = "oklch(24% 0.008 75)";
  const INK_PRIMARY = "oklch(94% 0.006 75)";
  const INK_SECONDARY = "oklch(65% 0.008 75)";
  const INK_MUTED = "oklch(42% 0.006 75)";

  function nodeRisk(n) {
    return n.risk_level || "clean";
  }

  function nodeWidth(n) {
    const textWidth = ctx ? ctx.measureText(n.id.split('/').pop()).width : 100;
    return Math.max(NODE_MIN_WIDTH, textWidth + NODE_PADDING * 2);
  }

  function nodeHeight(n, zoomK) {
    if (zoomK < 0.5) return NODE_HEIGHT_BASE;
    const fns = (n.functions || []).slice(0, 5);
    return NODE_HEIGHT_BASE + fns.length * NODE_LINE_HEIGHT + 8;
  }

  // Phase B: rectangle hit detection
  function nodeAt(clientX, clientY) {
    if (!quadtree) return null;
    const rect = canvas.getBoundingClientRect();
    const sx = clientX - rect.left;
    const sy = clientY - rect.top;
    const wx = (sx - transform.x) / transform.k;
    const wy = (sy - transform.y) / transform.k;

    const found = quadtree.find(wx, wy, 120);
    if (!found) return null;

    const w = nodeWidth(found);
    const h = nodeHeight(found, transform.k);
    const nx = found.x - w / 2;
    const ny = found.y - h / 2;

    return (wx >= nx && wx <= nx + w && wy >= ny && wy <= ny + h) ? found : null;
  }

  // Phase B: rounded rectangle path helper
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

  // Phase B: bezier edge + arrow helpers
  function rectBorderIntersection(cx, cy, w, h, dx, dy) {
    const hw = w / 2, hh = h / 2;
    const scale = Math.min(hw / Math.abs(dx || 1e-9), hh / Math.abs(dy || 1e-9));
    return { x: cx + dx * scale, y: cy + dy * scale };
  }

  function drawArrow(tx, ty, dx, dy, color, k) {
    const angle = Math.atan2(dy, dx);
    const size = 8 / k;
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
    if (simulation) {
      simulation.force("center", d3.forceCenter(width / 2, height / 2));
      simulation.alpha(0.3).restart();
    }
  }

  function buildQuadtree() {
    quadtree = d3.quadtree()
      .x((d) => d.x)
      .y((d) => d.y)
      .addAll(nodes);
  }

  function isDimmed(node) {
    const f = store.state.filter;
    const hov = store.state.hoveredNode;
    const sel = store.state.selectedNode;
    if (f.risk === "high" && nodeRisk(node) !== "red") return true;
    if (f.dead) {
      // Dead = semua fungsi is_dead_code, atau tidak ada fungsi sama sekali
      // tapi tetap connected. ponytail: simple — kalau ada minimal 1 fungsi
      // non-dead → bukan dead.
      const fns = node.functions || [];
      if (fns.length === 0) return false;  // zero-function files: neutral, show them (Finding 12)
      const allDead = fns.every((fn) => fn.is_dead_code);
      if (!allDead) return true;
    }
    // Selected/hover: dim semua yang bukan node itu atau neighbor.
    const focus = sel || hov;
    if (focus && focus !== node) {
      const neigh = focus._neighbors;
      if (neigh && !neigh.has(node.id)) return true;
    }
    return false;
  }

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

    // Phase B2: Bezier edges with arrows
    for (const e of edges) {
      const s = e.source, t = e.target;
      if (!s || !t || typeof s.x !== "number") continue;

      const edgeType = e.type || "imports";
      const color = edgeType === "circular"
        ? EDGE_COLORS.circular
        : edgeType === "function_call"
          ? EDGE_COLORS.function_call
          : EDGE_COLORS.imports;

      let alpha = 0.18;
      if (focus && (s.id === focus.id || t.id === focus.id)) alpha = 0.7;
      else if (focus) alpha = 0.04;
      ctx.globalAlpha = alpha;

      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const cx1 = s.x + dx * 0.4;
      const cy1 = s.y;
      const cx2 = s.x + dx * 0.6;
      const cy2 = t.y;

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.bezierCurveTo(cx1, cy1, cx2, cy2, t.x, t.y);
      ctx.strokeStyle = color;
      ctx.lineWidth = ((e.weight || 1) * 1.5) / k;

      if (edgeType === "circular") {
        ctx.setLineDash([6 / k, 3 / k]);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrow at target border
      if (alpha >= 0.18) {
        const tw = nodeWidth(t), th = nodeHeight(t, k);
        const arrowPt = rectBorderIntersection(t.x, t.y, tw, th, dx, dy);
        drawArrow(arrowPt.x, arrowPt.y, dx, dy, color, k);
      }

      // Circular warning label
      if (edgeType === "circular" && alpha >= 0.18) {
        const midX = (s.x + t.x) / 2;
        const midY = (s.y + t.y) / 2 - 10 / k;
        ctx.fillStyle = EDGE_COLORS.circular;
        ctx.font = (500) + " " + (10 / k) + "px Sora, sans-serif";
        ctx.fillText("⚠ circular", midX, midY);
      }
    }
    ctx.globalAlpha = 1;
    // Phase B1: Rectangle nodes
    // B6: openDirs visibility filter
    const _openDirs = store.state.openDirs;
    const _dirFilter = _openDirs && _openDirs.size > 0;

    for (const n of nodes) {
      // B6: skip node if dir filter active and node not in openDirs
      if (_dirFilter) {
        const parts = n.id.split("/");
        let visible = false;
        for (let i = 1; i <= parts.length; i++) {
          if (_openDirs.has(parts.slice(0, i).join("/"))) { visible = true; break; }
        }
        if (!visible) continue;
      }
      const w = nodeWidth(n);
      const h = nodeHeight(n, k);
      const x = n.x - w / 2;
      const y = n.y - h / 2;
      const r = 6;
      const risk = nodeRisk(n);
      const ring = RING[risk] || RING.clean;
      const rw = RING_WIDTH[risk] || 1.5;
      const unsupported = n.supported === false;
      const dim = isDimmed(n);

      let opacity = 0.65;
      if (dim) opacity = 0.1;
      else if (unsupported) opacity = 0.5;
      else if (focus && n === focus) opacity = 1.0;
      else if (focus) opacity = 0.85;
      ctx.globalAlpha = opacity;

      // Background fill
      ctx.fillStyle = unsupported ? NODE_FILL_UNSUPPORTED : NODE_FILL;
      roundRect(ctx, x, y, w, h, r);
      ctx.fill();

      // Border
      ctx.strokeStyle = ring;
      ctx.lineWidth = rw / k;
      if (unsupported) {
        // B4: Ghost node — dashed border
        ctx.setLineDash([4 / k, 4 / k]);
      }
      roundRect(ctx, x, y, w, h, r);
      ctx.stroke();
      ctx.setLineDash([]);

      // Selected glow
      if (sel && n === sel && !dim) {
        ctx.shadowColor = ring;
        ctx.shadowBlur = 8 / k;
        roundRect(ctx, x, y, w, h, r);
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // Red glow for high risk
      if (risk === "red" && !dim && sel !== n) {
        ctx.shadowColor = RING.red;
        ctx.shadowBlur = 12 / k;
        roundRect(ctx, x, y, w, h, r);
        ctx.strokeStyle = ring;
        ctx.lineWidth = rw / k;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // Filename header
      ctx.fillStyle = INK_PRIMARY;
      ctx.font = "600 " + (12 / k) + "px Sora, sans-serif";
      const fname = n.id.split("/").pop() || n.id;
      ctx.fillText(fname, x + NODE_PADDING, y + 16 / k);

      // Details when zoomed in
      if (k >= 0.5) {
        // Divider
        ctx.strokeStyle = BG_BORDER;
        ctx.lineWidth = 1 / k;
        ctx.beginPath();
        ctx.moveTo(x, y + NODE_HEIGHT_BASE - 8);
        ctx.lineTo(x + w, y + NODE_HEIGHT_BASE - 8);
        ctx.stroke();

        // Function list (max 5)
        const fns = (n.functions || []).slice(0, 5);
        ctx.fillStyle = INK_SECONDARY;
        ctx.font = "400 " + (10 / k) + "px JetBrains Mono, monospace";
        fns.forEach((fn, i) => {
          ctx.fillText("ƒ " + fn.name, x + NODE_PADDING, y + NODE_HEIGHT_BASE + i * NODE_LINE_HEIGHT);
        });
        if ((n.functions || []).length > 5) {
          ctx.fillStyle = INK_MUTED;
          ctx.fillText("+" + ((n.functions || []).length - 5) + " more", x + NODE_PADDING, y + NODE_HEIGHT_BASE + 5 * NODE_LINE_HEIGHT);
        }

        // Import count
        const importCount = (n.imports || []).length;
        if (importCount > 0) {
          ctx.fillStyle = INK_MUTED;
          ctx.fillText("↳ " + importCount + " import" + (importCount > 1 ? "s" : ""), x + NODE_PADDING, y + h - 6);
        }
      }
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function tick() {
    buildQuadtree();
    draw();
  }

  function precomputeNeighbors() {
    // Map node.id → Set of neighbor ids (incl. self).
    const byId = new Map(nodes.map((n) => [n.id, n]));
    nodes.forEach((n) => { n._neighbors = new Set([n.id]); n._degree = 0; });
    edges.forEach((e) => {
      const s = typeof e.source === "object" ? e.source.id : e.source;
      const t = typeof e.target === "object" ? e.target.id : e.target;
      const sn = byId.get(s), tn = byId.get(t);
      if (sn && tn) {
        sn._neighbors.add(t);
        tn._neighbors.add(s);
        sn._degree++; tn._degree++;
      }
    });
  }

  function initSim() {
    simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id((d) => d.id).distance(80).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius((d) => {
        const w = nodeWidth(d), h = nodeHeight(d, 1);
        return Math.sqrt(w * w + h * h) / 2 + 4;
      }))
      .on("tick", tick);
  }

  function initZoom() {
    zoomBehavior = d3.zoom()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => {
        transform = { x: event.transform.x, y: event.transform.y, k: event.transform.k };
        draw();
        updateZoomIndicator();
      });
    d3.select(canvas).call(zoomBehavior);
  }

  function updateZoomIndicator() {
    const el = document.getElementById("zoom-level");
    if (el) el.textContent = Math.round(transform.k * 100) + "%";
  }

  function fitToViewport() {
    if (!nodes.length) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      if (n.x < minX) minX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.x > maxX) maxX = n.x;
      if (n.y > maxY) maxY = n.y;
    }
    const pad = 60;
    const w = (maxX - minX) || 1, h = (maxY - minY) || 1;
    const k = Math.min(width / (w + pad * 2), height / (h + pad * 2), 2);
    const tx = (width - (minX + maxX) * k) / 2;
    const ty = (height - (minY + maxY) * k) / 2;
    d3.select(canvas).transition().duration(300)
      .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  }

  function panTo(node) {
    if (!node || typeof node.x !== "number") return;
    const k = Math.max(transform.k, 1);
    const tx = width / 2 - node.x * k;
    const ty = height / 2 - node.y * k;
    d3.select(canvas).transition().duration(280)
      .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  }

  // Tooltip.
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
      tip.style.top = (ev.clientY + 14) + "px";
      return;
    }
    const risk = node.risk_summary || "";
    const fns = (node.functions || []).length;
    tip.innerHTML =
      '<div class="tooltip-filename">' + escapeHtml(basename(node.path || node.id)) + "</div>" +
      '<div class="tooltip-path">' + escapeHtml(node.path || node.id) + "</div>" +
      '<div class="tooltip-divider"></div>' +
      '<div class="tooltip-meta">' + escapeHtml(risk || (fns + " functions")) + "</div>";
    tip.style.display = "block";
    tip.style.left = (ev.clientX + 14) + "px";
    tip.style.top = (ev.clientY + 14) + "px";
  }

  function hideTooltip() {
    const tip = document.getElementById("tooltip");
    if (tip) tip.style.display = "none";
  }

  // B5: Edge hit detection — brute-force O(edges), ok for <500 edges
  function edgeAt(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const sx = clientX - rect.left;
    const sy = clientY - rect.top;
    const wx = (sx - transform.x) / transform.k;
    const wy = (sy - transform.y) / transform.k;
    const threshold = 8 / transform.k;
    for (const e of edges) {
      const s = e.source, t = e.target;
      if (!s || !t || typeof s.x !== "number") continue;
      // Point-to-bezier approximation: sample 10 points
      const dx = t.x - s.x, dy = t.y - s.y;
      const cx1 = s.x + dx * 0.4, cy1 = s.y;
      const cx2 = s.x + dx * 0.6, cy2 = t.y;
      for (let i = 0; i <= 10; i++) {
        const ti = i / 10;
        const u = 1 - ti;
        const px = u*u*u * s.x + 3*u*u*ti * cx1 + 3*u*ti*ti * cx2 + ti*ti*ti * t.x;
        const py = u*u*u * s.y + 3*u*u*ti * cy1 + 3*u*ti*ti * cy2 + ti*ti*ti * t.y;
        const dist = Math.sqrt((wx - px) ** 2 + (wy - py) ** 2);
        if (dist < threshold) return e;
      }
    }
    return null;
  }

  function showEdgeTooltip(edge, ev) {
    const tip = document.getElementById("tooltip");
    if (!tip || !edge) return;
    const type = edge.type || "imports";
    const label = type === "circular" ? "circular dependency"
      : type === "function_call" ? "function call"
      : "import";
    tip.innerHTML = '<div class="tooltip-filename">' + escapeHtml(label) + '</div>';
    tip.style.display = "block";
    tip.style.left = (ev.clientX + 14) + "px";
    tip.style.top = (ev.clientY + 14) + "px";
  }

  function basename(p) {
    if (!p) return "";
    const i = p.lastIndexOf("/");
    return i >= 0 ? p.slice(i + 1) : p;
  }
  window.graps.basename = basename;  // Finding 14: shared ke panel.js

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function showWarnings(warnings) {
    const banner = document.getElementById("warning-banner");
    const summary = document.getElementById("warning-summary");
    if (!banner || !summary) return;
    if (!warnings || warnings.length === 0) {
      banner.style.display = "none";
      return;
    }
    banner.style.display = "";
    summary.textContent = warnings.length + " warning" + (warnings.length === 1 ? "" : "s") +
      " (" + summarizeWarningTypes(warnings) + ")";
  }

  function summarizeWarningTypes(warnings) {
    const counts = {};
    warnings.forEach((w) => { counts[w.type] = (counts[w.type] || 0) + 1; });
    return Object.entries(counts).map(([t, c]) => t + "×" + c).join(", ");
  }

  function showEmpty(graph) {
    const empty = document.getElementById("empty-state");
    if (!empty) return;
    const nNodes = (graph.nodes || []).length;
    let totalFns = 0;
    (graph.nodes || []).forEach((n) => { totalFns += (n.functions || []).length; });
    if (nNodes === 0) {
      empty.innerHTML = emptyTpl("◇", "No Python files found",
        "graps scanned " + escapeHtml(graph.meta && graph.meta.root || ".") +
        " and found 0 .py files to analyze.",
        "graps ./src");
      empty.style.display = "";
      return false;
    }
    if (totalFns === 0) {
      empty.innerHTML = emptyTpl("◇", "Files found, no functions detected",
        "Your Python files may contain only constants, imports, or module-level code.",
        null);
      empty.style.display = "";
      return false;
    }
    if (nNodes === 1 && (graph.edges || []).length === 0) {
      empty.innerHTML = emptyTpl("◉", "Single file (no imports)",
        "This file has no import relationships with other files.", null);
      empty.style.display = "";
      // Tetap render canvas — single node still useful.
      return true;
    }
    empty.style.display = "none";
    return true;
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
    el.textContent = (meta.total_files || 0) + " files  " +
      (meta.total_functions || 0) + " fns";
  }

  function debounce(fn, ms) {
    let t = null;
    return function () {
      const args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(null, args), ms);
    };
  }

  async function loadGraph() {
    try {
      const r = await fetch("/api/graph");
      if (!r.ok) throw new Error("HTTP " + r.status);
      const graph = await r.json();
      setState({ graph: graph });

      hideLoading();
      updateTopBarStats(graph.meta);
      showWarnings(graph.warnings);

      const shouldRender = showEmpty(graph);
      if (!shouldRender) return;

      nodes = (graph.nodes || []).map((n) => Object.assign({}, n));
      edges = (graph.edges || []).map((e) => Object.assign({}, e));
      precomputeNeighbors();
      initSim();
      initZoom();
      draw();
    } catch (err) {
      hideLoading();
      if (toast) toast("Failed to load graph: " + err.message, "error");
      // ponytail: log untuk debug, tidak ada retry UI di MVP.
      console.error(err);
    }
  }

  function hideLoading() {
    const s = document.getElementById("loading-screen");
    if (s) s.style.display = "none";
  }

  function setupInteractions() {
    canvas.addEventListener("mousemove", (ev) => {
      const n = nodeAt(ev.clientX, ev.clientY);
      if (n) {
        // B5: edge tooltip only when no node under cursor
        if (n !== store.state.hoveredNode) {
          setState({ hoveredNode: n });
        }
        showTooltip(n, ev);
        canvas.style.cursor = n.supported !== false ? "pointer" : "default";
      } else {
        // Check edge hover
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

    canvas.addEventListener("click", (ev) => {
      const n = nodeAt(ev.clientX, ev.clientY);
      if (n && n.supported !== false) setState({ selectedNode: n });
    });

    document.addEventListener("keydown", (ev) => {
      const tag = (ev.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      if (ev.key === "Escape") {
        setState({ selectedNode: null });
        hideTooltip();
      } else if (ev.key === "f" || ev.key === "F") {
        fitToViewport();
      } else if (ev.key === "h" || ev.key === "H") {
        const cur = store.state.filter;
        setState({ filter: Object.assign({}, cur, { risk: cur.risk === "high" ? null : "high" }) });
      } else if (ev.key === "d" || ev.key === "D") {
        const cur = store.state.filter;
        setState({ filter: Object.assign({}, cur, { dead: !cur.dead }) });
      }
    });

    store.addEventListener("change", (e) => {
      if (e.detail.keys.includes("filter") || e.detail.keys.includes("selectedNode") || e.detail.keys.includes("hoveredNode")) {
        draw();
      }
    });

    // B6: openDirs filter — listen graps:dirs-changed from sidebar.js
    window.addEventListener("graps:dirs-changed", () => {
      draw();
    });

    window.addEventListener("graps:pan-to", (ev) => {
      const node = nodes.find((n) => n.id === ev.detail.id || n.path === ev.detail.id);
      if (node) {
        panTo(node);
        setState({ selectedNode: node });
      }
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

  function boot() {
    wrap = document.getElementById("graph-wrap");
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
    panTo: panTo,
    fit: fitToViewport,
    getNodes: () => nodes,
  };
})();

/* graps — popover + side panel (Phase C).
 *
 * C1: showPopover/hidePopover via node click, flip near right edge.
 * C2: Side panel with combobox, source viewer placeholder.
 * C3: Preserved caller/callee nav + risk cards from existing panel.
 *
 * ponytail: popover is DOM div, not canvas. Side panel reuse existing render.
 * Chat lives in ai.js — removed from here. */
(function () {
  "use strict";
  window.graps = window.graps || {};
  const store = window.graps.store;
  const setState = window.graps.setState;

  let panelEl;
  const expandedFns = new Set();

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  const basename = window.graps.basename;

  function fmtParam(p) {
    if (!p) return "";
    if (p.annotation) return esc(p.name) + ": " + esc(p.annotation);
    return esc(p.name);
  }

  function critClass(level) {
    return "crit-dot--" + (level || "clean");
  }

  // ============================================================
  // === C1: POPOVER ============================================
  // ============================================================

  function showPopover(node) {
    const el = document.getElementById("node-popover");
    if (!el) return;

    const graph = window.graps.graph;
    const transform = graph ? graph.getTransform() : null;
    if (!transform) return;

    const canvas = document.getElementById("graph-canvas");
    const rect = canvas.getBoundingClientRect();
    const screenX = rect.left + node.x * transform.k + transform.x;
    const screenY = rect.top + node.y * transform.k + transform.y;

    // Position: right of node, flip left if near viewport edge
    el.style.left = (screenX + 12) + "px";
    el.style.top = screenY + "px";
    el.classList.remove("hidden");
    // Flip check after render
    requestAnimationFrame(() => {
      const w = el.offsetWidth;
      if (screenX + 12 + w > window.innerWidth) {
        el.style.left = (screenX - 12 - w) + "px";
      }
    });

    const fns = (node.functions || []);
    const imports = (node.imports || []);
    const usedBy = findUsedBy(node);

    el.innerHTML = `
      <div class="popover-header">
        <span class="popover-filename">${esc(node.id)}</span>
        <button class="popover-expand" title="Open detail">›</button>
      </div>
      <div class="popover-section">
        <div class="popover-label">Functions (${fns.length})</div>
        ${fns.slice(0, 5).map(f =>
          '<div class="popover-fn">' + (f.is_dead_code ? '⚫' : 'ƒ') + ' ' + esc(f.name) + '</div>'
        ).join('')}
        ${fns.length > 5 ? '<div class="popover-more">+' + (fns.length - 5) + ' more</div>' : ''}
      </div>
      <div class="popover-section">
        <div class="popover-label">Imports (${imports.length})</div>
        ${imports.slice(0, 3).map(i =>
          '<div class="popover-import">↳ ' + esc(i.from || i.resolved_path || '?') + '</div>'
        ).join('')}
        ${imports.length > 3 ? '<div class="popover-more">+' + (imports.length - 3) + ' more</div>' : ''}
      </div>
      ${usedBy.length > 0 ? `
      <div class="popover-section">
        <div class="popover-label">Dipakai oleh</div>
        ${usedBy.map(f => '<div class="popover-used">' + esc(f) + '</div>').join('')}
      </div>` : ''}
      ${node.supported === false ? `
      <div class="popover-ghost-hint" data-action="expand">
        📁 ${esc(getDirectory(node.id))} — click to open directory
      </div>` : ''}
    `;

    // Expand icon → open side panel
    el.querySelector(".popover-expand")?.addEventListener("click", (e) => {
      e.stopPropagation();
      setState({ sidePanel: true });
      panelEl?.classList.add("open");
      panelEl?.setAttribute("aria-hidden", "false");
    });
  }

  function hidePopover() {
    const el = document.getElementById("node-popover");
    if (el) el.classList.add("hidden");
  }

  function findUsedBy(node) {
    const graph = store.state.graph;
    if (!graph || !graph.edges) return [];
    return (graph.edges || [])
      .filter(e => e.target === node.id)
      .map(e => e.source)
      .slice(0, 5);
  }

  function getDirectory(nodeId) {
    const i = nodeId.lastIndexOf("/");
    return i >= 0 ? nodeId.slice(0, i) : "";
  }

  // ============================================================
  // === C2 + C3: SIDE PANEL ===================================
  // ============================================================

  function fnRow(fn, idx) {
    const isOpen = expandedFns.has(fn.name);
    const ret = fn.returns ? esc(fn.returns) : "—";
    const dead = fn.is_dead_code
      ? '<span class="fn-dead">dead code</span>'
      : "";
    return (
      '<div class="fn-row' + (isOpen ? " active" : "") + '" data-fn="' + esc(fn.name) + '">' +
        '<span class="crit-dot ' + critClass(fn.criticality) + '"></span>' +
        '<span class="fn-name">' + esc(fn.name) + "</span>" +
        dead +
        '<span class="fn-return">' + ret + "</span>" +
        '<span class="fn-chevron">▸</span>' +
      "</div>" +
      (isOpen ? fnDetail(fn) : "")
    );
  }

  function fnDetail(fn) {
    const params = (fn.params || []).map(fmtParam).filter(Boolean);
    const callers = fn.callers || [];
    const callees = fn.callees || [];
    const risks = fn.risks || [];
    const lineRange = (fn.line_start != null)
      ? (fn.line_start + (fn.line_end != null ? " – " + fn.line_end : ""))
      : "—";

    return (
      '<div class="fn-detail" data-fn-detail="' + esc(fn.name) + '">' +
        (params.length
          ? '<div class="detail-label">Parameters</div>' +
            '<div class="detail-value">' + params.join(", ") + "</div>"
          : "") +
        (fn.returns
          ? '<div class="detail-label">Returns</div>' +
            '<div class="detail-value">' + esc(fn.returns) + "</div>"
          : "") +
        '<div class="detail-label">Lines</div>' +
        '<div class="detail-value">' + lineRange + "</div>" +

        (callers.length
          ? '<div class="detail-label">Called by ' + callers.length + "</div>" +
            callers.map((c) => {
              const target = c.file || "";
              const name = c.name || "";
              return '<div class="caller-item"' +
                (target ? ' data-pan-to="' + esc(target) + '"' : "") +
                ">" + esc(name) +
                (target ? ' <span style="opacity:0.5">' + esc(target) + "</span>" : "") +
                "</div>";
            }).join("")
          : "") +

        (callees.length
          ? '<div class="detail-label">Calls ' + callees.length + "</div>" +
            callees.map((c) => {
              const target = c.resolved_file || "";
              const name = c.name || "";
              return '<div class="caller-item"' +
                (target ? ' data-pan-to="' + esc(target) + '"' : "") +
                ">" + esc(name) +
                (target ? ' <span style="opacity:0.5">' + esc(target) + "</span>" : "") +
                "</div>";
            }).join("")
          : "") +

        (risks.length
          ? '<div class="detail-label">Risks</div>' +
            risks.map(riskCard).join("")
          : "") +
      "</div>"
    );
  }

  function riskCard(r) {
    const sev = r.severity || "low";
    const files = (r.affected_files || []).map((f) =>
      '<div class="risk-file">' + esc(f) + "</div>"
    ).join("");
    return (
      '<div class="risk-card risk-card--' + esc(sev) + '">' +
        '<div class="risk-title">' + esc(sev) + " " + esc(r.type || "") + "</div>" +
        '<div class="risk-desc">' + esc(r.detail || "") + "</div>" +
        (files ? '<div class="risk-files">' + files + "</div>" : "") +
      "</div>"
    );
  }

  function currentNode() {
    return store.state.selectedNode;
  }

  function findNodeByPath(rel) {
    const g = store.state.graph;
    if (!g || !g.nodes) return null;
    return (g.nodes || []).find((n) => n.path === rel || n.id === rel) || null;
  }

  // C2: ComboBox source viewer placeholder — spec §7.2 top section
  function renderCombobox(node) {
    const fns = node.functions || [];
    const imps = node.imports || [];
    return (
      '<div class="panel-section">' +
        '<div class="panel-label">Fungsi & Import</div>' +
        '<select class="panel-combobox" id="fn-select">' +
          '<option value="">Pilih fungsi atau import...</option>' +
          '<optgroup label="Fungsi">' +
            fns.map(f => '<option value="fn:' + esc(f.name) + '">' + esc(f.name) + '</option>').join('') +
          '</optgroup>' +
          '<optgroup label="Import">' +
            imps.map(i => '<option value="im:' + esc(i.from || i.resolved_path || '') + '">' + esc(i.from || i.resolved_path || '?') + '</option>').join('') +
          '</optgroup>' +
        '</select>' +
        '<div id="source-viewer" class="hidden" style="margin-top:8px">' +
          '<pre><code class="language-python" id="source-code"></code></pre>' +
        '</div>' +
      '</div>'
    );
  }

  // C2: AI context bridge — spec §7.2 bottom section
  function renderAIHint(node) {
    return (
      '<div class="panel-section panel-ai">' +
        '<div class="panel-label">AI Chat</div>' +
        '<div id="panel-ai-hint">' +
          'Context aktif: <span class="panel-tag">@' + esc(node.id) + '</span>' +
          '<button id="open-ai-bar" class="panel-ai-btn">Buka AI chat ↓</button>' +
        '</div>' +
      '</div>'
    );
  }

  // F2: loadSourceCode — fetch /api/source, render <code>, Prism.highlightElement.
  // ponytail: guard Prism undefined (CDN block / offline) → plain text fallback.
  async function loadSourceCode(fileId, fnName) {
    var viewer = document.getElementById("source-viewer");
    var codeEl = document.getElementById("source-code");
    if (!viewer || !codeEl) return;
    viewer.classList.remove("hidden");
    codeEl.textContent = "Loading…";
    try {
      var url = "/api/source?file=" + encodeURIComponent(fileId) +
                "&fn=" + encodeURIComponent(fnName);
      var res = await fetch(url);
      var data = await res.json();
      if (data.error) {
        codeEl.className = "language-none";
        codeEl.textContent = "Error: " + data.error;
        return;
      }
      codeEl.textContent = data.source || "";
      codeEl.className = "language-" + (data.language || "none");
      if (window.Prism && Prism.highlightElement) {
        Prism.highlightElement(codeEl);
      }
    } catch (err) {
      codeEl.className = "language-none";
      codeEl.textContent = "Gagal load source code";
    }
  }

  function render() {
    const node = currentNode();
    if (!panelEl) return;
    if (!node) {
      panelEl.classList.remove("open");
      panelEl.setAttribute("aria-hidden", "true");
      return;
    }
    panelEl.classList.add("open");
    panelEl.setAttribute("aria-hidden", "false");
    // E1: mobile orchestration — track active panel
    if (window.graps.setActivePanel) window.graps.setActivePanel('sidepanel');

    const fns = node.functions || [];
    const consts = node.constants || [];
    const imps = node.imports || [];

    let high = 0, medium = 0;
    fns.forEach((fn) => {
      (fn.risks || []).forEach((r) => {
        if (r.severity === "high") high++;
        else if (r.severity === "medium") medium++;
      });
    });

    // Header
    var html =
      '<div class="panel-header">' +
        '<button class="panel-close" id="panel-close" aria-label="Close panel">×</button>' +
        '<div class="panel-filename">' + esc(basename(node.path || node.id)) + "</div>" +
        '<div class="panel-filepath">' + esc(node.path || node.id) + "</div>" +
        '<div class="badge-row">' +
          (high ? '<span class="badge badge--high">' + high + " high</span>" : "") +
          (medium ? '<span class="badge badge--medium">' + medium + " medium</span>" : "") +
          '<span class="badge badge--count">' + fns.length + " functions</span>" +
        "</div>" +
      "</div>";

    // C2: Combobox + source viewer (spec §7.2)
    html += renderCombobox(node);

    // C2: AI hint → inject @tag ke AI bar
    html += renderAIHint(node);

    // C3: Caller/callee nav + risk cards (preservasi existing, di bawah combobox)
    html +=
      '<div class="section-header">Functions <span class="section-count">' + fns.length + "</span></div>" +
      (fns.length ? fns.map(fnRow).join("")
        : '<div class="fn-row" style="cursor:default;color:var(--ink-muted)">No functions</div>') +

      (consts.length ? (
        '<div class="section-header">Constants <span class="section-count">' + consts.length + "</span></div>" +
        consts.map((c) =>
          '<div class="fn-row" style="cursor:default">' +
            '<span class="fn-name">' + esc(c.name) + "</span>" +
            '<span class="fn-return">' + esc(c.value) + "</span>" +
          "</div>"
        ).join("")
      ) : "") +

      (imps.length ? (
        '<div class="section-header">Imports <span class="section-count">' + imps.length + "</span></div>" +
        imps.map((i) => {
          const names = (i.names || []).join(", ");
          return '<div class="fn-row" data-pan-to="' + esc(i.resolved_path || "") + '"' +
            (i.resolved_path ? "" : ' style="cursor:default"') + ">" +
            '<span class="fn-name">' + esc(i.from || "") + "</span>" +
            '<span class="fn-return">' + esc(names) + "</span>" +
            "</div>";
        }).join("")
      ) : "");

    panelEl.innerHTML = html;
    wireEvents();
  }

  function wireEvents() {
    var node = currentNode();

    // Close button
    var closeBtn = document.getElementById("panel-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        panelEl.classList.remove("open");
        panelEl.setAttribute("aria-hidden", "true");
        setState({ sidePanel: false });
        // E1: reset active panel on close
        if (window.graps.setActivePanel) window.graps.setActivePanel(null);
      });
    }

    // C2: Combobox handler
    var fnSelect = document.getElementById("fn-select");
    if (fnSelect && node) {
      fnSelect.addEventListener("change", (e) => {
        var val = e.target.value;
        if (val.startsWith("fn:")) {
          loadSourceCode(node.id, val.slice(3));
        }
      });
    }

    // C2: AI hint button → inject tag ke ai.js
    var openAiBtn = document.getElementById("open-ai-bar");
    if (openAiBtn && node) {
      openAiBtn.addEventListener("click", () => {
        if (window.graps.ai && window.graps.ai.injectTag) {
          window.graps.ai.injectTag(node.id);
        }
        var aiBar = document.getElementById("ai-bar");
        if (aiBar) aiBar.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    }

    // C3: Expandable fn rows (caller/callee preserved)
    panelEl.querySelectorAll(".fn-row[data-fn]").forEach((row) => {
      row.addEventListener("click", (ev) => {
        if (ev.target.closest("[data-pan-to]")) return;
        const name = row.dataset.fn;
        if (expandedFns.has(name)) expandedFns.delete(name);
        else expandedFns.add(name);
        render();
      });
    });

    // C3: Pan-to links
    panelEl.querySelectorAll("[data-pan-to]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const target = el.dataset.panTo;
        if (target) {
          window.dispatchEvent(new CustomEvent("graps:pan-to", { detail: { id: target } }));
        }
      });
    });
  }

  // ============================================================
  // === BOOT ===================================================
  // ============================================================

  function boot() {
    panelEl = document.getElementById("side-panel");
    if (!panelEl) return;

    store.addEventListener("change", (e) => {
      if (!e.detail.keys.includes("selectedNode")) return;
      const node = store.state.selectedNode;
      expandedFns.clear();

      if (node) {
        showPopover(node);
        // Only re-render side panel if it was already open (preserves lazy load)
        if (store.state.sidePanel) render();
      } else {
        hidePopover();
        panelEl.classList.remove("open");
        panelEl.setAttribute("aria-hidden", "true");
        setState({ sidePanel: false });
      }
    });

    // Also re-render when sidePanel state changes (via popover expand click)
    store.addEventListener("change", (e) => {
      if (!e.detail.keys.includes("sidePanel")) return;
      if (store.state.sidePanel && store.state.selectedNode) {
        render();
      } else if (!store.state.sidePanel) {
        panelEl.classList.remove("open");
        panelEl.setAttribute("aria-hidden", "true");
      }
    });

    // Delegated: ghost node popover click → expand directory
    document.getElementById("node-popover")?.addEventListener("click", (e) => {
      const hint = e.target.closest("[data-action=\"expand\"]");
      if (!hint) return;
      const dirName = hint.textContent.replace(/^.*?📁\s*/, "").replace(/\s*—.*$/, "").trim();
      if (dirName && window.graps.sidebar) window.graps.sidebar.expandDirectory(dirName);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

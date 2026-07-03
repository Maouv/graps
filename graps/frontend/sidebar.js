/* graps — directory sidebar (Phase D1).
 *
 * Public API: window.graps.sidebar
 *   .init()              — boot sidebar
 *   .expandDirectory(d)  — expand dir via ghost node click
 */
(function () {
  "use strict";
  window.graps = window.graps || {};
  const store = window.graps.store;
  const setState = window.graps.setState;

  let sidebarEl;

  function init() {
    sidebarEl = document.getElementById("dir-sidebar");
    if (!sidebarEl) return;

    // E1: chevron toggle sidebar
    document.getElementById("sidebar-chevron")?.addEventListener("click", () => {
      const cur = store.state.activePanel;
      if (cur === 'sidebar') window.graps.setActivePanel(null);
      else window.graps.setActivePanel('sidebar');
    });

    store.addEventListener("change", (e) => {
      if (e.detail.keys.includes("graph") || e.detail.keys.includes("openDirs")) {
        renderSidebar();
      }
    });
  }

  function renderSidebar() {
    const graph = store.state.graph;
    if (!graph || !graph.nodes || !graph.nodes.length) {
      sidebarEl.innerHTML = '<div class="sidebar-empty">Scan project to begin</div>';
      return;
    }
    const tree = buildDirTree(graph.nodes);
    sidebarEl.innerHTML = renderTree(tree);

    sidebarEl.querySelectorAll(".dir-item").forEach((el) => {
      el.addEventListener("click", () => {
        toggleDirectory(el.dataset.dir);
      });
    });
  }

  function buildDirTree(nodes) {
    const dirs = new Set();
    nodes.forEach((n) => {
      const parts = n.id.split("/");
      for (let i = 1; i < parts.length; i++) {
        dirs.add(parts.slice(0, i).join("/"));
      }
    });
    return Array.from(dirs).sort();
  }

  function renderTree(dirs) {
    const openDirs = store.state.openDirs || new Set();
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    return dirs.map((dir) => {
      const parts = dir.split("/");
      const depth = parts.length - 1;
      const name = isMobile
        ? parts.slice(-2).join("/") + "/"
        : parts[parts.length - 1] + "/";
      const isOpen = openDirs.has(dir);
      return (
        '<div class="dir-item depth-' + depth + '" data-dir="' + dir + '">' +
          '<span class="dir-icon">' + (isOpen ? "▾" : "▸") + "</span>" +
          '<span class="dir-name">' + name + "</span>" +
        "</div>"
      );
    }).join("");
  }

  function toggleDirectory(dir) {
    const current = store.state.openDirs || new Set();
    const next = new Set(current);
    if (next.has(dir)) { next.delete(dir); }
    else { next.add(dir); }
    setState({ openDirs: next });
    window.dispatchEvent(new CustomEvent("graps:dirs-changed"));
    // E1: mobile orchestration — notify active panel
    if (window.graps.setActivePanel) window.graps.setActivePanel('sidebar');
  }

  function expandDirectory(dir) {
    const current = store.state.openDirs || new Set();
    const next = new Set(current);
    next.add(dir);
    setState({ openDirs: next });
    window.dispatchEvent(new CustomEvent("graps:dirs-changed"));
  }

  window.graps.sidebar = { init: init, expandDirectory: expandDirectory };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

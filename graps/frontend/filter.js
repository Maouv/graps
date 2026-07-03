/* graps — shared state via EventTarget (Task_plan keputusan final).
 *
 * Public API:
 *   window.graps.store           — EventTarget dengan property .state
 *   window.graps.setState(part)  — Object.assign + dispatch 'change'
 *
 * Listener: store.addEventListener('change', e => { e.detail.prev, e.detail.next })
 *
 * ponytail: plain object, bukan Proxy. Caller wajib pakai setState() supaya
 * event ke-fire. Mutation langsung ke store.state tidak akan dispatch.
 */
(function () {
  "use strict";
  window.graps = window.graps || {};

  const store = new EventTarget();
  store.state = {
    graph: null,        // {meta, nodes, edges, warnings}
    selectedNode: null, // node object (bukan id)
    hoveredNode: null,
    filter: { risk: null, dead: false }, // risk: null|'high'
    sidePanel: false,   // bool — apakah side panel terbuka
    openDirs: new Set(), // Set<string> — directory yang di-expand user
    aiHistory: [],       // array — conversation history session ini
    activePanel: null,   // null|'sidebar'|'sidepanel'|'ai' — mobile: panel terbuka
  };

  function setState(partial) {
    const prev = Object.assign({}, store.state);
    Object.assign(store.state, partial);
    store.dispatchEvent(new CustomEvent("change", {
      detail: { prev: prev, next: store.state, keys: Object.keys(partial) },
    }));
  }

  window.graps.store = store;
  window.graps.setState = setState;

  // ponytail: mobile orchestration — max 1 overlay panel at a time.
  // Desktop hanya tracking state. Mobile auto-close side panel saat switch.
  function setActivePanel(name) {
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    if (isMobile && name !== 'sidepanel' && store.state.sidePanel) {
      setState({ sidePanel: false, activePanel: name });
      return;
    }
    setState({ activePanel: name });
  }
  window.graps.setActivePanel = setActivePanel;

  // Wire filter pills di top-bar setelah DOM ready.
  function wireFilterPills() {
    const pills = document.querySelectorAll(".filter-pill[data-filter]");
    pills.forEach((pill) => {
      pill.addEventListener("click", () => {
        const kind = pill.dataset.filter; // 'high' | 'dead'
        const cur = store.state.filter;
        const next = Object.assign({}, cur);
        if (kind === "high") {
          next.risk = cur.risk === "high" ? null : "high";
        } else if (kind === "dead") {
          next.dead = !cur.dead;
        }
        setState({ filter: next });
      });
    });
    // Reflect ke kelas .active.
    store.addEventListener("change", () => {
      const f = store.state.filter;
      pills.forEach((p) => {
        const kind = p.dataset.filter;
        const active = (kind === "high" && f.risk === "high") ||
                       (kind === "dead" && f.dead);
        p.classList.toggle("active", active);
        p.setAttribute("aria-checked", active ? "true" : "false");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireFilterPills);
  } else {
    wireFilterPills();
  }
})();

/* =========================================================================
   graps — Application UI logic
   FEAT-0002 tree · 0003 workspace · 0004 AI · 0005 split · 0006 resize
   FEAT-0007 responsive · 0008/0009 hierarchy · 0010–0013 tabs
   FEAT-0014 settings · 0015 /scan command
   Vanilla JS, no framework, no build step.
   ========================================================================= */
'use strict';

/* --- State --------------------------------------------------------------- */
const state = {
  graph: null,
  settings: { ai_enrichment: true, panel_widths: {}, tabs: [] },
  tabs: [],               // [{id, type, title, entityId, preview}]
  activeTabId: null,
  expanded: new Set(),    // expanded tree node IDs
  panels: { dir: true, ai: true },
  widths: { dir: 280, ai: 320 },
  aiAvailable: false,
  pendingPreview: null,  // timer for single-vs-double click (FEAT-0013)
};

/* --- API ----------------------------------------------------------------- */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText} ${txt}`);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('json') ? res.json() : res.text();
}

/* --- DOM helpers --------------------------------------------------------- */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const iconSvg = (id) => `<svg class="icon"><use href="#${id}"/></svg>`;

/* --- Tree (FEAT-0008/0009) ----------------------------------------------- */
function buildTreeData(graph) {
  const filesByMod = {};
  const fnsByFile = {};
  for (const f of graph.nodes.files) {
    const mid = f.module_id || '__root__';
    (filesByMod[mid] ||= []).push(f);
  }
  for (const fn of graph.nodes.functions) {
    (fnsByFile[fn.file_id] ||= []).push(fn);
  }
  const mkFn = (fn) => ({
    type: 'function', id: fn.id, label: fn.name, data: fn, children: [],
  });
  const mkFile = (f) => ({
    type: 'file', id: f.id, label: f.path.split('/').pop(), data: f,
    children: (fnsByFile[f.id] || []).sort((a, b) =>
      (a.line_start || 0) - (b.line_start || 0)).map(mkFn),
  });
  const tree = [];
  for (const m of (graph.nodes.modules || [])) {
    tree.push({
      type: 'module', id: m.id, label: m.name || m.id, data: m,
      children: (filesByMod[m.id] || []).sort((a, b) =>
        a.path.localeCompare(b.path)).map(mkFile),
    });
  }
  // orphan files (no module)
  for (const f of (filesByMod['__root__'] || []).sort((a, b) =>
    a.path.localeCompare(b.path))) {
    tree.push(mkFile(f));
  }
  return tree;
}

function renderTree() {
  const c = $('#tree');
  if (!state.graph) { c.innerHTML = '<p class="empty-state">No project loaded.</p>'; return; }
  const data = buildTreeData(state.graph);
  if (!data.length) { c.innerHTML = '<p class="empty-state">No files found.</p>'; return; }
  c.innerHTML = '';
  c.setAttribute('role', 'tree');
  for (const node of data) c.append(renderNode(node, 0));
}

function renderNode(node, depth) {
  const expanded = state.expanded.has(node.id);
  const hasKids = node.children.length > 0;
  const icons = { module: 'i-module', file: 'i-file', function: 'i-fn' };
  // row
  const row = document.createElement('div');
  row.className = 'tree-row' + (expanded ? ' expanded' : '');
  row.dataset.type = node.type;
  row.dataset.id = node.id;
  row.tabIndex = 0;
  row.setAttribute('role', 'treeitem');
  row.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  row.style.paddingLeft = `${8 + depth * 14}px`;
  row.innerHTML =
    `<span class="tree-chevron${expanded ? ' expanded' : ''}${hasKids ? '' : ' leaf'}">` +
    (hasKids ? iconSvg('i-chevron') : '') + `</span>` +
    iconSvg(icons[node.type]) +
    `<span class="tree-label">${esc(node.label)}</span>`;
  // single vs double click (FEAT-0013)
  row.addEventListener('click', () => onNodeClick(node));
  row.addEventListener('dblclick', () => onNodeDblClick(node));
  row.addEventListener('keydown', (e) => onNodeKey(e, node));
  // children
  const li = document.createElement('li');
  li.className = 'tree-node';
  li.setAttribute('role', 'none');
  li.append(row);
  if (hasKids && expanded) {
    const ul = document.createElement('ul');
    ul.className = 'tree-children';
    ul.setAttribute('role', 'group');
    for (const ch of node.children) ul.append(renderNode(ch, depth + 1));
    li.append(ul);
  }
  return li;
}

/* --- Click contract (FEAT-0002) ------------------------------------------ */
function onNodeClick(node) {
  // FEAT-0013: single click reuses safe preview tab
  clearTimeout(state.pendingPreview);
  state.pendingPreview = setTimeout(() => {
    if (node.type === 'module') {
      toggleExpand(node);
      openTab(node.id, 'module', node.label, true);
    } else if (node.type === 'file') {
      toggleExpand(node);
      openTab(node.id, 'source', node.label, true);
    } else if (node.type === 'function') {
      // function click opens FLOW not source (FEAT-0011)
      openTab(node.id, 'flow', node.label, true);
    }
  }, 200);
}

function onNodeDblClick(node) {
  clearTimeout(state.pendingPreview);
  // double-click → pin tab (FEAT-0013)
  if (node.type === 'module') {
    toggleExpand(node);
    openTab(node.id, 'module', node.label, false);
  } else if (node.type === 'file') {
    toggleExpand(node);
    openTab(node.id, 'source', node.label, false);
  } else if (node.type === 'function') {
    openTab(node.id, 'flow', node.label, false);
  }
}

function onNodeKey(e, node) {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onNodeClick(node); }
  if (e.key === 'ArrowRight' && !state.expanded.has(node.id)) { toggleExpand(node); }
  if (e.key === 'ArrowLeft' && state.expanded.has(node.id)) { toggleExpand(node); }
}

function toggleExpand(node) {
  if (!node.children.length) return;
  if (state.expanded.has(node.id)) state.expanded.delete(node.id);
  else state.expanded.add(node.id);
  renderTree();
}

/* --- Tabs (FEAT-0010/0011/0012/0013) ------------------------------------- */
function openTab(entityId, type, title, preview = true) {
  // dedup by entity ID (FEAT-0013)
  let tab = state.tabs.find(t => t.entityId === entityId);
  if (tab) {
    if (!preview) tab.preview = false;  // pin if double-click
  } else {
    tab = { id: crypto.randomUUID(), entityId, type, title, preview };
    state.tabs.push(tab);
  }
  state.activeTabId = tab.id;
  renderTabs();
  renderTabContent(tab);
  persistTabs();
}

function closeTab(tabId) {
  const idx = state.tabs.findIndex(t => t.id === tabId);
  if (idx === -1) return;
  state.tabs.splice(idx, 1);
  if (state.activeTabId === tabId) {
    state.activeTabId = state.tabs[idx]?.id || state.tabs[idx - 1]?.id || null;
  }
  renderTabs();
  if (state.activeTabId) renderTabContent(state.tabs.find(t => t.id === state.activeTabId));
  else renderEmpty();
  persistTabs();
}

function activateTab(tabId) {
  state.activeTabId = tabId;
  renderTabs();
  const tab = state.tabs.find(t => t.id === tabId);
  if (tab) renderTabContent(tab);
}

function renderTabs() {
  const bar = $('#tab-bar');
  if (!state.tabs.length) {
    bar.innerHTML = '<span class="tab-empty">No tabs open</span>';
    return;
  }
  bar.innerHTML = '';
  for (const t of state.tabs) {
    const icons = { source: 'i-file', flow: 'i-sync', module: 'i-module' };
    const tab = document.createElement('div');
    tab.className = 'tab' +
      (t.id === state.activeTabId ? ' active' : '') +
      (t.preview ? ' tab-preview' : '');
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-selected', t.id === state.activeTabId ? 'true' : 'false');
    tab.tabIndex = 0;
    tab.innerHTML =
      iconSvg(icons[t.type]) +
      `<span class="tab-label">${esc(t.title)}</span>` +
      `<button class="tab-close" aria-label="Close tab">${iconSvg('i-close')}</button>`;
    tab.addEventListener('click', () => activateTab(t.id));
    tab.querySelector('.tab-close').addEventListener('click', (e) => {
      e.stopPropagation();
      closeTab(t.id);
    });
    bar.append(tab);
  }
}

async function renderTabContent(tab) {
  const c = $('#tab-content');
  c.innerHTML = '<p class="empty-state">Loading…</p>';
  try {
    if (tab.type === 'source') await renderSource(tab, c);
    else if (tab.type === 'flow') await renderFlow(tab, c);
    else if (tab.type === 'module') await renderModule(tab, c);
  } catch (err) {
    c.innerHTML = `<div class="workspace-empty"><p>${esc(err.message)}</p></div>`;
  }
}

/* --- Source view (FEAT-0010) -------------------------------------------- */
async function renderSource(tab, c) {
  // file_id is the entity; for function-level source, pass fn param
  const fn = tab.entityId.includes('::') ? tab.entityId.split('::')[1] : '';
  const fileId = tab.entityId.includes('::') ? tab.entityId.split('::')[0] : tab.entityId;
  const url = `/api/source?file=${encodeURIComponent(fileId)}` +
    (fn ? `&fn=${encodeURIComponent(fn)}` : '');
  const res = await api(url);
  // API returns {file, fn, source, language}
  const src = (res && res.source) ? res.source : String(res);
  const lines = String(src).split('\n');
  c.innerHTML = '<div class="source-view"><pre></pre></div>';
  const pre = c.querySelector('pre');
  for (let i = 0; i < lines.length; i++) {
    const div = document.createElement('div');
    div.className = 'source-line';
    div.textContent = lines[i];
    pre.append(div);
  }
}

/* --- Flow view (FEAT-0011) ----------------------------------------------- */
async function renderFlow(tab, c) {
  // flow ID = <file_id>#call_sequence
  const fnId = tab.entityId;
  const fileFn = fnId.split('::');
  const flowId = `${fileFn[0]}#call_sequence`;
  const flow = await api(`/api/flows/${encodeURIComponent(flowId)}`);
  const steps = flow.steps || [];
  c.innerHTML = '<div class="flow-view"></div>';
  const view = c.querySelector('.flow-view');
  if (!steps.length) {
    view.innerHTML = '<p class="empty-state">No flow steps found.</p>';
    return;
  }
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    const conf = s.confidence || 'resolved';
    const div = document.createElement('div');
    div.className = 'flow-step';
    div.dataset.confidence = conf;
    div.innerHTML =
      (i > 0 ? '<span class="arrow">→</span>' : '<span class="arrow">●</span>') +
      `<span class="fn-name">${esc(s.callee || s.name || '?')}</span>` +
      `<span class="dim">${esc(conf)}</span>`;
    view.append(div);
  }
}

/* --- Module overview (FEAT-0012) ----------------------------------------- */
async function renderModule(tab, c) {
  const mod = await api(`/api/modules/${encodeURIComponent(tab.entityId)}`);
  c.innerHTML = '<div class="module-view"></div>';
  const v = c.querySelector('.module-view');
  const sections = [
    ['Path', [mod.file_id || mod.id]],
    ['Language', [mod.language || '—']],
    ['Boundary', [mod.confidence || 'unknown']],
    ['Members', (mod.member_files || []).map(f => typeof f === 'string' ? f : (f.path || f.id || String(f)))],
    ['Functions', (mod.member_functions || []).map(f => typeof f === 'string' ? f : (f.name || f.id || String(f)))],
    ['Dependencies', (mod.dependency_ids || mod.dependencies || []).map(d => typeof d === 'string' ? d : (d.id || JSON.stringify(d)))],
    ['Diagnostics', (mod.diagnostics || []).map(d => typeof d === 'string' ? d : JSON.stringify(d))],
  ];
  // AI enrichment (optional, FEAT-0012/0014)
  if (mod.ai_name || mod.ai_responsibility) {
    sections.push(['AI Name', [mod.ai_name || '—']]);
    sections.push(['AI Responsibility', [mod.ai_responsibility || '—']]);
    sections.push(['AI Capabilities', (mod.ai_capabilities || [])]);
  }
  for (const [title, items] of sections) {
    if (!items.length) continue;
    const sec = document.createElement('div');
    sec.className = 'module-section';
    sec.innerHTML = `<h3>${title}</h3><ul>${items.map(i => `<li>${esc(String(i))}</li>`).join('')}</ul>`;
    v.append(sec);
  }
}

function renderEmpty() {
  $('#tab-content').innerHTML =
    '<div class="workspace-empty">' + iconSvg('i-module') +
    '<p>Select a file, function, or module from the explorer.</p></div>';
}

/* --- Panel toggle (FEAT-0005) -------------------------------------------- */
function togglePanel(name) {
  state.panels[name] = !state.panels[name];
  const panel = $(name === 'dir' ? '#dir-panel' : '#ai-panel');
  panel.dataset.open = state.panels[name];
  // update split buttons
  const btn = $(`.split-btn[data-panel="${name}"]`);
  if (btn) {
    btn.setAttribute('aria-pressed', state.panels[name]);
    const img = btn.querySelector('.split-img');
    img.dataset.state = state.panels[name] ? 'select' : 'unselect';
    img.src = `/icon/split-horizontal-right-${img.dataset.state}.svg`;
  }
  // mobile backdrop
  if (isMobile() && state.panels[name]) showBackdrop();
  else hideBackdrop();
  persistSettings();
}

/* --- Resizers (FEAT-0006) ------------------------------------------------ */
function initResizers() {
  for (const [id, side, name] of [
    ['resizer-left', 'left', 'dir'],
    ['resizer-right', 'right', 'ai'],
  ]) {
    const r = $('#' + id);
    if (!r) continue;
    let dragging = false, startX = 0, startW = 0;
    r.addEventListener('pointerdown', (e) => {
      dragging = true; startX = e.clientX; startW = state.widths[name];
      r.classList.add('dragging'); r.setPointerCapture(e.pointerId);
    });
    r.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const delta = side === 'left' ? e.clientX - startX : startX - e.clientX;
      const w = Math.round(Math.max(200, Math.min(600, startW + delta)));
      state.widths[name] = w;
      applyWidth(name);
    });
    r.addEventListener('pointerup', () => {
      dragging = false; r.classList.remove('dragging'); persistSettings();
    });
    r.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const dir = (side === 'left' ? 1 : -1) * (e.key === 'ArrowRight' ? 10 : -10);
        state.widths[name] = Math.max(200, Math.min(600, state.widths[name] + dir));
        applyWidth(name);
      }
    });
  }
}

function applyWidth(name) {
  const panel = $(name === 'dir' ? '#dir-panel' : '#ai-panel');
  if (isMobile()) return;
  panel.style.width = state.widths[name] + 'px';
}

/* --- AI panel (FEAT-0004/0014/0015) -------------------------------------- */
// ponytail: checkAIStatus removed — enrich UI (status dot/text) deleted in BUG-0003.
// aiAvailable now set from loadSettings() to avoid duplicate /api/settings fetch.

async function sendAI(msg) {
  const msgs = $('#ai-messages');
  appendMsg(msgs, 'user', msg);
  // /scan command (FEAT-0015)
  if (msg.startsWith('/scan')) {
    appendMsg(msgs, 'assistant', 'Scanning…');
    try {
      const res = await api('/api/scan', { method: 'POST', body: JSON.stringify({ mode: msg }) });
      appendMsg(msgs, 'assistant',
        `Scan complete. Files: ${res.scan?.file_count ?? '?'}, ` +
        `Functions: ${res.scan?.function_count ?? '?'}`);
      // refresh graph
      state.graph = await api('/api/graph');
      renderTree();
    } catch (err) {
      appendMsg(msgs, 'error', `Scan failed: ${err.message}`);
    }
    return;
  }
  // regular chat
  try {
    const res = await api('/api/ai/chat', {
      method: 'POST', body: JSON.stringify({ message: msg }),
    });
    appendMsg(msgs, 'assistant', res.reply || res.message || '(empty)');
  } catch (err) {
    // no blocking modal (FEAT-0004)
    appendMsg(msgs, 'error', err.message);
  }
}

function appendMsg(container, cls, text) {
  const d = document.createElement('div');
  d.className = `ai-msg ${cls}`;
  d.textContent = text;
  container.append(d);
  container.scrollTop = container.scrollHeight;
}

/* --- Settings persistence (FEAT-0006/0013/0014) ------------------------- */
async function loadSettings() {
  try {
    const s = await api('/api/settings');
    state.settings = s;
    state.aiAvailable = s.ai_enrichment !== false;
    if (s.panel_widths) {
      state.widths.dir = clampW(s.panel_widths.dir) || 280;
      state.widths.ai = clampW(s.panel_widths.ai) || 320;
    }
    applyWidth('dir'); applyWidth('ai');
    // restore tabs (FEAT-0013)
    if (s.tabs && s.tabs.length) {
      for (const t of s.tabs) {
        try {
          state.tabs.push({ ...t, preview: false });
        } catch { /* fail safely on deleted entities */ }
      }
      if (state.tabs.length) {
        state.activeTabId = state.tabs[0].id;
        renderTabs();
        renderTabContent(state.tabs[0]);
      }
    }
  } catch { /* safe fallback — defaults */ }
}

async function persistSettings() {
  try {
    await api('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({
        panel_widths: state.widths,
        ai_enrichment: state.aiAvailable,
      }),
    });
  } catch { /* non-blocking */ }
}

async function persistTabs() {
  try {
    await api('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({
        tabs: state.tabs.map(t => ({
          entityId: t.entityId, type: t.type, title: t.title, id: t.id,
        })),
      }),
    });
  } catch { /* non-blocking */ }
}

/* --- Responsive (FEAT-0007) ---------------------------------------------- */
function isMobile() {
  return window.innerWidth <= 1024;
}

function showBackdrop() {
  const b = $('#backdrop');
  b.hidden = false;
  b.onclick = () => {
    if (state.panels.dir) togglePanel('dir');
    if (state.panels.ai) togglePanel('ai');
  };
}
function hideBackdrop() { $('#backdrop').hidden = true; }

/* --- Utilities ------------------------------------------------------------ */
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
function clampW(w) {
  w = Number(w);
  return (w >= 200 && w <= 600) ? w : null;
}

/* --- Init ----------------------------------------------------------------- */
async function init() {
  // load settings first (FEAT-0006 restore widths, FEAT-0013 restore tabs)
  await loadSettings();

  // load graph
  try {
    state.graph = await api('/api/graph');
    renderTree();
  } catch (err) {
    $('#tree').innerHTML = `<p class="empty-state">Failed to load: ${esc(err.message)}</p>`;
  }

  // AI status — set from loadSettings() (enrich UI removed in BUG-0003)

  // split toggle buttons (sole panel toggle mechanism post-BUG-0003)
  $$('.split-btn').forEach(btn => {
    btn.addEventListener('click', () => togglePanel(btn.dataset.panel));
  });

  // resizers
  initResizers();

  // AI input
  const input = $('#ai-input');
  const send = $('#ai-send');
  const submit = () => {
    const v = input.value.trim();
    if (!v) return;
    input.value = '';
    sendAI(v);
  };
  send.addEventListener('click', submit);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });

  // responsive: re-check on resize
  window.addEventListener('resize', () => {
    if (!isMobile()) { applyWidth('dir'); applyWidth('ai'); hideBackdrop(); }
  });
}

document.addEventListener('DOMContentLoaded', init);

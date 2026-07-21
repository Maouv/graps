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
// ponytail: crypto.randomUUID needs secure context (HTTPS/localhost). Fallback for LAN HTTP.
const uid = () => crypto.randomUUID?.() ?? (Date.now().toString(36) + Math.random().toString(36).slice(2));

/* --- Tree (FEAT-0008/0009) ----------------------------------------------- */
// ponytail: Option B — folder/file/function trie from file paths. No module
// nodes (scanner makes 1 module per file → would add redundant wrapper per file).
// Module-overview tabs (FEAT-0012) become unreachable from tree; re-wire later.
function buildTreeData(graph) {
  const fnsByFile = {};
  for (const fn of graph.nodes.functions) (fnsByFile[fn.file_id] ||= []).push(fn);
  const mkFn = (fn) => ({
    type: 'function', id: fn.id, label: fn.name, data: fn, children: [],
  });
  const mkFile = (f) => ({
    type: 'file', id: f.id, label: f.path.split('/').pop(), data: f,
    children: (fnsByFile[f.id] || []).sort((a, b) =>
      (a.line_start || 0) - (b.line_start || 0)).map(mkFn),
  });
  // folder trie from file paths (last segment = filename)
  const root = { children: [] };
  for (const f of graph.nodes.files) {
    if (!f.path) continue;  // guard: skip empty paths
    const segs = f.path.split('/');
    let cur = root;
    for (let i = 0; i < segs.length - 1; i++) {
      let folder = cur.children.find(c => c.type === 'folder' && c.label === segs[i]);
      if (!folder) {
        folder = { type: 'folder', id: segs.slice(0, i + 1).join('/'), label: segs[i], children: [] };
        cur.children.push(folder);
      }
      cur = folder;
    }
    cur.children.push(mkFile(f));
  }
  // sort: folders first, then files; alphabetical within group
  const order = { folder: 0, file: 1, function: 2 };
  (function sort(nodes) {
    nodes.sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9)
      || a.label.localeCompare(b.label));
    for (const n of nodes) if (n.children?.length) sort(n.children);
  })(root.children);
  return root.children;
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
  const icons = { folder: null, module: 'i-module', file: 'i-file', function: 'i-fn' };
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
 (icons[node.type] ? iconSvg(icons[node.type]) : '') +
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
  // folders: expand/collapse immediately, no tab (no single-vs-double-click delay)
  if (node.type === 'folder') { toggleExpand(node); return; }
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
    tab = { id: uid(), entityId, type, title, preview };
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
function humanize(name) {
  return String(name || '')
    .replace(/[._]/g, ' ')
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

// Confidence is a structural fact, not a failure: most "unresolved" calls are
// builtin/stdlib/external-library calls that the deterministic resolver can
// never trace without type inference (DEC-0005). Label by reason so it reads
// as "outside project scope", not "broken".
function confLabel(step) {
  const conf = step.confidence || 'resolved';
  if (conf === 'resolved') return 'resolved';
  if (conf === 'partial') return 'partial';
  if (step.unresolved_reason === 'method_not_in_class') return 'not in class';
  // attribute_call_unresolved / unqualified_name_not_in_scope
  return 'external / builtin';
}

async function renderFlow(tab, c) {
  // flow ID = <full_fn_id>#call_sequence
  const flowId = `${tab.entityId}#call_sequence`;
  const flow = await api(`/api/flows/${encodeURIComponent(flowId)}`);
  const steps = flow.steps || [];
  c.innerHTML = '<div class="flow-view"></div>';
  const view = c.querySelector('.flow-view');
  if (!steps.length) {
    view.innerHTML = '<p class="empty-state">No flow steps found.</p>';
    return;
  }

  // header
  const title = document.createElement('div');
  title.className = 'flow-title';
  title.textContent = `${tab.title}()`;
  view.append(title);

  // goal (heuristic, structural — not AI-generated)
  const goal = document.createElement('div');
  goal.className = 'flow-goal';
  goal.innerHTML = `<h3>Goal</h3><p>${esc(humanize(tab.title))}</p>`;
  view.append(goal);

  // sequence
  const seq = document.createElement('div');
  seq.className = 'flow-sequence';
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    const conf = s.confidence || 'resolved';
    if (i > 0) {
      const arrow = document.createElement('div');
      arrow.className = 'flow-arrow';
      arrow.textContent = '↓';
      seq.append(arrow);
    }
    const div = document.createElement('div');
    div.className = 'flow-step';
    div.dataset.confidence = conf;
    div.innerHTML =
      `<span class="fn-name">${esc(s.name || '?')}</span>` +
      `<span class="dim">${esc(confLabel(s))}</span>`;
    seq.append(div);
  }
  view.append(seq);

  // functions — distinct resolved call targets
  const fns = new Map();
  const files = new Set();
  for (const s of steps) {
    if (!s.target) continue;
    const [file, qname] = s.target.split('::');
    if (file) files.add(file);
    if (qname) fns.set(s.target, qname.split('.').pop());
  }
  if (fns.size) {
    const sec = document.createElement('div');
    sec.className = 'flow-section';
    sec.innerHTML = `<h3>Functions</h3><ul>${
      [...fns.values()].map((n) => `<li>✓ ${esc(n)}()</li>`).join('')
    }</ul>`;
    view.append(sec);
  }

  // files — distinct files referenced by resolved targets
  if (files.size) {
    const sec = document.createElement('div');
    sec.className = 'flow-section';
    sec.innerHTML = `<h3>Files</h3><ul>${
      [...files].map((f) => `<li>${esc(f)}</li>`).join('')
    }</ul>`;
    view.append(sec);
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
      const w = Math.round(Math.max(80, Math.min(600, startW + delta)));
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
        state.widths[name] = Math.max(80, Math.min(600, state.widths[name] + dir));
        applyWidth(name);
      }
    });
  }
}

function applyWidth(name) {
  const panel = $(name === 'dir' ? '#dir-panel' : '#ai-panel');
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
      state.widths.dir = clampW(s.panel_widths.dir) || state.widths.dir;
      state.widths.ai = clampW(s.panel_widths.ai) || state.widths.ai;
    }
    applyWidth('dir'); applyWidth('ai');
    // BUG-0006: tabs NOT restored from settings — clean slate on page load.
    // persistTabs() still writes for future session-restore feature; see backlog.
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

function showBackdrop() { /* ponytail: backdrop removed in BUG-0008 — 3-column on all devices */ }
function hideBackdrop() { /* ponytail: backdrop removed in BUG-0008 */ }

/* --- Utilities ------------------------------------------------------------ */
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
function clampW(w) {
  w = Number(w);
  return (w >= 80 && w <= 600) ? w : null;
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
    applyWidth('dir'); applyWidth('ai');
  });
}

document.addEventListener('DOMContentLoaded', init);

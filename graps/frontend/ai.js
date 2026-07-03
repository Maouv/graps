/* graps — AI chat bar (Phase D2).
 *
 * Public API: window.graps.ai
 *   .init()       — boot AI bar
 *   .injectTag(n) — inject @tag from side panel
 */
(function () {
  "use strict";
  window.graps = window.graps || {};
  const store = window.graps.store;
  const setState = window.graps.setState;
  const toast = window.graps.toast;

  let inputEl, messagesEl, tagsEl;

  function init() {
    inputEl = document.getElementById("ai-input");
    messagesEl = document.getElementById("ai-messages");
    tagsEl = document.getElementById("ai-tags");

    document.getElementById("ai-send")?.addEventListener("click", sendMessage);
    // E1: chevron toggle AI bar
    document.getElementById("ai-chevron")?.addEventListener("click", () => {
      const cur = store.state.activePanel;
      if (cur === 'ai') window.graps.setActivePanel(null);
      else window.graps.setActivePanel('ai');
    });
    inputEl?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // E1: mobile — tap/focus AI input → set active panel
    inputEl?.addEventListener("focus", () => {
      if (window.graps.setActivePanel) window.graps.setActivePanel('ai');
    });
    document.getElementById("ai-input-row")?.addEventListener("click", () => {
      if (window.graps.setActivePanel) window.graps.setActivePanel('ai');
    });

    store.addEventListener("change", (e) => {
      if (!e.detail.keys.includes("selectedNode")) return;
      const node = store.state.selectedNode;
      if (node) setImplicitTag(node.id);
    });

    // E1: mobile activePanel listener — expand/collapse AI bar
    store.addEventListener("change", (e) => {
      if (!e.detail.keys.includes("activePanel")) return;
      const bar = document.getElementById("ai-bar");
      if (!bar) return;
      const isMobile = window.matchMedia("(max-width: 768px)").matches;
      if (store.state.activePanel === "ai") {
        bar.classList.add("open");
        if (isMobile) inputEl?.focus();
      } else {
        bar.classList.remove("open");
      }
    });

    inputEl?.addEventListener("input", (e) => {
      if (e.target.value.trim() === "/new") {
        e.target.value = "";
        clearConversation();
      }
    });
  }

  function setImplicitTag(nodeId) {
    if (inputEl) inputEl.placeholder = "Ask about @" + nodeId + "...";
    renderTags([nodeId]);
  }

  function renderTags(tags) {
    if (!tagsEl) return;
    tagsEl.innerHTML = tags.map((t) =>
      '<span class="ai-tag">@' + t + "</span>"
    ).join("");
  }

  async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message || message.startsWith("/")) return;

    const selectedNode = store.state.selectedNode;
    const tagged = selectedNode ? [selectedNode.id] : [];
    const manualTags = (message.match(/@[\w./]+/g) || []).map((t) => t.slice(1));
    const allTagged = [...new Set([...tagged, ...manualTags])];

    appendMessage("user", message);
    inputEl.value = "";

    const history = store.state.aiHistory || [];

    try {
      const res = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, tagged: allTagged, history }),
      });
      const data = await res.json();

      if (data.error_type) {
        appendMessage("error", data.detail || "AI error");
        return;
      }
      appendMessage("assistant", data.reply);
      setState({
        aiHistory: [
          ...history,
          { role: "user", content: message },
          { role: "assistant", content: data.reply },
        ],
      });
      if (data.warnings && data.warnings.length) {
        data.warnings.forEach((w) => {
          if (toast) toast(w, "warning");
        });
      }
    } catch (err) {
      appendMessage("error", "Cannot reach server");
    }
  }

  function appendMessage(role, content) {
    if (!messagesEl) return;
    const el = document.createElement("div");
    el.className = "ai-message ai-" + role;
    el.textContent = content;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function clearConversation() {
    setState({ aiHistory: [] });
    if (messagesEl) messagesEl.innerHTML = "";
    if (toast) toast("New session started", "info");
  }

  function injectTag(nodeId) {
    if (inputEl) {
      const cur = inputEl.value;
      if (!cur.includes("@" + nodeId)) {
        inputEl.value = cur + " @" + nodeId;
      }
      inputEl.focus();
    }
  }

  window.graps.ai = { init: init, injectTag: injectTag };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

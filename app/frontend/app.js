/* AI Agent frontend — chat + direct tool invocation. Vanilla JS, no deps. */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const api = (path, opts) => fetch(path, opts).then((r) => r.json());

  const state = {
    messages: [],           // {role, content}
    tools: {},              // name -> tool meta
    sending: false,
    conversationId: null,   // active conversation (null until first message)
    models: {},             // provider -> remembered model name
  };

  const EMPTY_STATE_HTML = `
    <div class="empty-state">
      <div class="empty-emoji">💬</div>
      <h2>How can I help?</h2>
      <p>I can search the web, check weather &amp; air quality, convert units and
         currencies, manage notes, fact-check claims, summarize, translate and more.</p>
      <div class="suggestions">
        <button class="chip">What's the weather in Tokyo?</button>
        <button class="chip">Convert 100 USD to INR</button>
        <button class="chip">What happened on 21 July 1969?</button>
        <button class="chip">Summarize the latest AI news</button>
      </div>
    </div>`;

  // ------------------------- Status + tools -------------------------
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      const pill = $("#status-pill");
      if (s.llm_configured) {
        pill.textContent = `${s.provider} · ${s.model}`;
        pill.className = "pill pill-ok";
      } else {
        pill.textContent = "no API key — tools only";
        pill.className = "pill pill-warn";
      }
    } catch {
      $("#status-pill").textContent = "offline";
    }
  }

  // ------------------------- LLM settings -------------------------
  async function loadSettings() {
    try {
      const s = await api("/api/settings");
      state.models = s.models || {};
      $("#provider-select").value = s.provider;
      $("#model-input").value = s.model || "";
    } catch { /* non-fatal */ }
  }

  async function applySettings(body) {
    try {
      await api("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      loadStatus();
    } catch (e) { console.error("settings update failed", e); }
  }

  function onProviderChange() {
    const provider = $("#provider-select").value;
    // Prefill the model box with that provider's remembered model.
    const model = (state.models && state.models[provider]) || "";
    $("#model-input").value = model;
    applySettings({ provider, model: model || undefined });
  }

  function onModelChange() {
    const provider = $("#provider-select").value;
    const model = $("#model-input").value.trim();
    if (!model) return;
    if (state.models) state.models[provider] = model;
    applySettings({ provider, model });
  }

  async function loadTools() {
    const data = await api("/api/tools");
    const list = $("#tool-list");
    list.innerHTML = "";
    const badge = $("#tools-count");
    if (badge) badge.textContent = data.count ? `(${data.count})` : "";
    Object.entries(data.categories).forEach(([category, tools]) => {
      const wrap = document.createElement("div");
      wrap.className = "tool-category";
      const h = document.createElement("h3");
      h.textContent = category;
      wrap.appendChild(h);
      tools.forEach((t) => {
        state.tools[t.name] = t;
        const btn = document.createElement("button");
        btn.className = "tool-item";
        btn.dataset.name = t.name;
        btn.dataset.search = (t.name + " " + t.description).toLowerCase();
        btn.innerHTML = `<span class="t-name">${t.name}</span>
                         <span class="t-desc">${t.description}</span>`;
        btn.addEventListener("click", () => openTool(t.name));
        wrap.appendChild(btn);
      });
      list.appendChild(wrap);
    });
  }

  function filterTools(q) {
    q = q.toLowerCase().trim();
    document.querySelectorAll(".tool-item").forEach((el) => {
      const match = !q || el.dataset.search.includes(q);
      el.style.display = match ? "" : "none";
    });
    document.querySelectorAll(".tool-category").forEach((cat) => {
      const anyVisible = [...cat.querySelectorAll(".tool-item")]
        .some((el) => el.style.display !== "none");
      cat.style.display = anyVisible ? "" : "none";
    });
  }

  // ------------------------- Conversations -------------------------
  async function loadConversations() {
    try {
      const data = await api("/api/conversations");
      renderConversations(data.conversations || []);
    } catch { /* non-fatal */ }
  }

  function renderConversations(convs) {
    const list = $("#conv-list");
    list.innerHTML = "";
    if (!convs.length) {
      list.innerHTML = '<div class="conv-empty">No saved chats yet.</div>';
      return;
    }
    convs.forEach((c) => {
      const item = document.createElement("div");
      item.className = "conv-item" + (c.id === state.conversationId ? " active" : "");
      item.dataset.id = c.id;
      const title = document.createElement("span");
      title.className = "c-title";
      title.textContent = c.title || "New chat";
      const del = document.createElement("button");
      del.className = "c-del";
      del.title = "Delete chat";
      del.textContent = "✕";
      item.appendChild(title);
      item.appendChild(del);
      item.addEventListener("click", (e) => {
        if (e.target === del) return;
        openConversation(c.id);
      });
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteConversation(c.id);
      });
      list.appendChild(item);
    });
  }

  async function openConversation(id) {
    try {
      const data = await api("/api/conversations/" + id);
      if (!data.ok) return;
      state.conversationId = id;
      state.messages = (data.messages || []).map((m) => ({ role: m.role, content: m.content }));
      renderLoadedMessages(state.messages);
      showView("chat");
      $("#active-title").textContent = "Chat";
      $("#active-sub").textContent = data.conversation.title || "";
      markActiveConversation();
      closeSidebar();
    } catch { /* ignore */ }
  }

  function renderLoadedMessages(messages) {
    const box = $("#messages");
    box.innerHTML = "";
    if (!messages.length) { box.innerHTML = EMPTY_STATE_HTML; bindSuggestions(); return; }
    messages.forEach((m) => addMessage(m.role, m.content));
  }

  function markActiveConversation() {
    document.querySelectorAll(".conv-item").forEach((el) => {
      el.classList.toggle("active", Number(el.dataset.id) === state.conversationId);
    });
  }

  async function deleteConversation(id) {
    try {
      await fetch("/api/conversations/" + id, { method: "DELETE" });
    } catch { /* ignore */ }
    if (id === state.conversationId) newChat();
    loadConversations();
  }

  function newChat() {
    state.conversationId = null;
    state.messages = [];
    $("#messages").innerHTML = EMPTY_STATE_HTML;
    bindSuggestions();
    showView("chat");
    $("#active-title").textContent = "Chat";
    $("#active-sub").textContent = "Ask anything, or run a tool directly";
    markActiveConversation();
    closeSidebar();
  }

  // Lazily create a conversation the first time the user sends a message.
  async function ensureConversation(firstText) {
    if (state.conversationId) return state.conversationId;
    const data = await api("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: firstText.slice(0, 60) }),
    });
    state.conversationId = data.conversation.id;
    return state.conversationId;
  }

  // ------------------------- Chat -------------------------
  function showView(which) {
    $("#chat-view").classList.toggle("active", which === "chat");
    $("#tool-view").classList.toggle("active", which === "tool");
  }

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  }

  // Minimal markdown: code fences, inline code, bold, and links.
  function renderMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/```([\s\S]*?)```/g, (_, c) => `<pre>${c.trim()}</pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return html;
  }

  function addMessage(role, content, trace) {
    // Clear empty state on first message.
    const empty = $("#messages .empty-state");
    if (empty) empty.remove();

    const el = document.createElement("div");
    el.className = `msg ${role}`;
    const traceHtml = (trace && trace.length)
      ? `<div class="tools-trace">${trace.map((t) =>
          `<span class="trace-chip ${t.ok ? "ok" : "err"}">🔧 ${t.tool}</span>`).join("")}</div>`
      : "";
    el.innerHTML = `
      <div class="avatar">${role === "user" ? "🧑" : "✦"}</div>
      <div class="bubble-wrap">
        <div class="role">${role === "user" ? "You" : "Agent"}</div>
        <div class="bubble">${renderMarkdown(content)}</div>
        ${traceHtml}
      </div>`;
    $("#messages").appendChild(el);
    el.scrollIntoView({ behavior: "smooth", block: "end" });
    return el;
  }

  function scrollBottom() {
    const m = $("#messages");
    m.scrollTop = m.scrollHeight;
  }

  // Build an empty assistant message that we fill in as the stream arrives.
  function createStreamingAssistant() {
    const empty = $("#messages .empty-state");
    if (empty) empty.remove();

    const el = document.createElement("div");
    el.className = "msg assistant";
    el.innerHTML = `
      <div class="avatar">✦</div>
      <div class="bubble-wrap">
        <div class="role">Agent</div>
        <div class="tools-trace" style="display:none"></div>
        <div class="bubble streaming"><span class="typing"><span></span><span></span><span></span></span></div>
        <div class="file-actions-wrap"></div>
      </div>`;
    $("#messages").appendChild(el);
    scrollBottom();
    return {
      bubble: el.querySelector(".bubble"),
      traceEl: el.querySelector(".tools-trace"),
      filesEl: el.querySelector(".file-actions-wrap"),
      stopCursor: () => el.querySelector(".bubble").classList.remove("streaming"),
    };
  }

  // ------------------------- File actions -------------------------
  const fileName = (p) => (p || "").split(/[\\/]/).pop();

  async function osOpen(path, reveal, btn) {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Opening…";
    try {
      const res = await api("/api/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, reveal }),
      });
      btn.textContent = res.ok ? original : "Failed";
      if (!res.ok) console.error("open failed:", res.error);
    } catch (e) {
      btn.textContent = "Failed";
      console.error(e);
    } finally {
      setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 1400);
    }
  }

  function mkFileBtn(label, path, reveal) {
    const b = document.createElement("button");
    b.className = "file-btn";
    b.textContent = label;
    b.addEventListener("click", () => osOpen(path, reveal, b));
    return b;
  }

  // Render a "saved file" row with Open file / Open directory buttons.
  function addFileActions(container, path) {
    if (!container || !path) return;
    if (container.querySelector(`[data-path="${CSS.escape(path)}"]`)) return;
    const row = document.createElement("div");
    row.className = "file-actions";
    row.dataset.path = path;
    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = "📄 " + fileName(path);
    name.title = path;
    row.append(
      name,
      mkFileBtn("Open file", path, false),
      mkFileBtn("Open directory", path, true),
    );
    container.appendChild(row);
  }

  // A tool result may carry a produced file path (save_research -> data.path,
  // resize_image -> data.output).
  function extractFilePath(result) {
    const d = (result && result.data) || {};
    return d.path || d.output || null;
  }

  // ------------------------- File upload -------------------------
  async function uploadFile(file) {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch("/api/upload", { method: "POST", body: fd });
    return resp.json();
  }

  function isFilePathParam(key) {
    const k = key.toLowerCase();
    return k === "path" || k === "file_path" || k.endsWith("_path") ||
           k.includes("image") || k === "filepath";
  }

  // An Upload button that uploads a chosen file and fills `input` with its path.
  function makeUploadButton(input) {
    const wrap = document.createElement("span");
    wrap.className = "upload-wrap";
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.style.display = "none";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "upload-btn";
    btn.textContent = "⤴ Upload";
    btn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      const f = fileInput.files[0];
      if (!f) return;
      const original = btn.textContent;
      btn.textContent = "Uploading…";
      btn.disabled = true;
      try {
        const res = await uploadFile(f);
        if (res.ok) {
          input.value = res.path;
          btn.textContent = "✓ " + res.filename.slice(0, 18);
        } else {
          btn.textContent = "Failed";
          console.error(res.error);
        }
      } catch (e) {
        btn.textContent = "Failed";
        console.error(e);
      } finally {
        fileInput.value = "";
        setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 2200);
      }
    });
    wrap.append(btn, fileInput);
    return wrap;
  }

  function addTraceChip(traceEl, tool) {
    traceEl.style.display = "flex";
    const chip = document.createElement("span");
    chip.className = "trace-chip pending";
    chip.dataset.tool = tool;
    chip.textContent = "⏳ " + tool;
    traceEl.appendChild(chip);
    return chip;
  }

  function setChipState(chip, ok) {
    chip.classList.remove("pending");
    chip.classList.add(ok ? "ok" : "err");
    chip.textContent = (ok ? "🔧 " : "⚠️ ") + chip.dataset.tool;
  }

  async function sendMessage(text) {
    if (!text.trim() || state.sending) return;
    state.sending = true;
    $("#send-btn").disabled = true;

    addMessage("user", text);
    state.messages.push({ role: "user", content: text });

    let convId = null;
    try {
      convId = await ensureConversation(text);
    } catch { /* persistence is best-effort; continue without it */ }

    const { bubble, traceEl, filesEl, stopCursor } = createStreamingAssistant();
    const pendingChips = [];
    const trace = [];
    let full = "";
    let firstToken = true;

    const render = () => {
      if (firstToken) { bubble.innerHTML = ""; firstToken = false; }
      bubble.innerHTML = renderMarkdown(full) +
        '<span class="stream-caret">▍</span>';
      scrollBottom();
    };

    try {
      const resp = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: state.messages, conversation_id: convId }),
      });
      if (!resp.ok || !resp.body) throw new Error("HTTP " + resp.status);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 2);
          if (!line.startsWith("data:")) continue;
          let evt;
          try { evt = JSON.parse(line.slice(5).trim()); } catch { continue; }

          if (evt.type === "token") {
            full += evt.text;
            render();
          } else if (evt.type === "tool_call") {
            pendingChips.push(addTraceChip(traceEl, evt.tool));
            scrollBottom();
          } else if (evt.type === "tool_result") {
            const chip = pendingChips.shift();
            if (chip) setChipState(chip, evt.ok);
            trace.push({ tool: evt.tool, ok: evt.ok });
            if (evt.file) { addFileActions(filesEl, evt.file); scrollBottom(); }
          } else if (evt.type === "error") {
            full += (full ? "\n\n" : "") + "⚠️ " + evt.message;
            render();
          }
        }
      }
    } catch (e) {
      full = full || ("⚠️ Streaming failed: " + e.message);
    } finally {
      stopCursor();
      bubble.innerHTML = full ? renderMarkdown(full) : "(no response)";
      state.messages.push({ role: "assistant", content: full });
      state.sending = false;
      $("#send-btn").disabled = false;
      scrollBottom();
      loadConversations();  // refresh titles/ordering in the sidebar
    }
  }

  // ------------------------- Tool panel -------------------------
  function openTool(name) {
    const tool = state.tools[name];
    if (!tool) return;
    $("#tool-panel-title").textContent = name;
    $("#tool-panel-desc").textContent = tool.description;
    $("#active-title").textContent = "Tool · " + name;
    $("#active-sub").textContent = "Run this tool directly with custom inputs";

    const form = $("#tool-form");
    form.innerHTML = "";
    const props = (tool.parameters && tool.parameters.properties) || {};
    const required = (tool.parameters && tool.parameters.required) || [];
    Object.entries(props).forEach(([key, schema]) => {
      const field = document.createElement("div");
      field.className = "field";
      const label = document.createElement("label");
      label.textContent = key + (required.includes(key) ? " *" : "") +
        (schema.description ? ` — ${schema.description}` : "");
      field.appendChild(label);

      let input;
      if (schema.enum) {
        input = document.createElement("select");
        schema.enum.forEach((opt) => {
          const o = document.createElement("option");
          o.value = o.textContent = opt;
          input.appendChild(o);
        });
      } else if (schema.type === "integer" || schema.type === "number") {
        input = document.createElement("input");
        input.type = "number";
        if (schema.type === "number") input.step = "any";
      } else {
        input = document.createElement("input");
        input.type = "text";
      }
      input.dataset.key = key;
      input.dataset.type = schema.type || "string";

      // For file-path parameters, add an Upload button that fills the field
      // with the uploaded file's server-side path.
      if (isFilePathParam(key)) {
        const row = document.createElement("div");
        row.className = "input-with-upload";
        row.appendChild(input);
        row.appendChild(makeUploadButton(input, key));
        field.appendChild(row);
      } else {
        field.appendChild(input);
      }
      form.appendChild(field);
    });
    if (!Object.keys(props).length) {
      form.innerHTML = '<p class="muted">This tool takes no parameters.</p>';
    }
    $("#tool-result").hidden = true;
    $("#tool-file-actions").innerHTML = "";
    showView("tool");
    closeSidebar();
  }

  async function runTool() {
    const title = $("#tool-panel-title").textContent;
    const args = {};
    document.querySelectorAll("#tool-form [data-key]").forEach((input) => {
      let val = input.value;
      if (val === "") return;
      if (input.dataset.type === "integer") val = parseInt(val, 10);
      else if (input.dataset.type === "number") val = parseFloat(val);
      args[input.dataset.key] = val;
    });

    const out = $("#tool-result");
    const actions = $("#tool-file-actions");
    actions.innerHTML = "";
    out.hidden = false;
    out.textContent = "Running…";
    try {
      const res = await api("/api/tool/" + encodeURIComponent(title), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arguments: args }),
      });
      out.textContent = JSON.stringify(res, null, 2);
      const path = extractFilePath(res);
      if (path) addFileActions(actions, path);
    } catch (e) {
      out.textContent = "Error: " + e.message;
    }
  }

  // ------------------------- Sidebar -------------------------
  // On desktop the sidebar is a grid column, so we collapse the column.
  // On mobile it is an overlay, so we slide it in/out.
  const isMobile = () => window.matchMedia("(max-width: 820px)").matches;

  function toggleSidebar() {
    if (isMobile()) $("#sidebar").classList.toggle("open");
    else $("#app").classList.toggle("collapsed");
  }
  function closeSidebar() {
    $("#sidebar").classList.remove("open");
    // Leave desktop collapse state alone; only the overlay auto-closes.
  }

  function bindSuggestions() {
    document.querySelectorAll(".suggestions .chip").forEach((chip) => {
      chip.addEventListener("click", () => sendMessage(chip.textContent));
    });
  }

  // ------------------------- Wiring -------------------------
  function autoGrow(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }

  function init() {
    loadStatus();
    loadTools();
    loadConversations();
    loadSettings();

    // Collapsible tools list (starts collapsed).
    const toolsToggle = $("#tools-toggle");
    toolsToggle.addEventListener("click", () => {
      const body = $("#tools-body");
      const open = body.classList.toggle("collapsed") === false;
      toolsToggle.setAttribute("aria-expanded", String(open));
      if (open) $("#tool-search").focus();
    });

    // LLM provider / model controls.
    $("#provider-select").addEventListener("change", onProviderChange);
    $("#model-input").addEventListener("change", onModelChange);

    const input = $("#composer-input");
    input.addEventListener("input", () => autoGrow(input));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const text = input.value;
        input.value = "";
        autoGrow(input);
        sendMessage(text);
      }
    });
    $("#send-btn").addEventListener("click", () => {
      const text = input.value;
      input.value = "";
      autoGrow(input);
      sendMessage(text);
    });

    $("#tool-search").addEventListener("input", (e) => filterTools(e.target.value));
    $("#tool-run").addEventListener("click", runTool);
    $("#tool-back").addEventListener("click", () => {
      showView("chat");
      $("#active-title").textContent = "Chat";
      $("#active-sub").textContent = "Ask anything, or run a tool directly";
    });
    $("#new-chat").addEventListener("click", newChat);

    $("#menu-btn").addEventListener("click", toggleSidebar);
    $("#sidebar-toggle").addEventListener("click", toggleSidebar);

    // Chat composer file attachment: upload, then reference the path so the
    // agent can act on it (summarize a doc, resize an image, …).
    $("#attach-btn").addEventListener("click", () => $("#attach-input").click());
    $("#attach-input").addEventListener("change", async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const btn = $("#attach-btn");
      btn.textContent = "⏳";
      try {
        const res = await uploadFile(f);
        if (res.ok) {
          const hint = `[Uploaded file: ${res.path}]`;
          input.value = (input.value ? input.value + "\n\n" : "") + hint + "\n";
          autoGrow(input);
          input.focus();
        } else {
          console.error(res.error);
        }
      } catch (err) {
        console.error(err);
      } finally {
        btn.textContent = "📎";
        e.target.value = "";
      }
    });

    bindSuggestions();
  }

  document.addEventListener("DOMContentLoaded", init);
})();

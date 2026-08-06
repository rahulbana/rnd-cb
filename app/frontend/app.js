/* AI Agent frontend — chat + direct tool invocation. Vanilla JS, no deps. */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const api = (path, opts) => fetch(path, opts).then((r) => r.json());

  const state = {
    messages: [],      // {role, content}
    tools: {},         // name -> tool meta
    sending: false,
  };

  // ------------------------- Status + tools -------------------------
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      const pill = $("#status-pill");
      if (s.llm_configured) {
        pill.textContent = `${s.model} · ${s.tool_count} tools`;
        pill.className = "pill pill-ok";
      } else {
        pill.textContent = "no API key — tools only";
        pill.className = "pill pill-warn";
      }
    } catch {
      $("#status-pill").textContent = "offline";
    }
  }

  async function loadTools() {
    const data = await api("/api/tools");
    const list = $("#tool-list");
    list.innerHTML = "";
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

  function addTyping() {
    const el = document.createElement("div");
    el.className = "msg assistant typing-msg";
    el.innerHTML = `<div class="avatar">✦</div>
      <div class="bubble-wrap"><div class="role">Agent</div>
      <div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div></div>`;
    $("#messages").appendChild(el);
    el.scrollIntoView({ behavior: "smooth", block: "end" });
    return el;
  }

  async function sendMessage(text) {
    if (!text.trim() || state.sending) return;
    state.sending = true;
    $("#send-btn").disabled = true;

    addMessage("user", text);
    state.messages.push({ role: "user", content: text });
    const typing = addTyping();

    try {
      const res = await api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: state.messages }),
      });
      typing.remove();
      const reply = res.reply || "(no response)";
      addMessage("assistant", reply, res.tools_used);
      state.messages.push({ role: "assistant", content: reply });
    } catch (e) {
      typing.remove();
      addMessage("assistant", "⚠️ Request failed: " + e.message);
    } finally {
      state.sending = false;
      $("#send-btn").disabled = false;
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
      field.appendChild(input);
      form.appendChild(field);
    });
    if (!Object.keys(props).length) {
      form.innerHTML = '<p class="muted">This tool takes no parameters.</p>';
    }
    $("#tool-result").hidden = true;
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
    out.hidden = false;
    out.textContent = "Running…";
    try {
      const res = await api("/api/tool/" + encodeURIComponent(title), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arguments: args }),
      });
      out.textContent = JSON.stringify(res, null, 2);
    } catch (e) {
      out.textContent = "Error: " + e.message;
    }
  }

  // ------------------------- Sidebar (mobile) -------------------------
  function toggleSidebar() { $("#sidebar").classList.toggle("open"); }
  function closeSidebar() { $("#sidebar").classList.remove("open"); }

  // ------------------------- Wiring -------------------------
  function autoGrow(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }

  function init() {
    loadStatus();
    loadTools();

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
    $("#new-chat").addEventListener("click", () => {
      state.messages = [];
      $("#messages").innerHTML = "";
      location.reload();
    });

    $("#menu-btn").addEventListener("click", toggleSidebar);
    $("#sidebar-toggle").addEventListener("click", toggleSidebar);

    document.querySelectorAll(".suggestions .chip").forEach((chip) => {
      chip.addEventListener("click", () => sendMessage(chip.textContent));
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();

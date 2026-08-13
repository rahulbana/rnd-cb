"use strict";

const state = {
  projectId: null,
  ws: null,
  lastSeq: 0,
  tokenEl: null,
  outputEl: null,
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.text();
}

// ---------------- provider status ----------------
async function loadConfig() {
  try {
    const cfg = await api("/api/config");
    const color = cfg.healthy === false ? "var(--red)" : "var(--green)";
    $("#providerStatus").innerHTML =
      `<span style="color:${color}">●</span> ${cfg.provider} · ${cfg.model}` +
      (cfg.memory_enabled ? " · memory" : "");

    // Approval checkbox: sticky user preference, defaulting to server config.
    const stored = localStorage.getItem("autodev.requireApproval");
    const initial =
      stored === null ? !!cfg.require_plan_approval : stored === "true";
    $("#approvalToggle").checked = initial;
  } catch (e) {
    $("#providerStatus").textContent = "offline";
  }
}

$("#approvalToggle").onchange = (e) => {
  localStorage.setItem("autodev.requireApproval", e.target.checked);
};

// ---------------- project list ----------------
async function loadProjects() {
  const projects = await api("/api/projects");
  const list = $("#projectList");
  list.innerHTML = "";
  for (const p of projects) {
    const item = el("div", "project-item");
    if (p.id === state.projectId) item.classList.add("active");
    const status = p.running ? "running" : p.status;
    item.innerHTML = `
      <div class="pi-name">${escapeHtml(p.name || "Untitled")}</div>
      <div class="pi-meta">
        <span class="dot ${status}"></span>
        <span>${status}</span>
        ${p.language ? `· <span>${escapeHtml(p.language)}</span>` : ""}
      </div>`;
    item.onclick = () => selectProject(p.id);
    list.appendChild(item);
  }
}

// ---------------- create ----------------
$("#createBtn").onclick = async () => {
  const goal = $("#goalInput").value.trim();
  if (goal.length < 3) return;
  $("#createBtn").disabled = true;
  try {
    const project = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        goal,
        auto_start: true,
        require_approval: $("#approvalToggle").checked,
      }),
    });
    $("#goalInput").value = "";
    await loadProjects();
    await selectProject(project.id);
  } catch (e) {
    alert("Failed to create: " + e.message);
  } finally {
    $("#createBtn").disabled = false;
  }
};

// ---------------- select / render ----------------
async function selectProject(id) {
  state.projectId = id;
  state.lastSeq = 0;
  state.tokenEl = null;
  state.outputEl = null;

  $("#emptyState").classList.add("hidden");
  $("#projectView").classList.remove("hidden");
  $("#stream").innerHTML = "";

  const p = await api(`/api/projects/${id}`);
  renderHeader(p);
  renderFiles(p.artifacts || []);
  renderPlan(p.plan);
  await loadProjects();

  // Replay persisted events, then open the live socket.
  const events = await api(`/api/projects/${id}/events?after=0`);
  for (const ev of events) handleEvent(ev, false);
  connectSocket(id);
  switchTab("stream");
}

function renderHeader(p) {
  $("#pName").textContent = p.name || "Untitled";
  $("#pDesc").textContent = p.description || p.goal || "";
  const awaiting = p.status === "awaiting_approval";
  const status = p.running ? "running" : p.status;
  const badge = $("#pStatus");
  badge.textContent = status.replace("_", " ");
  badge.className = "badge " + status;
  $("#runBtn").disabled = !!p.running || awaiting;
  $("#stopBtn").disabled = !p.running;
  $("#approvalBar").classList.toggle("hidden", !awaiting);
}

function renderPlan(plan) {
  $("#planView").textContent = plan
    ? JSON.stringify(plan, null, 2)
    : "No plan yet.";
}

function renderFiles(artifacts) {
  const list = $("#fileList");
  list.innerHTML = "";
  if (!artifacts.length) {
    list.appendChild(el("li", "", "No files yet"));
    return;
  }
  for (const a of artifacts) {
    const li = el("li", "", a.path);
    li.title = a.path;
    li.onclick = async () => {
      document.querySelectorAll("#fileList li").forEach((n) =>
        n.classList.remove("active")
      );
      li.classList.add("active");
      try {
        const f = await api(
          `/api/projects/${state.projectId}/files?path=${encodeURIComponent(a.path)}`
        );
        $("#fileView").textContent = f.content;
      } catch (e) {
        $("#fileView").textContent = "Could not load file.";
      }
    };
    list.appendChild(li);
  }
}

// ---------------- websocket streaming ----------------
function connectSocket(id) {
  if (state.ws) {
    try { state.ws.close(); } catch (e) {}
  }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/projects/${id}`);
  state.ws = ws;
  ws.onopen = () => ws.send(JSON.stringify({ after: state.lastSeq }));
  ws.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    handleEvent(ev, true);
  };
}

function handleEvent(ev, live) {
  // Ephemeral streams (not persisted): live token thinking + command output.
  if (ev.type === "token") {
    appendToken(ev.data && ev.data.text ? ev.data.text : "");
    return;
  }
  if (ev.type === "output") {
    appendOutput(ev.data && ev.data.line ? ev.data.line : "");
    return;
  }

  // Persisted milestone events reset the ephemeral buffers.
  state.tokenEl = null;
  state.outputEl = null;
  if (ev.seq) state.lastSeq = Math.max(state.lastSeq, ev.seq);

  const line = el("div", "line " + (ev.type || ""));
  const phase = ev.phase ? `[${ev.phase}] ` : "";
  line.textContent = phase + (ev.message || "");
  addLine(line);

  if (ev.type === "result" && ev.data && ev.data.tail) {
    const pre = el("div", "line output");
    pre.textContent = ev.data.tail;
    addLine(pre);
  }

  // Refresh side panels on meaningful transitions.
  if (["file", "result", "done", "status", "phase", "approval"].includes(ev.type)) {
    refreshSidePanels();
  }
}

function appendToken(text) {
  if (!state.tokenEl) {
    state.tokenEl = el("div", "token-stream");
    addLine(state.tokenEl);
  }
  state.tokenEl.textContent += text;
  scrollStream();
}

function appendOutput(text) {
  if (!state.outputEl) {
    state.outputEl = el("div", "line output");
    addLine(state.outputEl);
  }
  state.outputEl.textContent += (state.outputEl.textContent ? "\n" : "") + text;
  scrollStream();
}

function addLine(node) {
  $("#stream").appendChild(node);
  scrollStream();
}

function scrollStream() {
  const s = $("#stream");
  // Auto-scroll only when already near the bottom.
  if (s.scrollHeight - s.scrollTop - s.clientHeight < 120) {
    s.scrollTop = s.scrollHeight;
  }
}

let refreshTimer = null;
function refreshSidePanels() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    if (!state.projectId) return;
    try {
      const p = await api(`/api/projects/${state.projectId}`);
      renderHeader(p);
      renderFiles(p.artifacts || []);
      renderPlan(p.plan);
      loadProjects();
    } catch (e) {}
  }, 400);
}

// ---------------- tabs ----------------
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => switchTab(t.dataset.tab);
});
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === name)
  );
  document.querySelectorAll(".tab-panel").forEach((p) =>
    p.classList.add("hidden")
  );
  $(`#tab-${name}`).classList.remove("hidden");
}

// ---------------- actions ----------------
$("#runBtn").onclick = async () => {
  await api(`/api/projects/${state.projectId}/run`, { method: "POST" });
  connectSocket(state.projectId);
  refreshSidePanels();
};
$("#stopBtn").onclick = async () => {
  await api(`/api/projects/${state.projectId}/stop`, { method: "POST" });
  refreshSidePanels();
};
$("#approveBtn").onclick = async () => {
  $("#approvalBar").classList.add("hidden");
  await api(`/api/projects/${state.projectId}/approve`, { method: "POST" });
  connectSocket(state.projectId);
  refreshSidePanels();
};
$("#reviseBtn").onclick = async () => {
  const feedback = $("#reviseInput").value.trim();
  if (!feedback) return;
  $("#reviseInput").value = "";
  $("#approvalBar").classList.add("hidden");
  await api(`/api/projects/${state.projectId}/revise`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });
  connectSocket(state.projectId);
  refreshSidePanels();
};
$("#deleteBtn").onclick = async () => {
  if (!confirm("Delete this project and its sandbox?")) return;
  await api(`/api/projects/${state.projectId}`, { method: "DELETE" });
  state.projectId = null;
  $("#projectView").classList.add("hidden");
  $("#emptyState").classList.remove("hidden");
  loadProjects();
};

// ---------------- util ----------------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// ---------------- boot ----------------
loadConfig();
loadProjects();
setInterval(loadProjects, 5000);

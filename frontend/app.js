/* TravelPlanner SPA — talks to the FastAPI backend on the same origin. */
"use strict";
const API = "/api/v1";

// --- tiny helpers ----------------------------------------------------------
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (m) => m ? `${Number(m.amount).toLocaleString()} ${m.currency}` : "—";

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "content-type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

// --- app state -------------------------------------------------------------
const state = { trips: [], trip: null, tab: "overview", planning: false };

const TABS = [
  ["overview", "Overview", "📋"], ["itinerary", "Itinerary", "🗓"],
  ["budget", "Budget", "💰"], ["map", "Map", "🗺"],
  ["activities", "Explore", "📸"], ["practical", "Practical", "🧳"],
  ["assistant", "Assistant", "💬"],
];

// --- boot ------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", async () => {
  $("#newTripBtn").addEventListener("click", showHome);
  $("#menuToggle").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  await loadMeta();
  await loadTrips();
  showHome();
});

async function loadMeta() {
  try {
    const meta = await api("/meta");
    const mode = meta.llm.mode.includes("offline")
      ? `⚙️ Offline mode — set OPENAI_API_KEY for full AI (${meta.agents.length} agents ready)`
      : `✅ AI online · ${meta.agents.length} agents`;
    $("#modeBadge").textContent = mode;
  } catch (e) { $("#modeBadge").textContent = ""; }
}

async function loadTrips() {
  try {
    state.trips = await api("/trips");
  } catch (e) { state.trips = []; }
  renderTripList();
}

function renderTripList() {
  $("#tripCount").textContent = state.trips.length;
  const list = $("#tripList");
  list.innerHTML = state.trips.map((t) => `
    <div class="trip-item ${state.trip && state.trip.trip_id === t.trip_id ? "active" : ""}"
         data-id="${t.trip_id}">
      <div class="t">${esc(t.title)}</div>
      <div class="s">${esc((t.destinations || []).join(", ") || "No destination")} ·
        ${t.duration_days || "?"}d · <span class="pill">${esc(t.status)}</span></div>
    </div>`).join("") || `<div class="muted" style="font-size:13px">No trips yet — create one!</div>`;
  list.querySelectorAll(".trip-item").forEach((el) =>
    el.addEventListener("click", () => openTrip(el.dataset.id)));
}

// --- Home / trip creation --------------------------------------------------
function showHome() {
  state.trip = null; renderTripList(); setHeaderActions("");
  $("#sidebar").classList.remove("open");
  $("#view").innerHTML = `
    <section class="hero">
      <h1>Where to next?</h1>
      <p>Describe your trip in plain language. A team of AI travel agents will research the
         destination, build a day-by-day itinerary, estimate your budget and more.</p>
      <div class="composer">
        <textarea id="nlInput" placeholder="e.g. Plan an 8-day trip to Tokyo from Delhi in October with my wife, budget 2.5 lakh, we love food, culture and photography"></textarea>
        <div class="row between" style="margin-top:10px">
          <div class="chips" id="exampleChips"></div>
          <button class="btn primary" id="createBtn">Plan my trip →</button>
        </div>
      </div>
    </section>
    <div class="grid cols-3 mt" id="featureCards"></div>`;

  const examples = [
    "Plan a honeymoon in Bali for 6 days",
    "5-day family trip to New York, budget $4000",
    "Weekend in Paris — art, food and photography",
    "10 days in Tokyo from Delhi in October, love food and culture",
  ];
  $("#exampleChips").innerHTML = examples.map((e, i) =>
    `<button data-i="${i}">${esc(e)}</button>`).join("");
  $("#exampleChips").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => { $("#nlInput").value = examples[b.dataset.i]; }));

  const features = [
    ["🧠", "Multi-agent planning", "13 specialists coordinate research, itinerary, budget and safety."],
    ["🛡", "Honest data", "Every fact is labelled — verified, live, estimated or AI recommendation."],
    ["💬", "Context-aware assistant", "Ask to make it cheaper, add a stop or replan for rain."],
  ];
  $("#featureCards").innerHTML = features.map(([i, t, d]) =>
    `<div class="card"><div style="font-size:26px">${i}</div><h3>${t}</h3><div class="soft">${d}</div></div>`).join("");

  $("#createBtn").addEventListener("click", createTrip);
}

async function createTrip() {
  const text = $("#nlInput").value.trim();
  if (!text) return;
  const btn = $("#createBtn"); btn.disabled = true; btn.textContent = "Creating…";
  try {
    const trip = await api("/trips/from-text", { method: "POST", body: JSON.stringify({ text }) });
    await loadTrips();
    state.trip = trip; state.tab = "overview";
    renderDashboard();
    await planTrip(); // kick off planning immediately with live progress
  } catch (e) {
    alert("Could not create trip: " + e.message);
    btn.disabled = false; btn.textContent = "Plan my trip →";
  }
}

// --- Open / dashboard ------------------------------------------------------
async function openTrip(id) {
  try {
    state.trip = await api("/trips/" + id);
    state.tab = "overview";
    $("#sidebar").classList.remove("open");
    renderDashboard();
  } catch (e) { alert("Could not open trip: " + e.message); }
}

function setHeaderActions(html) { $("#headerActions").innerHTML = html; }

function renderDashboard() {
  renderTripList();
  const t = state.trip;
  setHeaderActions(`
    <button class="btn sm" id="replanBtn">↻ Replan</button>
    <button class="btn sm primary" id="optimizeBtn">✨ Optimize</button>`);
  $("#replanBtn").addEventListener("click", planTrip);
  $("#optimizeBtn").addEventListener("click", optimizeTrip);

  $("#view").innerHTML = `
    <div class="row between">
      <div>
        <h1 style="margin-bottom:2px">${esc(t.title)}</h1>
        <div class="soft">${esc((t.request.destinations || []).join(", ") || "—")} ·
          ${t.request.duration_days || "?"} days · ${t.request.travelers} traveller(s) ·
          <span class="pill">${esc(t.status)}</span></div>
      </div>
    </div>
    <div class="tabs" id="tabs"></div>
    <div id="tabView"></div>`;

  const tabs = $("#tabs");
  tabs.innerHTML = TABS.map(([id, label]) =>
    `<button class="tab ${state.tab === id ? "active" : ""}" data-tab="${id}">${label}</button>`).join("");
  tabs.querySelectorAll(".tab").forEach((b) =>
    b.addEventListener("click", () => { state.tab = b.dataset.tab; renderDashboard(); }));

  renderBottomNav();
  renderTab();
}

function renderBottomNav() {
  const nav = $("#bottomNav");
  nav.innerHTML = TABS.map(([id, label, icon]) =>
    `<button class="${state.tab === id ? "active" : ""}" data-tab="${id}">
      <span style="font-size:18px">${icon}</span>${label}</button>`).join("");
  nav.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => { state.tab = b.dataset.tab; renderDashboard();
      window.scrollTo({ top: 0, behavior: "smooth" }); }));
}

function renderTab() {
  const el = $("#tabView");
  if (state.planning) { el.innerHTML = planningView(); return; }
  ({
    overview: renderOverview, itinerary: renderItinerary, budget: renderBudget,
    map: renderMap, activities: renderActivities, practical: renderPractical,
    assistant: renderAssistant,
  }[state.tab] || renderOverview)(el);
}

// --- Tabs ------------------------------------------------------------------
function renderOverview(el) {
  const t = state.trip;
  const warnings = (t.warnings || []).slice(0, 6);
  el.innerHTML = `
    <div class="grid cols-3 mb">
      ${statCard("💰 Budget (comfort)", t.budget ? money(t.budget.total_comfort) : "Not planned",
        t.budget ? (t.budget.within_budget === false ? "Over budget" : "Within budget") : "")}
      ${statCard("🗓 Itinerary", (t.itinerary?.length || 0) + " days", (activityCount(t)) + " activities")}
      ${statCard("☀ Weather", t.weather ? `${t.weather.typical_low_c}–${t.weather.typical_high_c}°C` : "—",
        t.weather ? esc(t.weather.season) : "")}
    </div>
    ${warnings.length ? `<div class="warnbox mb"><strong>Heads up:</strong><ul class="clean">
      ${warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>` : ""}
    <div class="grid cols-2">
      <div class="card">
        <h3>Highlights</h3>
        ${(t.highlights || []).map((h) => `
          <div class="row" style="align-items:flex-start;margin:8px 0">
            <span class="trust ${h.trust}">${h.trust.replace("_", " ")}</span>
            <span class="soft" style="flex:1">${esc(h.value)}</span></div>`).join("") ||
          `<div class="muted">Plan the trip to see highlights.</div>`}
      </div>
      <div class="card">
        <h3>Destination</h3>
        ${t.destination_overview ? `
          <p class="soft">${esc(t.destination_overview.summary || "")}</p>
          <div class="row"><span class="badge">Best time</span> ${esc(t.destination_overview.best_time_to_visit || "")}</div>
          <div class="mt"><strong>Neighborhoods:</strong> <span class="soft">${esc((t.destination_overview.neighborhoods || []).join(", "))}</span></div>`
          : `<div class="muted">Not researched yet.</div>`}
      </div>
    </div>
    ${t.flights ? `<div class="card mt"><h3>✈️ Flights <span class="trust estimated">estimated</span></h3>
      ${(t.flights.options || []).map((o) => `<div class="row between">
        <div><strong>${esc(o.from_airport)} → ${esc(o.to_airport)}</strong> · ${o.stops} stop(s) · ${o.duration_hours}h</div>
        <div class="soft">${esc(o.note || "")}</div></div>`).join("")}</div>` : ""}`;
}

function renderItinerary(el) {
  const t = state.trip;
  if (!t.itinerary?.length) { el.innerHTML = empty("No itinerary yet.", "Plan the trip to generate a day-by-day timeline."); return; }
  el.innerHTML = t.itinerary.map((d) => `
    <div class="day">
      <div class="day-head"><span class="n">Day ${d.day}</span>
        <span class="soft">${d.date ? esc(d.date) : ""}</span></div>
      <div class="soft mb">${esc(d.summary || "")}</div>
      <div class="timeline">
        ${d.items.map((it) => `
          <div class="tl-item ${it.kind}">
            <div class="tl-time">${esc(it.start_time)}${it.duration_minutes ? " · " + it.duration_minutes + " min" : ""}</div>
            <div class="tl-title">${esc(it.title)}
              ${it.recommendation ? `<span class="badge ${it.recommendation}">${it.recommendation.replace("_", " ")}</span>` : ""}</div>
          </div>`).join("")}
      </div>
    </div>`).join("");
}

function renderBudget(el) {
  const b = state.trip.budget;
  if (!b) { el.innerHTML = empty("No budget yet.", "Plan the trip to build a min/comfort/premium budget."); return; }
  const max = Math.max(...b.lines.map((l) => l.premium.amount), 1);
  el.innerHTML = `
    <div class="grid cols-3 mb">
      ${statCard("Minimum", money(b.total_minimum))}
      ${statCard("Comfort", money(b.total_comfort))}
      ${statCard("Premium", money(b.total_premium))}
    </div>
    ${b.within_budget === false ? `<div class="warnbox mb">Estimated comfort cost exceeds your stated budget.</div>` : ""}
    ${(b.advice || []).map((a) => `<div class="soft mb">💡 ${esc(a)}</div>`).join("")}
    <div class="card">
      <table class="budget">
        <thead><tr><th>Category</th><th>Min</th><th>Comfort</th><th>Premium</th></tr></thead>
        <tbody>${b.lines.map((l) => `<tr>
          <td>${esc(l.category)}<div class="bar" style="margin-top:4px"><span style="width:${Math.round(l.comfort.amount / max * 100)}%"></span></div></td>
          <td>${money(l.minimum)}</td><td>${money(l.comfort)}</td><td>${money(l.premium)}</td></tr>`).join("")}</tbody>
        <tfoot><tr><td>Total</td><td>${money(b.total_minimum)}</td><td>${money(b.total_comfort)}</td><td>${money(b.total_premium)}</td></tr></tfoot>
      </table>
    </div>
    <div class="muted mt" style="font-size:12px">All figures are planning estimates, not quotes.</div>`;
}

async function renderMap(el) {
  el.innerHTML = `<div class="card"><div class="muted">Loading map…</div></div>`;
  try {
    const m = await api(`/trips/${state.trip.trip_id}/map`);
    const pts = m.points || [];
    const markers = pts.map((p) => {
      const x = (p.lng + 180) / 360 * 100;
      const y = (90 - p.lat) / 180 * 100;
      return `<div class="map-marker" style="left:${x}%;top:${y}%">
        <div class="dot"></div><div class="lbl">${esc(p.name)}</div></div>`;
    }).join("");
    el.innerHTML = `
      <div class="mapwrap">${markers || `<div class="muted" style="padding:20px">No coordinates.</div>`}</div>
      <div class="grid cols-auto mt">${pts.map((p) => `<div class="card">
        <strong>${esc(p.name)}</strong><div class="soft">${p.lat.toFixed(3)}, ${p.lng.toFixed(3)}</div>
        <span class="badge">${esc(p.kind)}</span></div>`).join("")}</div>
      <div class="muted mt" style="font-size:12px">Equirectangular projection · coordinates from the geocode tool.</div>`;
  } catch (e) { el.innerHTML = empty("Map unavailable.", e.message); }
}

function renderActivities(el) {
  const t = state.trip;
  const acts = t.activities || [], food = t.restaurants || [];
  if (!acts.length && !food.length) { el.innerHTML = empty("Nothing to explore yet.", "Plan the trip to get activity and dining ideas."); return; }
  el.innerHTML = `
    <h3>📸 Activities</h3>
    <div class="grid cols-auto mb">${acts.map(placeCard).join("") || `<div class="muted">None</div>`}</div>
    <h3>🍽 Food & dining</h3>
    <div class="grid cols-auto">${food.map(placeCard).join("") || `<div class="muted">None</div>`}</div>`;
}

function placeCard(p) {
  return `<div class="card"><div class="row between">
    <strong>${esc(p.name)}</strong>
    ${p.recommendation ? `<span class="badge ${p.recommendation}">${p.recommendation.replace("_", " ")}</span>` : ""}</div>
    <div class="soft" style="font-size:13px">${esc(p.note || p.category || "")}</div>
    ${p.duration_minutes ? `<div class="muted" style="font-size:12px;margin-top:6px">~${p.duration_minutes} min</div>` : ""}</div>`;
}

function renderPractical(el) {
  const t = state.trip;
  el.innerHTML = `
    <div class="grid cols-2">
      ${infoCard("🛂 Visa & documents", t.visa, ["requirement", "passport_validity"], t.visa?.documents, "disclaimer")}
      ${infoCard("🛡 Safety", t.safety, ["overall"], t.safety?.common_scams, null, "Common scams")}
      ${weatherCard(t.weather)}
      ${localCard(t.local_tips)}
    </div>
    <div class="card mt"><h3>🧳 Packing list</h3>
      ${(t.packing || []).length ? `<ul class="clean" style="columns:2">${t.packing.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`
        : `<div class="muted">Plan the trip to generate a packing list.</div>`}</div>`;
}

function infoCard(title, obj, fields, list, disclaimerKey, listTitle) {
  if (!obj) return `<div class="card"><h3>${title}</h3><div class="muted">Not available yet.</div></div>`;
  return `<div class="card"><h3>${title}</h3>
    ${fields.map((f) => obj[f] ? `<div class="soft mb">${esc(obj[f])}</div>` : "").join("")}
    ${list?.length ? `<strong style="font-size:13px">${listTitle || "Prepare"}:</strong>
      <ul class="clean">${list.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    ${disclaimerKey && obj[disclaimerKey] ? `<div class="muted" style="font-size:12px">⚠️ ${esc(obj[disclaimerKey])}</div>` : ""}</div>`;
}

function weatherCard(w) {
  if (!w) return `<div class="card"><h3>☀ Weather</h3><div class="muted">Not available.</div></div>`;
  return `<div class="card"><h3>☀ Weather <span class="trust estimated">estimated</span></h3>
    <div class="stat">${w.typical_low_c}–${w.typical_high_c}°C</div>
    <div class="stat-label">${esc(w.season)} · ${esc(w.rain_probability)} rain</div>
    ${w.clothing?.length ? `<div class="mt"><strong style="font-size:13px">Pack:</strong>
      <ul class="clean">${w.clothing.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>` : ""}</div>`;
}

function localCard(l) {
  if (!l) return `<div class="card"><h3>🗺 Local tips</h3><div class="muted">Not available.</div></div>`;
  return `<div class="card"><h3>🗺 Local tips</h3>
    <div class="soft mb"><strong>Currency:</strong> ${esc(l.currency)} · <strong>Tipping:</strong> ${esc(l.tipping)}</div>
    ${l.etiquette?.length ? `<ul class="clean">${l.etiquette.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>` : ""}</div>`;
}

// --- Assistant chat --------------------------------------------------------
const chatHistory = [];
function renderAssistant(el) {
  el.innerHTML = `
    <div class="card chat">
      <div class="chat-log" id="chatLog">
        ${chatHistory.map(renderMsg).join("") || `<div class="msg assistant">Hi! I'm your travel assistant.
          Ask me to make the trip cheaper, add an attraction, or replan for rain. I know your itinerary,
          budget and weather.</div>`}
      </div>
      <div class="chat-input">
        <input id="chatInput" placeholder="Ask anything about your trip…" />
        <button class="btn primary" id="chatSend">Send</button>
      </div>
    </div>`;
  const send = () => sendChat();
  $("#chatSend").addEventListener("click", send);
  $("#chatInput").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  $("#chatLog").scrollTop = 1e9;
}

function renderMsg(m) { return `<div class="msg ${m.role}">${esc(m.content)}</div>`; }

async function sendChat() {
  const input = $("#chatInput"); const text = input.value.trim();
  if (!text) return;
  input.value = "";
  chatHistory.push({ role: "user", content: text });
  chatHistory.push({ role: "assistant", content: "…" });
  renderAssistant($("#tabView"));
  const idx = chatHistory.length - 1;
  try {
    const res = await api("/chat", { method: "POST",
      body: JSON.stringify({ trip_id: state.trip.trip_id, message: text }) });
    chatHistory[idx].content = res.reply;
    if (res.used_agents?.length) {
      // Refresh trip data if an agent modified it.
      state.trip = await api("/trips/" + state.trip.trip_id);
    }
  } catch (e) { chatHistory[idx].content = "Error: " + e.message; }
  renderAssistant($("#tabView"));
}

// --- Planning with SSE progress -------------------------------------------
const PROGRESS = {};
function planningView() {
  const agents = ["destination", "flight", "hotel", "activity", "food", "weather",
    "itinerary", "transportation", "budget", "visa", "safety", "packing", "local_guide"];
  return `<div class="card">
    <h3>Planning your trip…</h3>
    <div class="progress-list">${agents.map((a) => `
      <div class="progress-row ${PROGRESS[a] ? "done" : ""}" id="pr-${a}">
        <span class="ico">${PROGRESS[a] ? "✓" : `<span class="spinner"></span>`}</span>
        <span>${labelFor(a)}</span></div>`).join("")}</div>
  </div>`;
}
function labelFor(a) {
  return ({ destination: "Researching destination", flight: "Estimating flights",
    hotel: "Finding accommodation", activity: "Curating activities", food: "Picking restaurants",
    weather: "Checking the weather", itinerary: "Building the itinerary",
    transportation: "Mapping local transport", budget: "Calculating the budget",
    visa: "Visa & documents", safety: "Safety guidance", packing: "Packing list",
    local_guide: "Local tips" }[a] || a);
}

async function planTrip() { await runStream(`/trips/${state.trip.trip_id}/plan/stream`); }

async function runStream(path) {
  state.planning = true;
  for (const k in PROGRESS) delete PROGRESS[k];
  state.tab = "overview"; renderDashboard();
  try {
    const res = await fetch(API + path, { method: "POST", headers: { "content-type": "application/json" } });
    const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n"); buf = parts.pop();
      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const ev = JSON.parse(line.slice(5).trim());
        handlePlanEvent(ev);
      }
    }
  } catch (e) {
    alert("Planning failed: " + e.message);
  }
  state.planning = false;
  try { state.trip = await api("/trips/" + state.trip.trip_id); } catch (e) {}
  await loadTrips();
  renderDashboard();
}

function handlePlanEvent(ev) {
  if (ev.type === "agent_done" && ev.agent) {
    PROGRESS[ev.agent] = true;
    const row = $(`#pr-${ev.agent}`);
    if (row) { row.classList.add("done"); $(".ico", row).textContent = "✓"; }
  } else if (ev.type === "result" && ev.data) {
    state.trip = ev.data;
  }
}

async function optimizeTrip() {
  try {
    state.trip = await api(`/trips/${state.trip.trip_id}/optimize`, { method: "POST" });
    await loadTrips(); state.tab = "budget"; renderDashboard();
  } catch (e) { alert("Optimize failed: " + e.message); }
}

// --- small render utils ----------------------------------------------------
function statCard(label, value, sub = "") {
  return `<div class="card"><div class="stat-label">${label}</div>
    <div class="stat">${esc(value)}</div><div class="soft">${esc(sub)}</div></div>`;
}
function empty(title, sub) {
  return `<div class="card" style="text-align:center;padding:40px">
    <div style="font-size:34px">🧭</div><h3>${esc(title)}</h3><div class="muted">${esc(sub)}</div></div>`;
}
function activityCount(t) {
  return (t.itinerary || []).reduce((n, d) => n + d.items.filter((i) => i.kind === "activity").length, 0);
}

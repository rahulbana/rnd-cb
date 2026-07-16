"use strict";

const strategies = window.STRATEGIES || [];
const $ = (sel) => document.querySelector(sel);

const strategySelect = $("#strategy");
const strategyDesc = $("#strategy-desc");
const paramsBox = $("#params");
const form = $("#chunk-form");
const errorEl = $("#error");
const submitBtn = $("#submit-btn");
const resultsEl = $("#results");
const emptyState = $("#empty-state");

let lastResponse = null;

// ---- Build the strategy dropdown ---------------------------------------- //
strategies.forEach((s) => {
  const opt = document.createElement("option");
  opt.value = s.key;
  opt.textContent = s.available ? s.label : `${s.label} (needs OpenAI key)`;
  opt.disabled = !s.available;
  strategySelect.appendChild(opt);
});

function currentStrategy() {
  return strategies.find((s) => s.key === strategySelect.value);
}

// ---- Render parameter controls for the selected strategy ---------------- //
function renderParams() {
  const s = currentStrategy();
  strategyDesc.textContent = s.description;
  paramsBox.innerHTML = "";

  if (!s.params.length) {
    paramsBox.innerHTML = '<p class="param-help">This strategy has no tunable parameters.</p>';
    return;
  }

  s.params.forEach((p) => {
    const row = document.createElement("div");
    row.className = "param-row";

    if (p.type === "bool") {
      row.innerHTML = `
        <label>
          <span>${p.label}</span>
          <input type="checkbox" data-name="${p.name}" ${p.default ? "checked" : ""}/>
        </label>
        ${p.help ? `<p class="param-help">${p.help}</p>` : ""}`;
    } else {
      const min = p.min ?? 0;
      const max = p.max ?? 1000;
      const step = p.step ?? 1;
      row.innerHTML = `
        <label>
          <span>${p.label}</span>
          <span class="val" id="val-${p.name}">${p.default}</span>
        </label>
        <input type="range" data-name="${p.name}" data-type="${p.type}"
               min="${min}" max="${max}" step="${step}" value="${p.default}"/>
        ${p.help ? `<p class="param-help">${p.help}</p>` : ""}`;
    }
    paramsBox.appendChild(row);
  });

  paramsBox.querySelectorAll('input[type="range"]').forEach((inp) => {
    inp.addEventListener("input", () => {
      $(`#val-${inp.dataset.name}`).textContent = inp.value;
    });
  });
}

function collectParams() {
  const params = {};
  paramsBox.querySelectorAll("input[data-name]").forEach((inp) => {
    const name = inp.dataset.name;
    if (inp.type === "checkbox") {
      params[name] = inp.checked;
    } else {
      params[name] = inp.dataset.type === "float" ? parseFloat(inp.value) : parseInt(inp.value, 10);
    }
  });
  return params;
}

strategySelect.addEventListener("change", renderParams);

// ---- Submit -> call API -> render --------------------------------------- //
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.hidden = true;

  const fd = new FormData();
  fd.append("strategy", strategySelect.value);
  fd.append("params", JSON.stringify(collectParams()));
  const fileInput = $("#file");
  if (fileInput.files.length) fd.append("file", fileInput.files[0]);
  fd.append("text", $("#text").value);

  submitBtn.disabled = true;
  submitBtn.textContent = "Chunking…";

  try {
    const res = await fetch("/api/chunk", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    lastResponse = data;
    render(data);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Chunk it →";
  }
});

// ---- Rendering ---------------------------------------------------------- //
function statCard(num, lbl, sub, cls) {
  return `<div class="stat-card ${cls || ""}">
    <div class="num">${num}</div>
    <div class="lbl">${lbl}</div>
    ${sub ? `<div class="sub">${sub}</div>` : ""}
  </div>`;
}

function render(data) {
  const st = data.stats;
  emptyState.hidden = true;
  resultsEl.hidden = false;

  $("#result-meta").textContent =
    `${data.strategy_label}  ·  ${data.filename || "pasted text"}  ·  ` +
    Object.entries(data.params).map(([k, v]) => `${k}=${v}`).join(" ");

  // Stat cards
  const cards = [];
  cards.push(statCard(st.chunk_count, "Chunks"));
  cards.push(statCard(`${st.char_len.mean}`, "Avg chars / chunk",
    `min ${st.char_len.min} · max ${st.char_len.max}`));
  cards.push(statCard(`${st.token_est.mean}`, "Avg tokens / chunk",
    `~${st.token_est.total} tokens total`));
  const cvClass = st.char_len.cv <= 0.15 ? "good" : st.char_len.cv >= 0.5 ? "warn" : "";
  cards.push(statCard(st.char_len.cv, "Size variability (CV)",
    st.char_len.cv <= 0.15 ? "very uniform" : st.char_len.cv >= 0.5 ? "highly variable" : "moderate", cvClass));
  const redClass = st.overlap.redundancy_pct === 0 ? "good" : st.overlap.redundancy_pct >= 25 ? "warn" : "";
  cards.push(statCard(`${st.overlap.redundancy_pct}%`, "Overlap redundancy",
    `${st.overlap.total_chars} extra chars stored`, redClass));
  const wordClass = st.boundaries.mid_word_pct === 0 ? "good" : st.boundaries.mid_word_pct >= 30 ? "warn" : "";
  cards.push(statCard(`${st.boundaries.mid_word_pct}%`, "Chunks cutting a word",
    `${st.boundaries.mid_word_cuts} of ${st.chunk_count}`, wordClass));
  const sentClass = st.boundaries.mid_sentence_pct === 0 ? "good" : st.boundaries.mid_sentence_pct >= 50 ? "warn" : "";
  cards.push(statCard(`${st.boundaries.mid_sentence_pct}%`, "Chunks cutting a sentence",
    `${st.boundaries.mid_sentence_cuts} of ${st.chunk_count}`, sentClass));
  cards.push(statCard(`${st.coverage_pct}%`, "Source coverage",
    `${st.source_chars} source chars`));
  $("#stat-cards").innerHTML = cards.join("");

  renderHistogram(st.histogram);

  // Chunks
  $("#chunk-count").textContent = st.chunk_count;
  renderChunks(data.chunks);

  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderHistogram(h) {
  const box = $("#histogram");
  const max = Math.max(...h.counts, 1);
  box.innerHTML = h.counts.map((c, i) => {
    const pct = (c / max) * 100;
    return `<div class="hist-bar" style="height:${Math.max(pct, c ? 4 : 0)}%">
      <span class="tip">${h.labels[i]} chars · ${c} chunk${c === 1 ? "" : "s"}</span>
    </div>`;
  }).join("");
  $("#histogram-axis").innerHTML =
    `<span>${h.edges[0]} chars</span><span>${h.edges[h.edges.length - 1]} chars</span>`;
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

function renderChunks(chunks) {
  const showOverlap = $("#show-overlap").checked;
  const box = $("#chunks");
  box.innerHTML = chunks.map((c) => {
    let body;
    if (showOverlap && c.overlap_prev > 0 && c.overlap_prev <= c.text.length) {
      const head = escapeHtml(c.text.slice(0, c.overlap_prev));
      const tail = escapeHtml(c.text.slice(c.overlap_prev));
      body = `<mark title="overlap with previous chunk">${head}</mark>${tail}`;
    } else {
      body = escapeHtml(c.text);
    }
    const ov = c.overlap_prev > 0 ? `<span class="ov">↻ ${c.overlap_prev} overlap</span>` : "";
    return `<div class="chunk">
      <div class="chunk-head">
        <span class="badge">#${c.index}</span>
        <span class="meta">${c.char_len} chars · ~${c.token_est} tok</span>
        <span class="meta">offset ${c.start}–${c.end}</span>
        ${ov}
      </div>
      <div class="chunk-body">${body}</div>
    </div>`;
  }).join("");
}

$("#show-overlap").addEventListener("change", () => {
  if (lastResponse) renderChunks(lastResponse.chunks);
});

// ---- Init --------------------------------------------------------------- //
renderParams();

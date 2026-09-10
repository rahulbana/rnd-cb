// ---------------------------------------------------------------------------
// AI Text Summarizer — frontend. Talks to the Express API: streams summaries
// over NDJSON, counts tokens, and renders structured JSON extraction.
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);

const els = {
  input: $("inputText"),
  file: $("fileInput"),
  sample: $("sampleBtn"),
  clear: $("clearBtn"),
  charCount: $("charCount"),
  tokenCount: $("tokenCount"),
  length: $("lengthSelect"),
  style: $("styleSelect"),
  format: $("formatSelect"),
  focus: $("focusInput"),
  summarize: $("summarizeBtn"),
  extract: $("extractBtn"),
  count: $("countBtn"),
  stop: $("stopBtn"),
  status: $("statusLine"),
  output: $("output"),
  outputMeta: $("outputMeta"),
  modelBadge: $("modelBadge"),
};

const LABELS = {
  length: { short: "Short", medium: "Medium", detailed: "Detailed" },
  style: {
    neutral: "Neutral",
    executive: "Executive",
    technical: "Technical",
    academic: "Academic",
    casual: "Casual",
    eli5: "Simple (ELI5)",
  },
  format: {
    paragraph: "Paragraph",
    bullets: "Bullet points",
    "key-points": "Key points",
    structured: "Structured report",
  },
};

let controller = null; // AbortController for the in-flight stream

// --- Init -----------------------------------------------------------------

async function init() {
  try {
    const res = await fetch("/api/config");
    const cfg = await res.json();
    els.modelBadge.textContent = cfg.model;
    fillSelect(els.length, cfg.lengths, LABELS.length, "medium");
    fillSelect(els.style, cfg.styles, LABELS.style, "neutral");
    fillSelect(els.format, cfg.formats, LABELS.format, "structured");
  } catch {
    els.modelBadge.textContent = "offline";
  }
  updateCharCount();
}

function fillSelect(select, values, labels, def) {
  select.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = labels[v] ?? v;
    if (v === def) opt.selected = true;
    select.appendChild(opt);
  }
}

// --- Input helpers --------------------------------------------------------

function updateCharCount() {
  const n = els.input.value.length;
  els.charCount.textContent = `${n.toLocaleString()} characters`;
  els.tokenCount.textContent = "";
}

function currentOptions() {
  return {
    text: els.input.value,
    length: els.length.value,
    style: els.style.value,
    format: els.format.value,
    focus: els.focus.value.trim() || undefined,
  };
}

function setBusy(busy) {
  els.summarize.disabled = busy;
  els.extract.disabled = busy;
  els.count.disabled = busy;
  els.stop.hidden = !busy;
}

// --- Token counting -------------------------------------------------------

async function countTokens() {
  if (!els.input.value.trim()) return;
  els.tokenCount.textContent = "counting…";
  try {
    const res = await fetch("/api/count-tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentOptions()),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "count failed");
    els.tokenCount.textContent = `~${data.inputTokens.toLocaleString()} input tokens`;
  } catch (err) {
    els.tokenCount.textContent = `token count failed: ${err.message}`;
  }
}

// --- Summarize (streaming NDJSON) ----------------------------------------

async function summarize() {
  const opts = currentOptions();
  if (!opts.text.trim()) {
    showError("Please enter or upload some text first.");
    return;
  }

  setBusy(true);
  els.status.textContent = "Starting…";
  els.outputMeta.textContent = "";
  let markdown = "";
  renderStreaming("");

  controller = new AbortController();
  try {
    const res = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts),
      signal: controller.signal,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `Request failed (${res.status})`);
    }

    await readNdjson(res.body, (event) => {
      switch (event.type) {
        case "status":
          els.status.textContent = event.message;
          break;
        case "meta":
          els.outputMeta.textContent =
            event.strategy === "map-reduce"
              ? `map-reduce · ${event.chunks} sections · ~${event.inputTokens.toLocaleString()} input tokens`
              : `single pass · ~${event.inputTokens.toLocaleString()} input tokens`;
          break;
        case "delta":
          markdown += event.text;
          renderStreaming(markdown);
          break;
        case "done":
          els.status.textContent = "Done.";
          els.output.innerHTML = renderMarkdown(markdown);
          els.outputMeta.textContent +=
            ` · ${event.outputTokens.toLocaleString()} output tokens`;
          break;
        case "error":
          throw new Error(event.message);
      }
    });
  } catch (err) {
    if (err.name === "AbortError") {
      els.status.textContent = "Stopped.";
    } else {
      showError(err.message);
      els.status.textContent = "";
    }
  } finally {
    setBusy(false);
    controller = null;
  }
}

// Parse a newline-delimited-JSON stream, invoking onEvent per line.
async function readNdjson(body, onEvent) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let nl;
    while ((nl = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
  const tail = buffer.trim();
  if (tail) onEvent(JSON.parse(tail));
}

// --- Structured extraction ------------------------------------------------

async function extract() {
  const text = els.input.value;
  if (!text.trim()) {
    showError("Please enter or upload some text first.");
    return;
  }
  setBusy(true);
  els.status.textContent = "Extracting structured data…";
  els.outputMeta.textContent = "";
  els.output.innerHTML = '<p class="placeholder">Working…</p>';

  try {
    const res = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "extraction failed");
    els.status.textContent = "Done.";
    els.output.innerHTML = renderStructured(data);
  } catch (err) {
    showError(err.message);
    els.status.textContent = "";
  } finally {
    setBusy(false);
  }
}

function renderStructured(d) {
  const list = (items) =>
    items.length
      ? `<ul>${items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`
      : '<p class="placeholder">None.</p>';
  return [
    `<h2>${escapeHtml(d.title || "Untitled")}</h2>`,
    `<p>${escapeHtml(d.summary || "")}</p>`,
    "<h3>Key Points</h3>",
    list(d.keyPoints || []),
    "<h3>Decisions</h3>",
    list(d.decisions || []),
    "<h3>Action Items</h3>",
    list(d.actionItems || []),
    "<h3>Entities</h3>",
    list(d.entities || []),
  ].join("");
}

// --- Rendering ------------------------------------------------------------

function renderStreaming(md) {
  els.output.innerHTML = renderMarkdown(md) + '<span class="cursor"></span>';
  els.output.scrollTop = els.output.scrollHeight;
}

function showError(message) {
  els.output.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(s) {
  // Order matters: escape first, then apply inline markdown.
  return escapeHtml(s)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

// A small, dependency-free markdown renderer covering what the summarizer emits:
// H2/H3 headings, bullet lists, bold, inline code, and paragraphs.
function renderMarkdown(md) {
  if (!md.trim()) return '<p class="placeholder">…</p>';
  const lines = md.split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^###\s+/.test(line)) {
      closeList();
      html += `<h3>${inline(line.replace(/^###\s+/, ""))}</h3>`;
    } else if (/^##\s+/.test(line)) {
      closeList();
      html += `<h2>${inline(line.replace(/^##\s+/, ""))}</h2>`;
    } else if (/^#\s+/.test(line)) {
      closeList();
      html += `<h2>${inline(line.replace(/^#\s+/, ""))}</h2>`;
    } else if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`;
    } else if (line.trim() === "") {
      closeList();
    } else {
      closeList();
      html += `<p>${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

// --- Events ---------------------------------------------------------------

els.input.addEventListener("input", updateCharCount);

els.file.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  els.input.value = await file.text();
  updateCharCount();
  els.file.value = "";
});

els.clear.addEventListener("click", () => {
  els.input.value = "";
  els.focus.value = "";
  updateCharCount();
  els.output.innerHTML = '<p class="placeholder">Your summary will appear here.</p>';
  els.status.textContent = "";
  els.outputMeta.textContent = "";
});

els.sample.addEventListener("click", () => {
  els.input.value = SAMPLE_TEXT;
  updateCharCount();
});

els.summarize.addEventListener("click", summarize);
els.extract.addEventListener("click", extract);
els.count.addEventListener("click", countTokens);
els.stop.addEventListener("click", () => controller?.abort());

// A short sample so the app is usable without hunting for text to paste.
const SAMPLE_TEXT = `Quarterly Engineering Review — Q3

Overview
This quarter the platform team focused on reliability and cost. We migrated the
primary datastore to a managed service, reducing on-call incidents by 40% and
cutting infrastructure spend by roughly $18,000 per month. The migration ran two
weeks longer than planned due to an unexpected data-encoding issue in legacy
records, which required a one-off backfill job.

Key results
- API p99 latency dropped from 820ms to 310ms after connection-pool tuning.
- We shipped the new rate limiter, eliminating the three largest outage classes
  from last quarter.
- Test coverage on the billing service rose from 54% to 81%.
- The mobile release cadence moved from monthly to biweekly.

Decisions
- We will standardize on the managed datastore for all new services starting Q4.
- The legacy reporting pipeline will be deprecated; teams must migrate by end of
  Q1 next year.
- We approved hiring two additional SREs to support the expanded on-call rotation.

Risks and open questions
- The backfill job revealed data-quality gaps that may affect historical reports.
- Vendor lock-in is a growing concern; we should evaluate an exit strategy.
- Biweekly mobile releases increase QA load and may require more automation.

Next steps
- Finalize the Q4 migration plan and communicate deadlines to all teams.
- Draft an SRE onboarding guide before the new hires start.
- Investigate the historical data-quality issues and quantify their impact.
- Prototype automated QA for the mobile pipeline.`;

init();

// API client for the book review aggregator backend.
// In dev, Vite proxies these paths to the FastAPI server (see vite.config.js).
// Override with VITE_API_BASE for a deployed backend.

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function postJson(path, body) {
  const resp = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const data = await resp.json();
      if (data.detail) detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return resp;
}

export async function analyzeBook({ title, author }) {
  const resp = await postJson("/analyze", { title, author: author || null });
  return resp.json();
}

// Triggers a browser download of the rendered report.
export async function downloadReport({ title, author }, format) {
  const path = format === "pdf" ? "/export/pdf" : "/export/markdown";
  const resp = await postJson(path, { title, author: author || null });

  const blob = await resp.blob();
  const filename = parseFilename(resp.headers.get("Content-Disposition"), title, format);

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function parseFilename(disposition, title, format) {
  const fallback = `${slug(title)}.${format === "pdf" ? "pdf" : "md"}`;
  if (!disposition) return fallback;
  const match = /filename="([^"]+)"/.exec(disposition);
  return match ? match[1] : fallback;
}

function slug(text) {
  return (
    text
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .toLowerCase() || "book-report"
  );
}

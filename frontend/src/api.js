// Thin API client for the AI Translator backend.
const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  metadata: () => request("/metadata"),
  health: () => request("/health"),
  translate: (payload) =>
    request("/translate", { method: "POST", body: JSON.stringify(payload) }),
  translateBatch: (payload) =>
    request("/translate/batch", { method: "POST", body: JSON.stringify(payload) }),
  history: () => request("/history"),
  clearHistory: () => request("/history", { method: "DELETE" }),
};

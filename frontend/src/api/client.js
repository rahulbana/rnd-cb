// Thin wrapper around the backend REST API.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return body;
}

export const api = {
  health: () => request("/health"),

  generate: (payload) =>
    request("/generate", { method: "POST", body: JSON.stringify(payload) }),

  explain: (payload) =>
    request("/explain", { method: "POST", body: JSON.stringify(payload) }),

  format: (payload) =>
    request("/format", { method: "POST", body: JSON.stringify(payload) }),

  validate: (payload) =>
    request("/validate", { method: "POST", body: JSON.stringify(payload) }),

  listHistory: (limit = 50) => request(`/history?limit=${limit}`),

  deleteHistoryItem: (id) => request(`/history/${id}`, { method: "DELETE" }),

  clearHistory: () => request("/history", { method: "DELETE" }),
};

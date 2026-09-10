// Thin client for the backend API.
const BASE = "/api";

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export function fetchOptions() {
  return fetch(`${BASE}/options`).then((r) => r.json());
}

export function generate(product, config) {
  return post("/generate", { product, config });
}

export function regenerateSection(product, config, section) {
  return post("/regenerate-section", { product, config, section });
}

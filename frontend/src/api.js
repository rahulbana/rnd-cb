// Thin wrapper around the backend API. Uses relative URLs so the Vite dev
// proxy (or any reverse proxy in production) can route to FastAPI.

async function post(path, payload) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function fetchOptions() {
  return fetch("/api/options").then((r) => r.json());
}

export const generateEmail = (payload) => post("/api/generate", payload);
export const rewriteEmail = (payload) => post("/api/rewrite", payload);
export const transformEmail = (payload) => post("/api/transform", payload);

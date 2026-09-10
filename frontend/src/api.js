// Thin wrapper around the backend API. All calls go through the Vite proxy
// (/api -> http://localhost:8000) so URLs stay same-origin in development.

async function post(path, body) {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      /* ignore JSON parse errors */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => fetch("/api/health").then((r) => r.json()),
  outline: (brief) => post("/outline", brief),
  section: (payload) => post("/section", payload),
  article: (brief) => post("/article", brief),
  titles: (brief) => post("/title", brief),
  metaDescription: (brief) => post("/meta-description", brief),
  rewrite: (payload) => post("/rewrite", payload),
};

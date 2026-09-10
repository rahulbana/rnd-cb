// Small fetch wrapper around the backend API.

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body; keep default message */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function getActions() {
  return request("/api/actions");
}

export function getHealth() {
  return request("/api/health");
}

export function detectLanguage(code) {
  return request("/api/detect", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function analyze({ code, action, language, audience }) {
  return request("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ code, action, language, audience }),
  });
}

// Thin API client for the AI JSON Generator backend.

async function request(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) detail = err.detail;
    } catch {
      // response wasn't JSON; keep the generic message
    }
    throw new Error(detail);
  }

  return res.json();
}

export function generateJSON(prompt, schema) {
  return request("/api/generate", { prompt, schema: schema ?? null });
}

export function validateJSON(data, schema) {
  return request("/api/validate", { data, schema });
}

export async function getHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

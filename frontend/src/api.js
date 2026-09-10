// Thin API client for the backend. Uses a relative path so the Vite dev
// proxy (or a same-origin deployment) forwards it to FastAPI.
const BASE = import.meta.env.VITE_API_BASE ?? "";

export async function analyzeResume(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE}/api/analyze`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response had no JSON body; keep the default message
    }
    throw new Error(detail);
  }

  return res.json();
}

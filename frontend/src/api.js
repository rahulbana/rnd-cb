// Thin client around the FastAPI backend.

export async function analyzeCsv(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch("/api/analyze", { method: "POST", body: form });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore json parse errors */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

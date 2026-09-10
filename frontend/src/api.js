// Thin API client for the FastAPI backend.

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function generateQuestions(payload) {
  return post("/api/generate", payload);
}

export function gradeQuiz(payload) {
  return post("/api/grade", payload);
}

export async function checkHealth() {
  const res = await fetch("/api/health");
  return res.json();
}

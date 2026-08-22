// Thin client for the FastAPI backend. In dev, Vite proxies /api -> :8000.
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function post(path, body) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new Error("Could not reach the server. Is the backend running?");
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON error body */
  }

  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
        ? detail.map((d) => d.msg).join("; ")
        : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

export const getTranscript = (url) => post("/api/transcript", { url });
export const getSummary = (url) => post("/api/summary", { url });
export const askQuestion = (url, question) => post("/api/ask", { url, question });
export const getMindMap = (url) => post("/api/mindmap", { url });

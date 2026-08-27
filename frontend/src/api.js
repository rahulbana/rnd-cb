// Thin API client for the research backend.
// API base is same-origin by default (Vite proxies /api in dev). Override with
// VITE_API_BASE for a separately-hosted backend.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function startResearch(topic) {
  const res = await fetch(`${API_BASE}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `Failed to start research (${res.status})`);
  }
  return res.json(); // { thread_id, status }
}

export async function getResearch(threadId) {
  const res = await fetch(`${API_BASE}/api/research/${threadId}`);
  if (!res.ok) throw new Error(`Failed to fetch state (${res.status})`);
  return res.json();
}

export async function cancelResearch(threadId) {
  await fetch(`${API_BASE}/api/research/${threadId}`, { method: "DELETE" });
}

// Open an SSE stream. Returns the EventSource so the caller can close it.
// `onEvent(type, payload)` fires for every known event type.
export function streamResearch(threadId, onEvent, onError) {
  const es = new EventSource(`${API_BASE}/api/research/${threadId}/stream`);
  const types = [
    "run_started",
    "planned",
    "searched",
    "reflected",
    "synthesized",
    "completed",
    "error",
    "cancelled",
  ];
  for (const type of types) {
    es.addEventListener(type, (e) => {
      try {
        onEvent(type, JSON.parse(e.data));
      } catch {
        onEvent(type, {});
      }
    });
  }
  es.onerror = () => {
    // The browser auto-reconnects; surface a soft error but keep the stream.
    if (onError) onError();
  };
  return es;
}

async function safeDetail(res) {
  try {
    const body = await res.json();
    return body.detail;
  } catch {
    return null;
  }
}

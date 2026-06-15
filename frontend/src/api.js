// API helper. Streams Server-Sent Events from the FastAPI backend.
// EventSource only supports GET, so we POST with fetch and parse the stream.

export async function streamStudyPlan(request, handlers) {
  const { onInit, onAgentDone, onComplete, onError } = handlers;

  const res = await fetch("/api/study-plan/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    // Normalize CRLF (sse-starlette uses \r\n) so framing is consistent.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    // SSE events are separated by a blank line.
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const event = parseSSE(chunk);
      if (!event) continue;
      const payload = event.data ? JSON.parse(event.data) : {};
      switch (event.event) {
        case "init":
          onInit?.(payload);
          break;
        case "agent_done":
          onAgentDone?.(payload);
          break;
        case "complete":
          onComplete?.(payload);
          break;
        case "error":
          onError?.(new Error(payload.message || "Unknown error"));
          break;
        default:
          break;
      }
    }
  }
}

function parseSSE(chunk) {
  const lines = chunk.split("\n");
  let event = "message";
  let data = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data && event === "message") return null;
  return { event, data };
}

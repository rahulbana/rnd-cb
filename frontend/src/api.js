// Streams agent events from the backend over a POST + Server-Sent-Events
// connection. EventSource only supports GET, so we parse the SSE frames
// ourselves from the fetch ReadableStream.

export async function streamSearch({ query, numSubqueries, onEvent, signal }) {
  const resp = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, num_subqueries: numSubqueries }),
    signal,
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`Request failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      const dataLines = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());

      if (dataLines.length === 0) continue;
      try {
        const payload = JSON.parse(dataLines.join("\n"));
        onEvent(payload);
      } catch (e) {
        // Ignore malformed frames.
      }
    }
  }
}

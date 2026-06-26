// Parses a fetch Response body (ReadableStream) of Server-Sent Events into a
// stream of parsed JSON event objects. EventSource only supports GET, so we
// parse the SSE frames ourselves to allow POST.
export async function* parseSSE(body) {
  const reader = body.getReader();
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

      const data = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("\n");

      if (!data) continue;
      try {
        yield JSON.parse(data);
      } catch {
        // Ignore malformed frames.
      }
    }
  }
}

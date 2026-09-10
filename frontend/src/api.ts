import type {
  AppConfig,
  StreamEvent,
  StructuredSummary,
  SummarizeOptions,
} from "./types";

async function jsonOrThrow(res: Response): Promise<any> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export async function fetchConfig(): Promise<AppConfig> {
  return jsonOrThrow(await fetch("/api/config"));
}

export async function countTokens(
  opts: SummarizeOptions,
): Promise<{ inputTokens: number; model: string }> {
  return jsonOrThrow(
    await fetch("/api/count-tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts),
    }),
  );
}

export async function extractStructured(
  text: string,
): Promise<StructuredSummary> {
  return jsonOrThrow(
    await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  );
}

/**
 * POST /api/summarize and invoke `onEvent` for each NDJSON event as it streams.
 * Pass an AbortSignal to cancel the in-flight request.
 */
export async function summarizeStream(
  opts: SummarizeOptions,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
    signal,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  if (!res.body) throw new Error("No response body to stream.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let nl: number;
    while ((nl = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (line) onEvent(JSON.parse(line) as StreamEvent);
    }
  }
  const tail = buffer.trim();
  if (tail) onEvent(JSON.parse(tail) as StreamEvent);
}

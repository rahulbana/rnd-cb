import type { ChatMessage, StreamEvent } from "./types";

/**
 * POST a conversation to the backend and yield parsed SSE events as they arrive.
 *
 * We can't use the browser `EventSource` API because it only supports GET, and
 * we need to POST the message history. Instead we read the `fetch` response body
 * as a stream and parse the `event:`/`data:` frames ourselves.
 */
export async function* streamChat(
  messages: Pick<ChatMessage, "role" | "content">[],
  signal: AbortSignal
): AsyncGenerator<StreamEvent> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!response.ok || !response.body) {
    const detail = await safeReadError(response);
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const event = parseFrame(frame);
      if (event) yield event;
    }
  }
}

function parseFrame(frame: string): StreamEvent | null {
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;

  try {
    const payload = JSON.parse(dataLines.join("\n"));
    return { type: eventName, ...payload } as StreamEvent;
  } catch {
    return null;
  }
}

async function safeReadError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export interface HealthInfo {
  status: "ok" | "degraded";
  model: string;
  mcp_server: string;
  tools: string[];
}

export async function fetchHealth(): Promise<HealthInfo> {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return response.json();
}

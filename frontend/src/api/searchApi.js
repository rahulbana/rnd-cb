// Typed access to the backend API. streamSearch is an async generator that
// yields each agent progress event as it arrives.
import { config } from "../config";
import { parseSSE } from "./sse";

export async function* streamSearch({ query, numSubqueries, signal }) {
  const resp = await fetch(`${config.apiBase}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, num_subqueries: numSubqueries }),
    signal,
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`Search request failed: ${resp.status}`);
  }

  yield* parseSSE(resp.body);
}

export async function getHealth() {
  const resp = await fetch(`${config.apiBase}/api/health`);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}

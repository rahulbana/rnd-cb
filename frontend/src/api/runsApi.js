// Run-history API client.
import { config } from "../config";

export async function listRuns(limit = 50) {
  const resp = await fetch(`${config.apiBase}/api/runs?limit=${limit}`);
  if (!resp.ok) throw new Error(`Failed to list runs: ${resp.status}`);
  return resp.json();
}

export async function getRun(runId) {
  const resp = await fetch(`${config.apiBase}/api/runs/${runId}`);
  if (!resp.ok) throw new Error(`Failed to load run: ${resp.status}`);
  return resp.json();
}

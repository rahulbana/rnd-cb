// Thin API client. Uses relative URLs so the Vite dev proxy (or same-origin
// deployment) routes requests to the FastAPI backend.

const BASE = "/api/v1";

async function handle(res) {
  if (res.status === 204) return null;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail =
      (data && (data.detail?.[0]?.msg || data.detail)) || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function createPlan(payload) {
  const res = await fetch(`${BASE}/plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

export async function listPlans() {
  return handle(await fetch(`${BASE}/plans`));
}

export async function getPlan(id) {
  return handle(await fetch(`${BASE}/plans/${id}`));
}

export async function deletePlan(id) {
  return handle(await fetch(`${BASE}/plans/${id}`, { method: "DELETE" }));
}

export async function getHealth() {
  return handle(await fetch(`${BASE}/health`));
}

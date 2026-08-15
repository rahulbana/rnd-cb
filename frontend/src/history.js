// Conversation history — backed by the server (SQLite now, Postgres later).
// Pure helpers (uid/titleFrom/groupByDate) plus a thin REST client.

export function uid() {
  return (crypto.randomUUID && crypto.randomUUID()) || String(Date.now() + Math.random());
}

export function titleFrom(text) {
  const t = (text || "").trim().replace(/\s+/g, " ");
  return t.length > 44 ? t.slice(0, 44) + "…" : t || "New chat";
}

// A fresh, not-yet-persisted conversation (created on the server on first save).
export function newConversation() {
  const now = Date.now();
  return { id: uid(), title: "New chat", createdAt: now, updatedAt: now, messageCount: 0 };
}

// Normalize a message loaded from the server so a reload mid-stream isn't stuck.
export function sanitizeMessages(messages) {
  return (messages || []).map((m) => ({
    ...m,
    status: m.status === "running" ? "done" : m.status,
    sources: m.sources || [],
    steps: m.steps || [],
  }));
}

export function groupByDate(convs) {
  const startOfDay = (d) => new Date(d).setHours(0, 0, 0, 0);
  const today = startOfDay(Date.now());
  const day = 86400000;
  const buckets = { Today: [], Yesterday: [], "Previous 7 days": [], Older: [] };
  for (const c of convs) {
    const d = startOfDay(c.updatedAt);
    if (d === today) buckets["Today"].push(c);
    else if (d === today - day) buckets["Yesterday"].push(c);
    else if (d > today - 7 * day) buckets["Previous 7 days"].push(c);
    else buckets["Older"].push(c);
  }
  return Object.entries(buckets)
    .filter(([, items]) => items.length)
    .map(([label, items]) => ({ label, items }));
}

// ---- REST client ----
const BASE = "/api/conversations";

export async function apiListConversations() {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error("Failed to list conversations");
  return (await res.json()).conversations || [];
}

export async function apiGetConversation(id) {
  const res = await fetch(`${BASE}/${id}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

export async function apiUpsertConversation(id, { title, messages }) {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, messages }),
  });
  if (!res.ok) throw new Error("Failed to save conversation");
  return res.json();
}

export async function apiRenameConversation(id, title) {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to rename");
  return res.json();
}

export async function apiDeleteConversation(id) {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete");
  return res.json();
}

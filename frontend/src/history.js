// Conversation history persisted in localStorage.
//
// Kept behind this small module so it can later be swapped for a backend store
// (e.g. GET/POST /api/conversations) without touching the components.

const KEY = "docchat:conversations";

function uid() {
  return (crypto.randomUUID && crypto.randomUUID()) || String(Date.now() + Math.random());
}

// On load, any message left mid-stream (from a reload during generation) is
// normalized so it doesn't appear stuck.
function sanitize(conv) {
  return {
    id: conv.id || uid(),
    title: conv.title || "New chat",
    createdAt: conv.createdAt || Date.now(),
    updatedAt: conv.updatedAt || Date.now(),
    messages: (conv.messages || []).map((m) => ({
      ...m,
      status: m.status === "running" ? "done" : m.status,
    })),
  };
}

export function loadConversations() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY));
    return Array.isArray(parsed) ? parsed.map(sanitize) : [];
  } catch {
    return [];
  }
}

export function saveConversations(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    /* quota / private mode — history just won't persist */
  }
}

export function newConversation() {
  const now = Date.now();
  return { id: uid(), title: "New chat", createdAt: now, updatedAt: now, messages: [] };
}

export function titleFrom(text) {
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > 44 ? t.slice(0, 44) + "…" : t || "New chat";
}

// Group conversations into Today / Yesterday / Previous 7 days / Older.
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

// API client for the chatbot backend.
// Credentials are HTTP Basic; we store the base64 token in localStorage.

const BASE = import.meta.env.VITE_API_BASE || "/api";
const STORAGE_KEY = "chatbot_auth";

export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storeAuth(username, token) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ username, token }));
}

export function clearAuth() {
  localStorage.removeItem(STORAGE_KEY);
}

function authHeader() {
  const auth = getStoredAuth();
  return auth ? { Authorization: `Basic ${auth.token}` } : {};
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    throw new ApiError("Unauthorized", 401);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return null;
  return res.json();
}

// --- Auth ------------------------------------------------------------------
export async function login(username, password) {
  const token = btoa(`${username}:${password}`);
  const res = await fetch(`${BASE}/me`, {
    headers: { Authorization: `Basic ${token}` },
  });
  if (res.status === 401) throw new ApiError("Invalid credentials", 401);
  if (!res.ok) throw new ApiError("Login failed", res.status);
  const info = await res.json();
  storeAuth(username, token);
  return info;
}

export async function fetchMe() {
  return request("/me");
}

// --- Conversations ---------------------------------------------------------
export async function listConversations() {
  return request("/conversations");
}

export async function createConversation(payload = {}) {
  return request("/conversations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getConversation(id) {
  return request(`/conversations/${id}`);
}

export async function updateConversation(id, payload) {
  return request(`/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteConversation(id) {
  return request(`/conversations/${id}`, { method: "DELETE" });
}

// --- Streaming chat --------------------------------------------------------
// Sends a message and streams the assistant reply. Calls callbacks:
//   onDelta(text), onDone(messageId), onError(detail)
export async function sendMessageStream(
  conversationId,
  content,
  { onDelta, onDone, onError, signal } = {}
) {
  let res;
  try {
    res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeader(),
      },
      body: JSON.stringify({ content }),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") return;
    onError?.("Network error. Please try again.");
    return;
  }

  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    onError?.(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const json = line.slice("data:".length).trim();
        if (!json) continue;
        let payload;
        try {
          payload = JSON.parse(json);
        } catch {
          continue;
        }
        if (payload.type === "delta") onDelta?.(payload.text);
        else if (payload.type === "done") onDone?.(payload.message_id);
        else if (payload.type === "error") onError?.(payload.detail);
      }
    }
  } catch (err) {
    if (err.name === "AbortError") return;
    onError?.("Streaming connection interrupted.");
  }
}

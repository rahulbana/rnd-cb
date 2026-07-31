// Thin fetch wrapper that attaches the bearer token and parses JSON.

const TOKEN_KEY = "chatbot_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = new URLSearchParams(form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { method, headers, body: payload });

  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || res.statusText || "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  register: (email, username, password) =>
    request("/api/auth/register", {
      method: "POST",
      body: { email, username, password },
    }),

  login: (username, password) =>
    request("/api/auth/login", {
      method: "POST",
      form: { username, password },
    }),

  me: () => request("/api/auth/me"),

  listSessions: () => request("/api/sessions"),
  createSession: () => request("/api/sessions", { method: "POST" }),
  getSession: (id) => request(`/api/sessions/${id}`),
  deleteSession: (id) => request(`/api/sessions/${id}`, { method: "DELETE" }),

  listMemories: () => request("/api/memories"),

  sendChat: (message, sessionId) =>
    request("/api/chat", {
      method: "POST",
      body: { message, session_id: sessionId ?? null },
    }),
};

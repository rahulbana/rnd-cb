import type {
  Conversation,
  DocumentOut,
  IngestAccepted,
  JobOut,
  Message,
  TokenResponse,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8080";
const API = `${BASE_URL}/api/v1`;

const ACCESS_KEY = "rag.access_token";
const REFRESH_KEY = "rag.refresh_token";

export const tokenStore = {
  access: (): string | null => localStorage.getItem(ACCESS_KEY),
  refresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = tokenStore.access();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokenStore.refresh();
  if (!refresh) return false;
  const res = await fetch(`${API}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return false;
  const data = (await res.json()) as { access_token: string };
  tokenStore.set(data.access_token);
  return true;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: authHeaders(init.headers as Record<string, string>),
  });
  if (res.status === 401 && retry && (await refreshAccessToken())) {
    return request<T>(path, init, false);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.error?.message ?? body?.detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  // --- auth ---
  async register(email: string, password: string): Promise<TokenResponse> {
    return request("/auth/register", jsonInit("POST", { email, password }));
  },
  async login(email: string, password: string): Promise<TokenResponse> {
    return request("/auth/login", jsonInit("POST", { email, password }));
  },

  // --- documents ---
  async listDocuments(): Promise<DocumentOut[]> {
    return request("/documents");
  },
  async uploadDocument(file: File): Promise<IngestAccepted> {
    const form = new FormData();
    form.append("file", file);
    return request("/documents", { method: "POST", body: form });
  },
  async deleteDocument(id: string): Promise<void> {
    return request(`/documents/${id}`, { method: "DELETE" });
  },
  async getJob(id: string): Promise<JobOut> {
    return request(`/jobs/${id}`);
  },

  // --- conversations ---
  async listConversations(): Promise<Conversation[]> {
    return request("/conversations");
  },
  async conversationMessages(id: string): Promise<Message[]> {
    return request(`/conversations/${id}/messages`);
  },

  // --- chat streaming (SSE over fetch) ---
  async streamChat(
    question: string,
    conversationId: string | null,
    handlers: {
      onMeta: (meta: { conversation_id: string; found: boolean; citations: unknown[] }) => void;
      onToken: (token: string) => void;
      onDone: () => void;
    },
  ): Promise<void> {
    const res = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ question, conversation_id: conversationId }),
    });
    if (!res.ok || !res.body) {
      throw new ApiError(res.status, "Chat stream failed");
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const lines = frame.split("\n");
        const event = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
        const dataLine = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
        if (!dataLine) continue;
        const data = JSON.parse(dataLine);
        if (event === "meta") handlers.onMeta(data);
        else if (event === "done") handlers.onDone();
        else if (data.token) handlers.onToken(data.token);
      }
    }
    handlers.onDone();
  },
};

export { ApiError };

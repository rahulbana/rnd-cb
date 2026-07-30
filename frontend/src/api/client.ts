import axios from "axios";

const baseURL = (import.meta.env.VITE_API_URL || "") + "/api/v1";

export const api = axios.create({ baseURL });

const TOKEN_KEY = "acw_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

const SESSION_KEY = "acw_session_id";

/** A per-browsing-session id used to group Langfuse traces for one writer. */
export function getSessionId(): string {
  let s = sessionStorage.getItem(SESSION_KEY);
  if (!s) {
    s =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(SESSION_KEY, s);
  }
  return s;
}

// Attach the bearer token and session id to every request.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  config.headers["X-Session-Id"] = getSessionId();
  return config;
});

// On 401, clear the token and bounce to login.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && getToken()) {
      setToken(null);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function apiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    return error.message;
  }
  return fallback;
}

/** Absolute URL for a backend export download (bearer token appended is not
 *  possible via <a>, so exports are fetched as blobs — see articles api). */
export const exportUrl = (id: string, format: string) =>
  `${baseURL}/articles/${id}/export?format=${format}`;

/** Resolve a stored media path (e.g. /media/banners/x.png) to a loadable URL. */
export const mediaUrl = (path: string | null | undefined): string | undefined =>
  path ? `${import.meta.env.VITE_API_URL || ""}${path}` : undefined;

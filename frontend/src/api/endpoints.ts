import { api } from "./client";
import type {
  Article,
  ArticleListItem,
  ArticleUpsert,
  GenerationRequest,
  GenerationResponse,
  SearchResult,
  StyleReference,
  User,
} from "./types";

// --- Auth ---
export async function register(email: string, password: string, full_name?: string) {
  const { data } = await api.post<{ access_token: string }>("/auth/register", {
    email,
    password,
    full_name,
  });
  return data;
}

export async function login(email: string, password: string) {
  // OAuth2 password form expects x-www-form-urlencoded with "username".
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const { data } = await api.post<{ access_token: string }>("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function fetchMe() {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

// --- Articles ---
export async function listArticles(params?: { q?: string; status?: string }) {
  const { data } = await api.get<ArticleListItem[]>("/articles", { params });
  return data;
}

export async function getArticle(id: string) {
  const { data } = await api.get<Article>(`/articles/${id}`);
  return data;
}

export async function createArticle(payload: ArticleUpsert) {
  const { data } = await api.post<Article>("/articles", payload);
  return data;
}

export async function updateArticle(id: string, payload: ArticleUpsert) {
  const { data } = await api.patch<Article>(`/articles/${id}`, payload);
  return data;
}

export async function deleteArticle(id: string) {
  await api.delete(`/articles/${id}`);
}

export async function generateBanner(id: string) {
  const { data } = await api.post<Article>(`/articles/${id}/banner`);
  return data;
}

// --- Generation ---
export async function generateContent(payload: GenerationRequest) {
  const { data } = await api.post<GenerationResponse>("/generate", payload);
  return data;
}

export async function expandContent(payload: {
  title: string;
  body: string;
  mode: string;
  instruction?: string;
}) {
  const { data } = await api.post<{ body: string }>("/generate/expand", payload);
  return data;
}

// --- Style references (writing-style settings) ---
export async function listStyleRefs() {
  const { data } = await api.get<StyleReference[]>("/style-references");
  return data;
}

export async function addStyleLink(url: string) {
  const { data } = await api.post<StyleReference>("/style-references/link", { url });
  return data;
}

export async function uploadStyleFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<StyleReference>("/style-references/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteStyleRef(id: string) {
  await api.delete(`/style-references/${id}`);
}

export async function submitFeedback(payload: {
  trace_id: string;
  name?: string;
  value: number;
  comment?: string;
}) {
  await api.post("/generate/feedback", payload);
}

// --- Search ---
export async function semanticSearch(q: string) {
  const { data } = await api.get<SearchResult[]>("/search", { params: { q } });
  return data;
}

// --- Export (fetched as a blob so the bearer token is sent) ---
export async function downloadExport(id: string, format: string, title: string) {
  const res = await api.get(`/articles/${id}/export`, {
    params: { format },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  const slug = title.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase().slice(0, 60) || "article";
  a.href = url;
  a.download = `${slug}.${format === "markdown" ? "md" : format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

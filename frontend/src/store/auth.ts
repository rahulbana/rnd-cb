import { create } from "zustand";
import { api, tokenStore } from "../lib/api-client";
import type { User } from "../lib/types";

const USER_KEY = "rag.user";

function loadUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: loadUser(),
  isAuthenticated: Boolean(tokenStore.access()),
  error: null,
  async login(email, password) {
    set({ error: null });
    try {
      const res = await api.login(email, password);
      tokenStore.set(res.access_token, res.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.user));
      set({ user: res.user, isAuthenticated: true });
    } catch (e) {
      set({ error: (e as Error).message });
      throw e;
    }
  },
  async register(email, password) {
    set({ error: null });
    try {
      const res = await api.register(email, password);
      tokenStore.set(res.access_token, res.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.user));
      set({ user: res.user, isAuthenticated: true });
    } catch (e) {
      set({ error: (e as Error).message });
      throw e;
    }
  },
  logout() {
    tokenStore.clear();
    localStorage.removeItem(USER_KEY);
    set({ user: null, isAuthenticated: false });
  },
}));

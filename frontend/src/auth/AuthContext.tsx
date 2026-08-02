import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, tokenStore } from "../api/client";
import type { Me } from "../api/types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!tokenStore.access) {
      setMe(null);
      return;
    }
    try {
      setMe(await api.me());
    } catch {
      tokenStore.clear();
      setMe(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await loadMe();
      setLoading(false);
    })();
  }, [loadMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      await api.login(email, password);
      await loadMe();
    },
    [loadMe],
  );

  const logout = useCallback(() => {
    api.logout();
    setMe(null);
  }, []);

  const hasPermission = useCallback(
    (permission: string) => !!me?.permissions.includes(permission),
    [me],
  );

  const value = useMemo<AuthState>(
    () => ({ me, loading, login, logout, refresh: loadMe, hasPermission }),
    [me, loading, login, logout, loadMe, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

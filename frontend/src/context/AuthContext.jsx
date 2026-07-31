import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function bootstrap() {
      if (getToken()) {
        try {
          const me = await api.me();
          setUser(me);
        } catch {
          setToken(null);
        }
      }
      setLoading(false);
    }
    bootstrap();
  }, []);

  async function login(username, password) {
    const data = await api.login(username, password);
    setToken(data.access_token);
    setUser(data.user);
  }

  async function register(email, username, password) {
    const data = await api.register(email, username, password);
    setToken(data.access_token);
    setUser(data.user);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

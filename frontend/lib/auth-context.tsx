"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearToken, setToken, type User } from "./api";

type AuthCtx = {
  user: User | null;
  loading: boolean;
  loginDev: (email: string) => Promise<void>;
  loginGoogle: () => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const u = await api.me();
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loginDev = async (email: string) => {
    const res = await api.devLogin(email);
    setToken(res.access_token);
    setUser(res.user);
  };

  const loginGoogle = async () => {
    const { url, dev_login } = await api.googleAuthUrl();
    if (url) {
      window.location.href = url;
    } else if (dev_login) {
      throw new Error("DEV_LOGIN");
    }
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginDev, loginGoogle, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

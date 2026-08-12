"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createContext, useContext } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import type { User } from "@/lib/types";

interface SessionResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  request: <T>(path: string, options?: RequestInit) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const tokenRef = useRef<string | null>(null);
  const refreshRef = useRef<Promise<string> | null>(null);

  const renew = useCallback(async (): Promise<string> => {
    if (!refreshRef.current) {
      refreshRef.current = apiRequest<SessionResponse>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({}),
      })
        .then((session) => {
          tokenRef.current = session.access_token;
          setUser(session.user);
          return session.access_token;
        })
        .finally(() => {
          refreshRef.current = null;
        });
    }
    return refreshRef.current;
  }, []);

  useEffect(() => {
    renew()
      .catch(() => {
        tokenRef.current = null;
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [renew]);

  const login = useCallback(async (email: string, password: string) => {
    const session = await apiRequest<SessionResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    tokenRef.current = session.access_token;
    setUser(session.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST", body: JSON.stringify({}) });
    } finally {
      tokenRef.current = null;
      setUser(null);
    }
  }, []);

  const request = useCallback(
    async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
      try {
        return await apiRequest<T>(path, options, tokenRef.current);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error;
        const token = await renew();
        return apiRequest<T>(path, options, token);
      }
    },
    [renew],
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, request }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe utilizarse dentro de AuthProvider");
  return context;
}


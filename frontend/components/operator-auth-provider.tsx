"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import type { PlatformOperator } from "@/lib/types";

interface OperatorSessionResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  operator: PlatformOperator;
}

interface OperatorAuthContextValue {
  operator: PlatformOperator | null;
  loading: boolean;
  login: (email: string, password: string, totpCode: string) => Promise<void>;
  logout: () => Promise<void>;
  request: <T>(path: string, options?: RequestInit) => Promise<T>;
}

const OperatorAuthContext = createContext<OperatorAuthContextValue | null>(null);

export function OperatorAuthProvider({ children }: { children: React.ReactNode }) {
  const [operator, setOperator] = useState<PlatformOperator | null>(null);
  const [loading, setLoading] = useState(true);
  const tokenRef = useRef<string | null>(null);
  const refreshRef = useRef<Promise<string> | null>(null);

  const renew = useCallback(async (): Promise<string> => {
    if (!refreshRef.current) {
      refreshRef.current = apiRequest<OperatorSessionResponse>("/operator-auth/refresh", {
        method: "POST",
        body: JSON.stringify({}),
      })
        .then((session) => {
          tokenRef.current = session.access_token;
          setOperator(session.operator);
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
        setOperator(null);
      })
      .finally(() => setLoading(false));
  }, [renew]);

  const login = useCallback(async (email: string, password: string, totpCode: string) => {
    const session = await apiRequest<OperatorSessionResponse>("/operator-auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, totp_code: totpCode }),
    });
    tokenRef.current = session.access_token;
    setOperator(session.operator);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiRequest("/operator-auth/logout", { method: "POST", body: JSON.stringify({}) });
    } finally {
      tokenRef.current = null;
      setOperator(null);
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
    <OperatorAuthContext.Provider value={{ operator, loading, login, logout, request }}>
      {children}
    </OperatorAuthContext.Provider>
  );
}

export function useOperatorAuth(): OperatorAuthContextValue {
  const context = useContext(OperatorAuthContext);
  if (!context) throw new Error("useOperatorAuth debe utilizarse dentro de OperatorAuthProvider");
  return context;
}

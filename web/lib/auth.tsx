"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken, setToken } from "./api";

interface AuthState {
  email: string | null;
  forwardingAddress: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  const [forwardingAddress, setForwardingAddress] = useState<string | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  async function refresh() {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setEmail(me.email);
      setForwardingAddress(me.forwarding_address);
    } catch {
      clearToken();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function signIn(email: string, password: string) {
    const { token } = await api.login(email, password);
    setToken(token);
    await refresh();
    router.push("/sale");
  }

  async function signUp(email: string, password: string) {
    const { token } = await api.signup(email, password);
    setToken(token);
    await refresh();
    router.push("/sale");
  }

  function signOut() {
    clearToken();
    setEmail(null);
    setForwardingAddress(null);
    router.push("/");
  }

  return (
    <AuthContext.Provider
      value={{ email, forwardingAddress, loading, signIn, signUp, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

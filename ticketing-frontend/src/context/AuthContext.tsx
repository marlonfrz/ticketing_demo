import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { getMeRequest, loginRequest } from "../features/auth/api/authApi";
import type { LoginCredentials } from "../features/auth/api/authApi";
import type { User } from "../types/domain";
import { AuthContext, type AuthContextValue } from "./auth-context";
import {
  clearServerSession,
  createServerSession,
} from "../features/auth/api/sessionApi";
import { isUnauthorizedError } from "../api/errors";

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const loadUser = async () => {
      try {
        const me = await getMeRequest();
        if (!cancelled) setUser(me);
      } catch (error) {
        if (!isUnauthorizedError(error)) {
          console.error("Error cargando usuario:", error);
        }
        void clearServerSession();
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    };

    void loadUser();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async ({ email, password }: LoginCredentials) => {
    const data = await loginRequest({ email, password });
    try {
      await createServerSession(data.access_token);
      const me = await getMeRequest();
      setUser(me);
      return me;
    } catch (error) {
      await clearServerSession().catch(() => undefined);
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    setUser(null);
    await clearServerSession().catch(() => undefined);
  }, []);

  const roles = useMemo(() => user?.roles ?? [], [user]);

  const isAuthenticated = !!user;
  const isPromoter = roles.includes("promoter");
  const isAdmin = roles.includes("admin");
  const canAccessPromoter = isPromoter || isAdmin;

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      setUser,
      authLoading,
      isAuthenticated,
      roles,
      isPromoter,
      isAdmin,
      canAccessPromoter,
      login,
      logout,
    }),
    [
      user,
      authLoading,
      isAuthenticated,
      roles,
      isPromoter,
      isAdmin,
      canAccessPromoter,
      login,
      logout,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

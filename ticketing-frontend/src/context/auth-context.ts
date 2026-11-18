import { createContext, type Dispatch, type SetStateAction } from "react";

import type { LoginCredentials } from "../features/auth/api/authApi";
import type { User } from "../types/domain";

export type AuthContextValue = {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  authLoading: boolean;
  isAuthenticated: boolean;
  roles: string[];
  isPromoter: boolean;
  isAdmin: boolean;
  canAccessPromoter: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

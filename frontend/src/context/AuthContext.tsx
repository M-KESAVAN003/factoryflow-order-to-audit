import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError, getStoredToken, setStoredToken } from "../lib/api";
import {
  clearOfflineCachesOnLogout,
  getSessionMeta,
  saveSessionMeta,
} from "../lib/offlineDb";
import { UserProfile } from "../types/auth";

interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  isOfflineSession: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function persistOfflineProfile(profile: UserProfile): Promise<void> {
  return saveSessionMeta({
    key: "active_session",
    userId: profile.id,
    email: profile.email,
    fullName: profile.full_name,
    department: profile.department,
    role: profile.role,
    roleDisplayName: profile.role_display_name,
    permissions: profile.permissions,
    lastAuthenticatedAt: new Date().toISOString(),
    lastMasterSyncAt: null,
  }).catch(() => undefined);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isOfflineSession, setIsOfflineSession] = useState<boolean>(false);

  const refreshUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setIsOfflineSession(false);
      setLoading(false);
      return;
    }
    try {
      const profile = await api.me();
      setUser(profile);
      setIsOfflineSession(false);
      void persistOfflineProfile(profile);
    } catch (err) {
      const isAuthFailure = err instanceof ApiError && (err.status === 401 || err.status === 403);
      if (!isAuthFailure) {
        const cached = await getSessionMeta().catch(() => null);
        if (cached) {
          setUser({
            id: cached.userId,
            email: cached.email,
            full_name: cached.fullName,
            department: cached.department,
            role: cached.role,
            role_display_name: cached.roleDisplayName,
            is_active: true,
            permissions: cached.permissions,
            created_at: cached.lastAuthenticatedAt,
            last_login_at: cached.lastAuthenticatedAt,
          });
          setIsOfflineSession(true);
          setLoading(false);
          return;
        }
      }
      setStoredToken(null);
      setUser(null);
      setIsOfflineSession(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    setStoredToken(result.access_token);
    setUser(result.user);
    setIsOfflineSession(false);
    void persistOfflineProfile(result.user);
    return result.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getStoredToken()) {
        await api.logout();
      }
    } catch {
      // Clear local session cleanly even when server logout call fails
    } finally {
      setStoredToken(null);
      setUser(null);
      setIsOfflineSession(false);
      await clearOfflineCachesOnLogout().catch(() => undefined);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, isOfflineSession, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return context;
}

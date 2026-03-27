import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { api } from '@/utils/api';
import type { AuthContextState } from '@/types/aurora';

const AuthContext = createContext<AuthContextState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthContextState>({
    isAuthenticated: false,
    user: null,
    permissions: [],
    sessionToken: null,
    subscription: null,
  });

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.auth.login(email, password);
    const profile = await api.auth.me(access_token);
    setState({
      isAuthenticated: true,
      sessionToken: access_token,
      user: {
        id: profile.id,
        email: profile.email,
        displayName: profile.display_name,
        role: 'user',
      },
      permissions: ['upload', 'render', 'colab'],
      subscription: {
        state: 'active',
        tier: profile.subscription_tier as AuthContextState['subscription'] extends null ? never : NonNullable<AuthContextState['subscription']>['tier'],
        tracksUsed: profile.tracks_used,
        trackLimit: profile.track_limit,
        storageUsedBytes: profile.storage_used_bytes,
        storageLimitBytes: profile.storage_limit_bytes,
      },
    });
    localStorage.setItem('aurora_token', access_token);
  }, []);

  const logout = useCallback(() => {
    setState({
      isAuthenticated: false,
      user: null,
      permissions: [],
      sessionToken: null,
      subscription: null,
    });
    localStorage.removeItem('aurora_token');
  }, []);

  // Restore session from localStorage
  useEffect(() => {
    const token = localStorage.getItem('aurora_token');
    if (!token) return;
    api.auth.me(token)
      .then((profile) => {
        setState({
          isAuthenticated: true,
          sessionToken: token,
          user: {
            id: profile.id,
            email: profile.email,
            displayName: profile.display_name,
            role: 'user',
          },
          permissions: ['upload', 'render', 'colab'],
          subscription: {
            state: 'active',
            tier: profile.subscription_tier as NonNullable<AuthContextState['subscription']>['tier'],
            tracksUsed: profile.tracks_used,
            trackLimit: profile.track_limit,
            storageUsedBytes: profile.storage_used_bytes,
            storageLimitBytes: profile.storage_limit_bytes,
          },
        });
      })
      .catch(() => localStorage.removeItem('aurora_token'));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout } as AuthContextState & { login: typeof login; logout: typeof logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx as AuthContextState & { login: (email: string, password: string) => Promise<void>; logout: () => void };
}

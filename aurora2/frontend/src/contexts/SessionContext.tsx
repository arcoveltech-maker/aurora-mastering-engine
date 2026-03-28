import React, { createContext, useContext } from 'react';
import { useSessionStore } from '@/stores/sessionStore';

// Re-export the store as context for legacy component compatibility
const SessionContext = createContext<ReturnType<typeof useSessionStore> | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const store = useSessionStore();
  return <SessionContext.Provider value={store}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
}

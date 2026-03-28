import { createContext, useContext, useState, ReactNode } from 'react';

interface SessionCtx { sessionId: string | null; setSessionId: (id: string | null) => void; }

const SessionContext = createContext<SessionCtx>({ sessionId: null, setSessionId: () => {} });

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  return (
    <SessionContext.Provider value={{ sessionId, setSessionId }}>
      {children}
    </SessionContext.Provider>
  );
}
export function useSession() { return useContext(SessionContext); }

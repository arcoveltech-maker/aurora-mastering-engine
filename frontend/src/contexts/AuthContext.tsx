import { createContext, useContext, useState, ReactNode } from 'react';

interface User { id: string; email: string; display_name: string; tier: string; }
interface AuthCtx { user: User | null; login: (u: User) => void; logout: () => void; }

const AuthContext = createContext<AuthCtx>({ user: null, login: () => {}, logout: () => {} });

const DEMO_USER: User = { id: 'demo', email: 'demo@aurora.ai', display_name: 'DEMOS INTONICS_FT', tier: 'pro' };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEMO_USER);
  return (
    <AuthContext.Provider value={{ user, login: setUser, logout: () => setUser(null) }}>
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() { return useContext(AuthContext); }

import { createContext, useContext, useState, ReactNode, useCallback } from 'react';

interface Toast { id: number; message: string; type?: string; }
interface ToastCtx { showToast: (msg: string, type?: string) => void; }

const ToastContext = createContext<ToastCtx>({ showToast: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const showToast = useCallback((message: string, type = 'info') => {
    const id = Date.now();
    setToasts(t => [...t, { id, message, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3000);
  }, []);
  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div style={{ position: 'fixed', bottom: 16, right: 16, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {toasts.map(t => (
          <div key={t.id} style={{ background: '#111318', border: '1px solid #9dff7c', color: '#ccd6f6', padding: '8px 14px', borderRadius: 4, fontFamily: 'monospace', fontSize: 12 }}>{t.message}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
export function useToast() { return useContext(ToastContext); }

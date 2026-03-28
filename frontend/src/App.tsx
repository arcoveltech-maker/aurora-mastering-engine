import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { SessionProvider } from '@/contexts/SessionContext';
import { MasteringApp } from '@/components/MasteringApp';
import { ToastContainer } from '@/components/common/Toast';

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <SessionProvider>
            <MasteringApp />
            <ToastContainer />
          </SessionProvider>
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

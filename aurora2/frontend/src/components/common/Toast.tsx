import { useToast } from '@/contexts/ToastContext';
import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from 'lucide-react';

const icons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertCircle,
};

const colors = {
  info: 'border-blue-500 bg-blue-950/80',
  success: 'border-green-500 bg-green-950/80',
  warning: 'border-yellow-500 bg-yellow-950/80',
  error: 'border-red-500 bg-red-950/80',
};

const iconColors = {
  info: 'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
};

export function ToastContainer() {
  const { toasts, removeToast } = useToast();
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80">
      {toasts.map((t) => {
        const Icon = icons[t.type];
        return (
          <div
            key={t.id}
            className={`flex items-start gap-3 p-3 rounded-lg border backdrop-blur-sm text-sm text-white animate-in slide-in-from-right ${colors[t.type]}`}
          >
            <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconColors[t.type]}`} />
            <span className="flex-1">{t.message}</span>
            <button onClick={() => removeToast(t.id)} className="shrink-0 text-white/50 hover:text-white">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

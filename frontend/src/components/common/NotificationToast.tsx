import React, { useEffect } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  ShieldAlert,
  FileCode,
  Wrench,
  X,
} from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';
import type { Notification, NotificationCategory, NotificationSeverity } from '../../types/notification';

export const NotificationToastContainer: React.FC = () => {
  const toastQueue = useNotificationStore((state) => state.toastQueue);
  const removeToast = useNotificationStore((state) => state.removeToast);

  if (toastQueue.length === 0) return null;

  // Show at most 3 recent toasts simultaneously
  const visibleToasts = toastQueue.slice(-3);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {visibleToasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
};

interface ToastItemProps {
  toast: Notification;
  onClose: () => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const getToastIcon = (category: NotificationCategory, severity: NotificationSeverity) => {
    switch (category) {
      case 'PERMISSION':
        return <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />;
      case 'ARTIFACT':
        return <FileCode className="w-5 h-5 text-emerald-400 shrink-0" />;
      case 'HEALING':
        return <Wrench className="w-5 h-5 text-purple-400 shrink-0" />;
      default:
        if (severity === 'ERROR') return <XCircle className="w-5 h-5 text-rose-400 shrink-0" />;
        if (severity === 'SUCCESS') return <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />;
        if (severity === 'WARNING') return <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />;
        return <Info className="w-5 h-5 text-sky-400 shrink-0" />;
    }
  };

  const getBorderColor = (severity: NotificationSeverity) => {
    switch (severity) {
      case 'ERROR':
        return 'border-rose-500/40 bg-rose-950/80';
      case 'WARNING':
        return 'border-amber-500/40 bg-amber-950/80';
      case 'SUCCESS':
        return 'border-emerald-500/40 bg-emerald-950/80';
      default:
        return 'border-sky-500/40 bg-slate-900/90';
    }
  };

  return (
    <div
      className={`pointer-events-auto p-4 rounded-xl border glass-panel shadow-2xl flex items-start gap-3 text-xs animate-in slide-in-from-bottom-5 duration-200 ${getBorderColor(
        toast.severity
      )}`}
    >
      {getToastIcon(toast.category, toast.severity)}
      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-slate-100 mb-0.5">{toast.title}</h4>
        <p className="text-slate-300 text-[11px] leading-relaxed break-words">{toast.message}</p>
      </div>
      <button
        onClick={onClose}
        className="text-slate-400 hover:text-slate-200 p-0.5 rounded hover:bg-white/10 transition-colors shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

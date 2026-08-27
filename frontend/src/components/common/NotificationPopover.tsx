import React, { useRef, useEffect } from 'react';
import {
  Bell,
  CheckCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  ShieldAlert,
  FileCode,
  Activity,
  Wrench,
  X,
} from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';
import type { NotificationCategory, NotificationSeverity } from '../../types/notification';

interface NotificationPopoverProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationPopover: React.FC<NotificationPopoverProps> = ({ isOpen, onClose }) => {
  const popoverRef = useRef<HTMLDivElement>(null);
  const notifications = useNotificationStore((state) => state.notifications);
  const unreadCount = useNotificationStore((state) => state.unreadCount);
  const activeFilter = useNotificationStore((state) => state.activeFilter);
  const setActiveFilter = useNotificationStore((state) => state.setActiveFilter);
  const markAsRead = useNotificationStore((state) => state.markAsRead);
  const markAllAsRead = useNotificationStore((state) => state.markAllAsRead);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredNotifications = notifications.filter((n) => {
    if (activeFilter === 'ALL') return true;
    if (activeFilter === 'UNREAD') return !n.read;
    return n.category === activeFilter;
  });

  const getCategoryIcon = (category: NotificationCategory, severity: NotificationSeverity) => {
    switch (category) {
      case 'PERMISSION':
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case 'ARTIFACT':
        return <FileCode className="w-4 h-4 text-emerald-400" />;
      case 'HEALING':
        return <Wrench className="w-4 h-4 text-purple-400" />;
      case 'TASK':
        return severity === 'ERROR' ? (
          <XCircle className="w-4 h-4 text-rose-400" />
        ) : (
          <CheckCircle2 className="w-4 h-4 text-sky-400" />
        );
      case 'WORKFLOW':
      default:
        if (severity === 'ERROR') return <XCircle className="w-4 h-4 text-rose-400" />;
        if (severity === 'SUCCESS') return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
        if (severity === 'WARNING') return <AlertTriangle className="w-4 h-4 text-amber-400" />;
        return <Info className="w-4 h-4 text-sky-400" />;
    }
  };

  const formatTimestamp = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const diffMs = Date.now() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 60) return 'Just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h ago`;
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div
      ref={popoverRef}
      className="absolute right-0 top-12 w-96 max-w-[calc(100vw-2rem)] glass-panel border border-slate-800 rounded-xl shadow-2xl z-50 overflow-hidden text-xs animate-in fade-in zoom-in-95 duration-150"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-slate-200">Notifications</span>
          {unreadCount > 0 && (
            <span className="bg-sky-500/20 text-sky-300 font-mono text-[10px] font-bold px-1.5 py-0.5 rounded-full border border-sky-500/30">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <button
              onClick={() => markAllAsRead()}
              className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-sky-300 px-2 py-1 rounded hover:bg-slate-800/60 transition-colors"
              title="Mark all as read"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              <span>Mark all read</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-slate-800/50 bg-slate-950/40 overflow-x-auto no-scrollbar font-mono text-[11px]">
        {(['ALL', 'UNREAD', 'WORKFLOW', 'PERMISSION', 'TASK', 'ARTIFACT', 'HEALING'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveFilter(tab)}
            className={`px-2.5 py-1 rounded-md capitalize whitespace-nowrap transition-colors ${
              activeFilter === tab
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30 font-medium'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            {tab.toLowerCase()}
          </button>
        ))}
      </div>

      {/* Notification List */}
      <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/40">
        {filteredNotifications.length === 0 ? (
          <div className="p-8 text-center text-slate-500 font-mono">
            <Activity className="w-6 h-6 mx-auto mb-2 opacity-40 text-slate-400" />
            <p>No notifications available</p>
          </div>
        ) : (
          filteredNotifications.map((n) => (
            <div
              key={n.id}
              onClick={() => !n.read && markAsRead(n.id)}
              className={`p-3.5 transition-colors cursor-pointer flex gap-3 ${
                !n.read ? 'bg-slate-900/60 hover:bg-slate-800/60' : 'opacity-75 hover:opacity-100 hover:bg-slate-900/40'
              }`}
            >
              <div className="mt-0.5 shrink-0">{getCategoryIcon(n.category, n.severity)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className={`font-medium ${!n.read ? 'text-slate-100' : 'text-slate-300'}`}>
                    {n.title}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 shrink-0">
                    {formatTimestamp(n.timestamp)}
                  </span>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed break-words">{n.message}</p>
                {n.workflow_id && (
                  <span className="inline-block mt-1 font-mono text-[9px] text-slate-500 bg-slate-950/60 px-1.5 py-0.5 rounded border border-slate-800">
                    ID: {n.workflow_id}
                  </span>
                )}
              </div>
              {!n.read && <div className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0 mt-1.5" />}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

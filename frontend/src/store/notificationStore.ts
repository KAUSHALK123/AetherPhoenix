import { create } from 'zustand';
import type { Notification, NotificationCategory } from '../types/notification';
import { notificationService } from '../services/notificationService';

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  toastQueue: Notification[];
  isConnected: boolean;
  activeFilter: 'ALL' | 'UNREAD' | NotificationCategory;
  
  // Actions
  fetchNotifications: () => Promise<void>;
  addNotification: (notification: Notification) => void;
  removeToast: (id: string) => void;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  setActiveFilter: (filter: 'ALL' | 'UNREAD' | NotificationCategory) => void;
  connectWebSocket: () => () => void;
}

let socketInstance: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  toastQueue: [],
  isConnected: false,
  activeFilter: 'ALL',

  fetchNotifications: async () => {
    try {
      const list = await notificationService.getNotifications();
      const unread = list.filter((n) => !n.read).length;
      set({ notifications: list, unreadCount: unread });
    } catch (err) {
      console.warn('Could not fetch initial notification history:', err);
    }
  },

  addNotification: (notification: Notification) => {
    set((state) => {
      // Avoid duplicate notification IDs
      if (state.notifications.some((n) => n.id === notification.id)) {
        return state;
      }

      const updated = [notification, ...state.notifications];
      const unread = updated.filter((n) => !n.read).length;
      const updatedToastQueue = [...state.toastQueue, notification];

      return {
        notifications: updated,
        unreadCount: unread,
        toastQueue: updatedToastQueue,
      };
    });
  },

  removeToast: (id: string) => {
    set((state) => ({
      toastQueue: state.toastQueue.filter((t) => t.id !== id),
    }));
  },

  markAsRead: async (id: string) => {
    set((state) => {
      const updated = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      );
      return {
        notifications: updated,
        unreadCount: updated.filter((n) => !n.read).length,
      };
    });

    try {
      await notificationService.markAsRead(id);
    } catch (err) {
      console.error('Failed to mark notification as read on backend:', err);
    }
  },

  markAllAsRead: async () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    }));

    try {
      await notificationService.markAllAsRead();
    } catch (err) {
      console.error('Failed to mark all notifications as read on backend:', err);
    }
  },

  setActiveFilter: (filter) => set({ activeFilter: filter }),

  connectWebSocket: () => {
    const connect = () => {
      if (socketInstance && (socketInstance.readyState === WebSocket.OPEN || socketInstance.readyState === WebSocket.CONNECTING)) {
        return;
      }

      socketInstance = notificationService.connectWebSocket(
        (notification) => {
          get().addNotification(notification);
        },
        () => {
          set({ isConnected: false });
        },
        () => {
          set({ isConnected: false });
          // Reconnect after 3 seconds
          reconnectTimer = setTimeout(() => {
            connect();
          }, 3000);
        }
      );

      socketInstance.onopen = () => {
        set({ isConnected: true });
      };
    };

    connect();
    get().fetchNotifications();

    // Cleanup function
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socketInstance) {
        socketInstance.close();
        socketInstance = null;
      }
    };
  },
}));

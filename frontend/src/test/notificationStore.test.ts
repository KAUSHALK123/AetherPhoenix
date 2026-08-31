import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useNotificationStore } from '../store/notificationStore';
import { notificationService } from '../services/notificationService';
import type { Notification } from '../types/notification';

vi.mock('../services/notificationService', () => ({
  notificationService: {
    getNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
    connectWebSocket: vi.fn(),
  },
}));

describe('notificationStore useNotificationStore', () => {
  beforeEach(() => {
    // Reset Zustand state manually
    useNotificationStore.setState({
      notifications: [],
      unreadCount: 0,
      toastQueue: [],
      isConnected: false,
      activeFilter: 'ALL',
    });
    vi.clearAllMocks();
  });

  it('starts with default initial empty notifications', () => {
    const state = useNotificationStore.getState();
    expect(state.notifications).toEqual([]);
    expect(state.unreadCount).toBe(0);
    expect(state.toastQueue).toEqual([]);
  });

  it('addNotification adds notification and increases unreadCount and toastQueue', () => {
    const mockNotification: Notification = {
      id: 'notif-1',
      event_type: 'test-event',
      title: 'New Notification',
      message: 'Workflow started',
      read: false,
      category: 'WORKFLOW',
      severity: 'INFO',
      timestamp: new Date().toISOString(),
    };

    useNotificationStore.getState().addNotification(mockNotification);

    const state = useNotificationStore.getState();
    expect(state.notifications.length).toBe(1);
    expect(state.notifications[0]).toEqual(mockNotification);
    expect(state.unreadCount).toBe(1);
    expect(state.toastQueue).toEqual([mockNotification]);
  });

  it('addNotification avoids duplicate notification IDs', () => {
    const mockNotification: Notification = {
      id: 'notif-dup',
      event_type: 'test-event',
      title: 'Dup Title',
      message: 'Dup Message',
      read: false,
      category: 'WORKFLOW',
      severity: 'INFO',
      timestamp: new Date().toISOString(),
    };

    useNotificationStore.getState().addNotification(mockNotification);
    useNotificationStore.getState().addNotification(mockNotification);

    const state = useNotificationStore.getState();
    expect(state.notifications.length).toBe(1);
    expect(state.unreadCount).toBe(1);
  });

  it('removeToast removes notification from toastQueue', () => {
    const mockNotification: Notification = {
      id: 'notif-toast',
      event_type: 'test-event',
      title: 'New Notification',
      message: 'Workflow started',
      read: false,
      category: 'WORKFLOW',
      severity: 'INFO',
      timestamp: new Date().toISOString(),
    };

    useNotificationStore.getState().addNotification(mockNotification);
    expect(useNotificationStore.getState().toastQueue.length).toBe(1);

    useNotificationStore.getState().removeToast('notif-toast');
    expect(useNotificationStore.getState().toastQueue.length).toBe(0);
  });

  it('markAsRead updates notification status and unreadCount', async () => {
    const mockNotification: Notification = {
      id: 'notif-read',
      event_type: 'test-event',
      title: 'New Notification',
      message: 'Workflow started',
      read: false,
      category: 'WORKFLOW',
      severity: 'INFO',
      timestamp: new Date().toISOString(),
    };

    vi.mocked(notificationService.markAsRead).mockResolvedValue(undefined);

    useNotificationStore.getState().addNotification(mockNotification);
    expect(useNotificationStore.getState().unreadCount).toBe(1);

    await useNotificationStore.getState().markAsRead('notif-read');

    const state = useNotificationStore.getState();
    expect(state.notifications[0].read).toBe(true);
    expect(state.unreadCount).toBe(0);
    expect(notificationService.markAsRead).toHaveBeenCalledWith('notif-read');
  });

  it('markAllAsRead updates all notifications and resets unreadCount', async () => {
    const n1: Notification = {
      id: 'n1',
      event_type: 'test-event',
      title: 'n1',
      message: 'm1',
      read: false,
      category: 'WORKFLOW',
      severity: 'INFO',
      timestamp: new Date().toISOString(),
    };
    const n2: Notification = {
      id: 'n2',
      event_type: 'test-event',
      title: 'n2',
      message: 'm2',
      read: false,
      category: 'WORKFLOW',
      severity: 'INFO',
      timestamp: new Date().toISOString(),
    };

    vi.mocked(notificationService.markAllAsRead).mockResolvedValue(undefined);

    useNotificationStore.getState().addNotification(n1);
    useNotificationStore.getState().addNotification(n2);
    expect(useNotificationStore.getState().unreadCount).toBe(2);

    await useNotificationStore.getState().markAllAsRead();

    const state = useNotificationStore.getState();
    expect(state.notifications.every((n) => n.read)).toBe(true);
    expect(state.unreadCount).toBe(0);
    expect(notificationService.markAllAsRead).toHaveBeenCalled();
  });
});

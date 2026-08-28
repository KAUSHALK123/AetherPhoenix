import { API_BASE_URL, request } from './apiClient';
import type { Notification, NotificationFilter } from '../types/notification';

export const notificationService = {
  /**
   * Fetch notification history from backend REST API
   */
  async getNotifications(filter: NotificationFilter = {}): Promise<Notification[]> {
    const params = new URLSearchParams();
    if (filter.workflow_id) params.append('workflow_id', filter.workflow_id);
    if (filter.unread_only) params.append('unread_only', 'true');

    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Notification[]>(`/api/v1/notifications${query}`);
  },

  /**
   * Mark a single notification as read
   */
  async markAsRead(notificationId: string): Promise<void> {
    await request(`/api/v1/notifications/${notificationId}/read`, {
      method: 'POST',
    });
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(): Promise<void> {
    await request('/api/v1/notifications/read-all', {
      method: 'POST',
    });
  },

  /**
   * Open WebSocket connection for real-time notification streaming
   */
  connectWebSocket(
    onMessage: (notification: Notification) => void,
    onError?: (event: Event) => void,
    onClose?: (event: CloseEvent) => void
  ): WebSocket {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/api/v1/notifications/ws';
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const notification: Notification = JSON.parse(event.data);
        if (notification && notification.id) {
          onMessage(notification);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket notification payload:', err);
      }
    };

    if (onError) ws.onerror = onError;
    if (onClose) ws.onclose = onClose;

    return ws;
  },
};

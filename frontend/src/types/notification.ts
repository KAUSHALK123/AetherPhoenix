export type NotificationCategory = 'WORKFLOW' | 'PERMISSION' | 'TASK' | 'ARTIFACT' | 'HEALING';

export type NotificationSeverity = 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';

export interface Notification {
  id: string;
  event_id?: string | null;
  workflow_id?: string | null;
  task_id?: string | null;
  event_type: string;
  title: string;
  message: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  timestamp: string;
  read: boolean;
  payload?: Record<string, any>;
}

export interface NotificationFilter {
  workflow_id?: string;
  unread_only?: boolean;
  category?: NotificationCategory;
}

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type PermissionStatus =
  | 'PENDING'
  | 'GRANTED'
  | 'APPROVED'
  | 'DENIED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'REVOKED';

export interface PermissionRequest {
  request_id: string;
  workflow_id: string;
  task_id?: string;
  permission_type: string;
  reason: string;
  risk_level: RiskLevel;
  status: PermissionStatus;
  requested_at?: string;
  expires_at?: string;
  resolved_at?: string;
  message?: string;
  context?: Record<string, unknown>;
}

export interface PermissionResponse {
  request_id: string;
  status: PermissionStatus;
  message?: string;
}

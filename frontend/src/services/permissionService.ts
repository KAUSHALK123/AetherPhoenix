import { request } from './apiClient';
import type { PermissionRequest, PermissionResponse } from '../types/permission';

export const permissionService = {
  /**
   * Fetches pending permission requests: GET /api/v1/permissions/pending
   */
  async getPendingPermissions(): Promise<PermissionRequest[]> {
    return request<PermissionRequest[]>('/api/v1/permissions/pending');
  },

  /**
   * Fetches all permission requests: GET /api/v1/permissions
   */
  async getAllPermissions(): Promise<PermissionRequest[]> {
    return request<PermissionRequest[]>('/api/v1/permissions');
  },

  /**
   * Approves a pending permission request: POST /api/v1/permissions/{request_id}/approve
   */
  async approvePermission(requestId: string, message?: string): Promise<PermissionResponse> {
    const query = message ? `?message=${encodeURIComponent(message)}` : '';
    return request<PermissionResponse>(`/api/v1/permissions/${requestId}/approve${query}`, {
      method: 'POST',
    });
  },

  /**
   * Rejects a pending permission request: POST /api/v1/permissions/{request_id}/reject
   */
  async rejectPermission(requestId: string, message?: string): Promise<PermissionResponse> {
    const query = message ? `?message=${encodeURIComponent(message)}` : '';
    return request<PermissionResponse>(`/api/v1/permissions/${requestId}/reject${query}`, {
      method: 'POST',
    });
  },
};

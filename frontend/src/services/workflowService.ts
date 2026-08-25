import { request } from './apiClient';
import type { WorkflowState } from '../types/workflow';

export const workflowService = {
  /**
   * Fetches workflows from dashboard endpoint: GET /api/v1/dashboard/workflows
   */
  async getWorkflows(): Promise<WorkflowState[]> {
    try {
      return await request<WorkflowState[]>('/api/v1/dashboard/workflows');
    } catch {
      // Return empty list if no active backend workflows exist yet
      return [];
    }
  },

  /**
   * Fetches single workflow: GET /api/v1/dashboard/workflows/{workflow_id}
   */
  async getWorkflowById(workflowId: string): Promise<WorkflowState | null> {
    try {
      return await request<WorkflowState>(`/api/v1/dashboard/workflows/${workflowId}`);
    } catch {
      return null;
    }
  },
};

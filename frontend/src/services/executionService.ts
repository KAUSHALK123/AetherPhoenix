import { request } from './apiClient';
import type { ExecuteWorkflowRequest, ExecuteWorkflowResponse } from '../types/execution';

export const executionService = {
  /**
   * Submits an approved PlannerOutput JSON for real backend execution.
   * POST /api/v1/workflows/execute
   *
   * Non-blocking on the backend — returns workflow_id immediately.
   * Frontend polls /api/v1/dashboard/workflows/{workflow_id} for status.
   */
  async executeWorkflow(
    planJson: string,
    sessionId?: string,
    executionMode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS' = 'ASSISTED'
  ): Promise<ExecuteWorkflowResponse> {
    const payload: ExecuteWorkflowRequest = {
      plan_json: planJson,
      session_id: sessionId || undefined,
      execution_mode: executionMode,
    };

    return request<ExecuteWorkflowResponse>('/api/v1/workflows/execute', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};


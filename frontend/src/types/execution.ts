/** Request body for POST /api/v1/workflows/execute */
export interface ExecuteWorkflowRequest {
  plan_json: string;
  session_id?: string;
  execution_mode?: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';
}

/** Immediate response from execute endpoint */
export interface ExecuteWorkflowResponse {
  workflow_id: string;
  status: string;
  message: string;
}


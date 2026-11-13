/**
 * Aligns with the real backend _serialize_state() output from
 * app/services/observability.py
 */
export type WorkflowStatus =
  | 'CREATED'
  | 'PLANNING'
  | 'READY'
  | 'RUNNING'
  | 'PAUSED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'ESCALATED'
  | 'BLOCKED'
  | 'PENDING';

export interface WorkflowTaskDetail {
  task_id: string;
  task_name: string;
  description: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'SKIPPED' | string;
  retry_count: number;
  dependencies: string[];
  permissions: string[];
  risk_level: string;
  category: string;
}

export interface ValidationDetail {
  task_id: string;
  workflow_id: string;
  is_valid: boolean;
  decision: string;
  checks: Record<string, boolean>;
  issues: string[];
}

/** Maps to the serialized workflow state from /api/v1/dashboard/workflows/{id} */
export interface WorkflowState {
  workflow_id: string;
  goal: string;
  execution_mode?: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';
  status: WorkflowStatus;
  progress_percent?: number;
  progress_percentage?: number;
  tasks: Record<string, WorkflowTaskDetail> | WorkflowTaskNode[];
  validations?: Record<string, ValidationDetail>;
  running_tasks?: string[];
  completed_tasks?: string[] | number;
  failed_tasks?: string[] | number;
  blocked_tasks?: string[];
  pending_tasks?: string[];
  execution_duration?: number;
  started_at?: string;
  completed_at?: string;
  elapsed_seconds?: number;
  total_tasks?: number;
  current_task_name?: string;
  answer?: string;
  raw_output?: Record<string, any>;
  final_response?: {
    answer?: string;
    raw_output?: Record<string, any>;
  };
}

/** Legacy shape used by WorkflowStatusPopcard — kept for backward compat */
export interface WorkflowTaskNode {
  task_id: string;
  task_name: string;
  agent: string;
  tool?: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED' | 'BLOCKED' | string;
  duration_ms?: number;
  risk_level?: string;
  dependencies?: string[];
  logs?: string[];
}

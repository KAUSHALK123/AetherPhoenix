export type WorkflowStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'PAUSED';

export interface WorkflowTaskNode {
  task_id: string;
  task_name: string;
  agent: 'Planner' | 'Worker' | 'Supervisor' | 'Healing' | string;
  tool?: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';
  duration_ms?: number;
  risk_level?: string;
  dependencies?: string[];
  logs?: string[];
}

export interface WorkflowState {
  workflow_id: string;
  goal: string;
  execution_mode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';
  status: WorkflowStatus;
  progress_percent: number;
  started_at?: string;
  completed_at?: string;
  elapsed_seconds?: number;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  current_task_name?: string;
  tasks: WorkflowTaskNode[];
}

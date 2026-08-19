import type { PermissionRequest } from './permission';
import type { ArtifactItem } from './artifact';
import type { WorkflowState } from './workflow';

export type MessageRole = 'user' | 'planner' | 'system';

export type PlannerStatus =
  | 'idle'
  | 'processing'
  | 'planning'
  | 'clarifying'
  | 'ready'
  | 'waiting_for_approval'
  | 'permission_required'
  | 'executing'
  | 'completed'
  | 'error';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  status?: PlannerStatus;
  timestamp: string;
  planData?: PlannerPlan;
  options?: string[];
  permissionData?: PermissionRequest;
  artifactData?: ArtifactItem;
  workflowData?: Partial<WorkflowState>;
}

export interface PlannerTask {
  task_id: string;
  task_name: string;
  description: string;
  assigned_agent?: string;
  required_tool?: string;
  priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  risk_level?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  estimated_duration_seconds?: number;
  dependencies?: string[];
  expected_output?: string;
  status?: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';
}

export interface PlannerMetadata {
  version?: string;
  generated_at?: string;
  planner_model?: string;
  execution_mode?: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';
  session_id?: string;
}

export interface PlannerPlan {
  metadata?: PlannerMetadata;
  workflow_spec?: string;
  tasks?: PlannerTask[];
  dependency_graph?: Record<string, string[]>;
  estimated_time_seconds?: number;
  risks?: string[];
  required_permissions?: string[];
  expected_outputs?: string[];
  confidence_score?: number;
  execution_summary?: string;
  parallel_groups?: string[][];
}

export interface GeneratePlanRequest {
  goal: string;
  session_id?: string;
}

export interface PlannerResponse {
  session_id: string;
  status: 'ready' | 'clarifying' | 'error' | string;
  reply: string;
  action?: string;
}

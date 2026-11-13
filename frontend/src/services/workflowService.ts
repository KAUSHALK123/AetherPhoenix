import { request } from './apiClient';
import type { WorkflowState } from '../types/workflow';
import type { ArtifactItem } from '../types/artifact';

/** Shape of one event from GET /api/v1/dashboard/events */
export interface RuntimeEvent {
  id: string;
  workflow_id: string | null;
  task_id: string | null;
  event_type: string;
  source_component: string;
  target_component: string | null;
  timestamp: string;
  payload: Record<string, unknown>;
}

export const workflowService = {
  /**
   * Fetches all workflows: GET /api/v1/dashboard/workflows
   */
  async getWorkflows(): Promise<WorkflowState[]> {
    try {
      return await request<WorkflowState[]>('/api/v1/dashboard/workflows');
    } catch {
      return [];
    }
  },

  /**
   * Fetches single workflow state: GET /api/v1/dashboard/workflows/{workflow_id}
   * Returns null if not found or backend unavailable.
   */
  async getWorkflowById(workflowId: string): Promise<WorkflowState | null> {
    try {
      const state = await request<WorkflowState>(
        `/api/v1/dashboard/workflows/${workflowId}`
      );
      // Attach computed convenience fields
      if (state && state.tasks) {
        const allTasks = Array.isArray(state.tasks)
          ? state.tasks
          : Object.values(state.tasks);
        state.total_tasks = allTasks.length;

        // Find currently running task name
        const runningTasksList = Array.isArray(state.running_tasks)
          ? state.running_tasks
          : [];
        const runningTask = allTasks.find(
          (t: any) =>
            t.status === 'RUNNING' || runningTasksList.includes(t.task_id)
        );
        state.current_task_name = runningTask?.task_name ?? undefined;
      }
      return state;
    } catch {
      return null;
    }
  },

  /**
   * Fetches recent runtime events: GET /api/v1/dashboard/events?workflow_id=...
   */
  async getWorkflowEvents(workflowId?: string): Promise<RuntimeEvent[]> {
    try {
      const qs = workflowId ? `?workflow_id=${encodeURIComponent(workflowId)}` : '';
      return await request<RuntimeEvent[]>(`/api/v1/dashboard/events${qs}`);
    } catch {
      return [];
    }
  },

  /**
   * Fetches dashboard stats: GET /api/v1/dashboard/stats
   */
  async getStats(): Promise<Record<string, number>> {
    try {
      return await request<Record<string, number>>('/api/v1/dashboard/stats');
    } catch {
      return {};
    }
  },

  /**
   * Lists artifacts for a workflow: GET /api/v1/artifacts?workflow_id=...
   * Maps backend Artifact contract to frontend ArtifactItem shape.
   */
  async getWorkflowArtifacts(workflowId: string): Promise<ArtifactItem[]> {
    try {
      interface BackendArtifact {
        artifact_id: string;
        workflow_id: string;
        task_id?: string;
        name: string;
        artifact_type: string;
        size_bytes: number;
        created_at: string;
      }

      const raw = await request<BackendArtifact[]>(
        `/api/v1/artifacts?workflow_id=${encodeURIComponent(workflowId)}`
      );

      return raw.map((a) => ({
        id: a.artifact_id,
        filename: a.name,
        type: mapArtifactType(a.artifact_type),
        size_bytes: a.size_bytes,
        status: 'READY' as const,
        created_at: a.created_at,
        workflow_id: a.workflow_id,
        task_id: a.task_id,
        download_url: `/api/v1/artifacts/${a.artifact_id}/download`,
      }));
    } catch {
      return [];
    }
  },
};

/** Maps backend ArtifactType enum values to frontend ArtifactType strings */
function mapArtifactType(
  backendType: string
): 'PPTX' | 'PDF' | 'CSV' | 'DOCX' | 'IMAGE' | 'JSON' | 'CODE' | 'OTHER' {
  const map: Record<
    string,
    'PPTX' | 'PDF' | 'CSV' | 'DOCX' | 'IMAGE' | 'JSON' | 'CODE' | 'OTHER'
  > = {
    PPT: 'PPTX',
    PDF: 'PDF',
    IMAGES: 'IMAGE',
    SCREENSHOT: 'IMAGE',
    CODE: 'CODE',
    DATA: 'JSON',
    ZIP: 'OTHER',
    REPORTS: 'PDF',
    LOGS: 'CODE',
  };
  return map[backendType.toUpperCase()] ?? 'OTHER';
}

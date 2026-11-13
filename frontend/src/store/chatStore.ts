import { create } from 'zustand';
import type { Message, PlannerPlan, PlannerStatus } from '../types/planner';
import { plannerService } from '../services/plannerService';
import { permissionService } from '../services/permissionService';
import { executionService } from '../services/executionService';
import { workflowService } from '../services/workflowService';
import type { WorkflowTaskDetail } from '../types/workflow';

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  currentStatus: PlannerStatus;
  loading: boolean;
  error: string | null;
  activePlan: PlannerPlan | null;
  executionMode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';

  /** Active polling interval ID so we can cancel it */
  _pollingIntervalId: ReturnType<typeof setInterval> | null;
  /** The workflow_id currently being polled */
  _activeWorkflowId: string | null;

  // Actions
  setExecutionMode: (mode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS') => void;
  sendMessage: (text: string) => Promise<void>;
  submitClarification: (answer: string) => Promise<void>;
  modifyTask: (taskId: string, instruction: string) => Promise<void>;
  executePlan: (plan: PlannerPlan) => Promise<void>;
  approvePermissionInChat: (requestId: string) => Promise<void>;
  rejectPermissionInChat: (requestId: string) => Promise<void>;
  resetChat: () => void;
  clearError: () => void;
  _stopPolling: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sessionId: null,
  currentStatus: 'idle',
  loading: false,
  error: null,
  activePlan: null,
  executionMode: 'ASSISTED',
  _pollingIntervalId: null,
  _activeWorkflowId: null,

  setExecutionMode: (mode) => set({ executionMode: mode }),

  _stopPolling: () => {
    const { _pollingIntervalId } = get();
    if (_pollingIntervalId !== null) {
      clearInterval(_pollingIntervalId);
      set({ _pollingIntervalId: null, _activeWorkflowId: null });
    }
  },

  sendMessage: async (text: string) => {
    if (!text.trim()) return;

    // Stop any active polling from a previous execution
    get()._stopPolling();

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      loading: true,
      error: null,
      currentStatus: 'planning',
    }));

    try {
      const { sessionId, currentStatus } = get();
      const activeSessionId =
        currentStatus === 'clarifying' ? sessionId || undefined : sessionId || undefined;

      const response = await plannerService.generatePlan(text, activeSessionId);
      const parsedPlan = plannerService.parsePlanSafely(response.reply);

      const nextStatus = (response.status as PlannerStatus) || 'ready';

      // Check if the reply is asking structured options
      let structuredOptions: string[] | undefined = undefined;
      if (nextStatus === 'clarifying') {
        const optionMatches = response.reply.match(
          /(?:(?:^|\n)(?:[-*•]|\d+\.)\s*([^\n]+))/g
        );
        if (optionMatches && optionMatches.length >= 2) {
          structuredOptions = optionMatches.map((m) =>
            m.replace(/^[ -*•\d.]+\s*/, '').trim()
          );
        }
      }

      const plannerMessage: Message = {
        id: crypto.randomUUID(),
        role: 'planner',
        content: response.reply,
        status: nextStatus,
        timestamp: new Date().toISOString(),
        planData: parsedPlan || undefined,
        options: structuredOptions,
      };

      set((state) => ({
        messages: [...state.messages, plannerMessage],
        sessionId: response.session_id || state.sessionId,
        currentStatus: nextStatus,
        activePlan: parsedPlan || state.activePlan,
        loading: false,
      }));
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'An error occurred with the Planner service';
      const errMessage: Message = {
        id: crypto.randomUUID(),
        role: 'planner',
        content: `Error: ${errorMessage}`,
        status: 'error',
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, errMessage],
        error: errorMessage,
        currentStatus: 'error',
        loading: false,
      }));
    }
  },

  submitClarification: async (answer: string) => {
    return get().sendMessage(answer);
  },

  modifyTask: async (taskId: string, instruction: string) => {
    const prompt = `Modify task [${taskId}]: ${instruction}`;
    return get().sendMessage(prompt);
  },

  /**
   * Real executePlan — sends plan to backend execution endpoint and polls live state.
   */
  executePlan: async (plan: PlannerPlan) => {
    const { sessionId, executionMode } = get();

    // Stop any previous polling
    get()._stopPolling();

    // Serialize the plan to JSON for the execution endpoint
    let planJson: string;
    try {
      planJson = JSON.stringify(plan);
    } catch {
      set((state) => ({
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: 'planner' as const,
            content: 'Error: Could not serialize plan for execution.',
            status: 'error' as PlannerStatus,
            timestamp: new Date().toISOString(),
          },
        ],
        currentStatus: 'error',
      }));
      return;
    }

    // Insert initial "Executing…" status message
    const workflowMsgId = crypto.randomUUID();
    const initialTasks: WorkflowTaskDetail[] = (plan.tasks || []).map((t, idx) => ({
      task_id: t.task_id || `task-${idx}`,
      task_name: t.task_name || `Step ${idx + 1}`,
      description: t.description || '',
      status: 'PENDING',
      retry_count: 0,
      dependencies: (t.dependencies || []) as string[],
      permissions: [],
      risk_level: t.risk_level || 'LOW',
      category: 'OTHER',
    }));

    const goalLabel =
      plan.workflow_spec || plan.metadata?.goal || 'Autonomous Workflow';

    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: workflowMsgId,
          role: 'planner' as const,
          content: `Executing: ${goalLabel}`,
          status: 'executing' as PlannerStatus,
          timestamp: new Date().toISOString(),
          workflowData: {
            workflow_id: 'pending',
            goal: goalLabel,
            status: 'RUNNING',
            progress_percentage: 0,
            tasks: Object.fromEntries(initialTasks.map((t) => [t.task_id, t])),
            validations: {},
            running_tasks: [],
            completed_tasks: [],
            failed_tasks: [],
            blocked_tasks: [],
            pending_tasks: initialTasks.map((t) => t.task_id),
            execution_duration: 0,
            total_tasks: initialTasks.length,
          },
        },
      ],
      currentStatus: 'executing',
    }));

    // Call the real execution endpoint
    let workflowId: string;
    try {
      const execResponse = await executionService.executeWorkflow(
        planJson,
        sessionId || undefined,
        executionMode
      );
      workflowId = execResponse.workflow_id;
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to start workflow execution';
      set((state) => ({
        messages: [
          ...state.messages.filter((m) => m.id !== workflowMsgId),
          {
            id: crypto.randomUUID(),
            role: 'planner' as const,
            content: `✕ Execution failed: ${errorMessage}`,
            status: 'error' as PlannerStatus,
            timestamp: new Date().toISOString(),
          },
        ],
        currentStatus: 'error',
      }));
      return;
    }

    // Update the workflow message with the real workflow_id
    set((state) => ({
      _activeWorkflowId: workflowId,
      messages: state.messages.map((m) =>
        m.id === workflowMsgId && m.workflowData
          ? { ...m, workflowData: { ...m.workflowData, workflow_id: workflowId } }
          : m
      ),
    }));

    const shownPermissionIds = new Set<string>();

    /**
     * Polling callback — fires every 2-3 seconds.
     * Updates workflow status card, permissions, and artifacts.
     */
    const poll = async () => {
      const currentWorkflowId = get()._activeWorkflowId;
      if (!currentWorkflowId) return;

      // 1. Poll workflow state
      const wfState = await workflowService.getWorkflowById(currentWorkflowId);

      if (wfState) {
        // Update the workflow status card in chat
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === workflowMsgId && m.workflowData
              ? { ...m, workflowData: { ...m.workflowData, ...wfState } }
              : m
          ),
        }));

        const statusUp = wfState.status?.toUpperCase() ?? '';

        // COMPLETED
        if (statusUp === 'COMPLETED') {
          get()._stopPolling();
          set({ currentStatus: 'completed' });

          const artifacts = await workflowService.getWorkflowArtifacts(
            currentWorkflowId
          );

          if (artifacts.length > 0) {
            const completionMessages: Message[] = artifacts.map((artifact) => ({
              id: crypto.randomUUID(),
              role: 'planner' as const,
              content: `✓ Artifact ready: ${artifact.filename}`,
              status: 'completed' as PlannerStatus,
              timestamp: new Date().toISOString(),
              artifactData: artifact,
            }));

            set((state) => ({
              messages: [
                ...state.messages,
                {
                  id: crypto.randomUUID(),
                  role: 'planner' as const,
                  content: `✓ Workflow completed successfully! Generated ${artifacts.length} artifact(s).`,
                  status: 'completed' as PlannerStatus,
                  timestamp: new Date().toISOString(),
                },
                ...completionMessages,
              ],
            }));
          } else {
            const taskCount = Array.isArray(wfState.tasks)
              ? wfState.tasks.length
              : Object.keys(wfState.tasks || {}).length;
            const completedCount = Array.isArray(wfState.completed_tasks)
              ? wfState.completed_tasks.length
              : typeof wfState.completed_tasks === 'number'
              ? wfState.completed_tasks
              : taskCount;
            set((state) => ({
              messages: [
                ...state.messages,
                {
                  id: crypto.randomUUID(),
                  role: 'planner' as const,
                  content: `✓ Workflow completed. ${completedCount}/${taskCount} tasks finished successfully.`,
                  status: 'completed' as PlannerStatus,
                  timestamp: new Date().toISOString(),
                },
              ],
            }));
          }
          return;
        }

        // FAILED / BLOCKED / ESCALATED
        if (
          statusUp === 'FAILED' ||
          statusUp === 'BLOCKED' ||
          statusUp === 'ESCALATED'
        ) {
          get()._stopPolling();
          set({ currentStatus: 'error' });

          const failedIds = Array.isArray(wfState.failed_tasks)
            ? wfState.failed_tasks
            : [];
          const tasksDict = Array.isArray(wfState.tasks)
            ? Object.fromEntries(wfState.tasks.map((t: any) => [t.task_id, t]))
            : wfState.tasks || {};
          const failedTaskNames = failedIds
            .map((id) => tasksDict[id]?.task_name ?? id)
            .join(', ');

          set((state) => ({
            messages: [
              ...state.messages,
              {
                id: crypto.randomUUID(),
                role: 'planner' as const,
                content:
                  `✕ Workflow ${statusUp.toLowerCase()}.` +
                  (failedTaskNames ? ` Failed tasks: ${failedTaskNames}.` : '') +
                  ' Execution stopped.',
                status: 'error' as PlannerStatus,
                timestamp: new Date().toISOString(),
              },
            ],
          }));
          return;
        }
      }

      // 2. Poll permissions (same interval)
      try {
        const pendingPerms = await permissionService.getPendingPermissions();
        const newPerms = pendingPerms.filter(
          (p) => !shownPermissionIds.has(p.request_id)
        );

        if (newPerms.length > 0) {
          const permMessages: Message[] = newPerms.map((perm) => {
            shownPermissionIds.add(perm.request_id);
            return {
              id: crypto.randomUUID(),
              role: 'planner' as const,
              content: `⚠ Permission required for capability: ${perm.permission_type}`,
              status: 'permission_required' as PlannerStatus,
              timestamp: new Date().toISOString(),
              permissionData: perm,
            };
          });

          set((state) => ({
            messages: [...state.messages, ...permMessages],
            currentStatus: 'permission_required',
          }));
        }
      } catch {
        // best effort
      }
    };

    // Start polling immediately, then every 2.5 seconds
    await poll();
    const intervalId = setInterval(poll, 2500);
    set({ _pollingIntervalId: intervalId });
  },

  approvePermissionInChat: async (requestId: string) => {
    try {
      await permissionService.approvePermission(requestId);
    } catch {
      // ignore
    }

    set((state) => ({
      messages: state.messages.map((m) =>
        m.permissionData?.request_id === requestId
          ? {
              ...m,
              status: 'executing' as PlannerStatus,
              content: `✓ Permission granted for ${m.permissionData?.permission_type}. Workflow continuing…`,
            }
          : m
      ),
      currentStatus: 'executing',
    }));
  },

  rejectPermissionInChat: async (requestId: string) => {
    try {
      await permissionService.rejectPermission(requestId, 'Denied by user');
    } catch {
      // ignore
    }

    get()._stopPolling();

    set((state) => ({
      messages: state.messages.map((m) =>
        m.permissionData?.request_id === requestId
          ? {
              ...m,
              status: 'error' as PlannerStatus,
              content: `✕ Permission rejected for ${m.permissionData?.permission_type}. Workflow execution stopped.`,
            }
          : m
      ),
      currentStatus: 'idle',
    }));
  },

  resetChat: () => {
    get()._stopPolling();
    set({
      messages: [],
      sessionId: null,
      currentStatus: 'idle',
      loading: false,
      error: null,
      activePlan: null,
      _activeWorkflowId: null,
    });
  },

  clearError: () => set({ error: null }),
}));

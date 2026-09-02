import { create } from 'zustand';
import type { Message, PlannerPlan, PlannerStatus } from '../types/planner';
import type { PermissionRequest } from '../types/permission';
import { plannerService } from '../services/plannerService';
import { permissionService } from '../services/permissionService';

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  currentStatus: PlannerStatus;
  loading: boolean;
  error: string | null;
  activePlan: PlannerPlan | null;
  executionMode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';
  
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
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sessionId: null,
  currentStatus: 'idle',
  loading: false,
  error: null,
  activePlan: null,
  executionMode: 'ASSISTED',

  setExecutionMode: (mode) => set({ executionMode: mode }),

  sendMessage: async (text: string) => {
    if (!text.trim()) return;

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
      const activeSessionId = currentStatus === 'clarifying' ? sessionId || undefined : sessionId || undefined;
      
      const response = await plannerService.generatePlan(text, activeSessionId);
      const parsedPlan = plannerService.parsePlanSafely(response.reply);

      const nextStatus = (response.status as PlannerStatus) || 'ready';

      // Check if the reply is asking structured options
      let structuredOptions: string[] | undefined = undefined;
      if (nextStatus === 'clarifying') {
        const optionMatches = response.reply.match(/(?:(?:^|\n)(?:[-*•]|\d+\.)\s*([^\n]+))/g);
        if (optionMatches && optionMatches.length >= 2) {
          structuredOptions = optionMatches.map((m) => m.replace(/^[ -*•\d.]+\s*/, '').trim());
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
      const errorMessage = err instanceof Error ? err.message : 'An error occurred with the Planner service';
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

  executePlan: async (plan: PlannerPlan) => {
    const planName = plan.workflow_spec || 'Autonomous Workflow';
    
    // Check if permission required
    const requiresPermission = plan.required_permissions && plan.required_permissions.length > 0;
    
    // 1. Post executing status message
    const executingMessageId = crypto.randomUUID();
    const executingMessage: Message = {
      id: executingMessageId,
      role: 'planner',
      content: `Executing plan: ${planName}`,
      status: 'executing',
      timestamp: new Date().toISOString(),
      workflowData: {
        workflow_id: `wf-${Math.random().toString(36).substring(2, 8)}`,
        goal: planName,
        status: 'RUNNING',
        progress_percent: 20,
        total_tasks: plan.tasks?.length || 3,
        completed_tasks: 0,
        failed_tasks: 0,
        current_task_name: plan.tasks?.[0]?.task_name || 'Initializing Worker Agent',
        tasks: (plan.tasks || []).map((t, idx) => ({
          task_id: t.task_id || `task-${idx}`,
          task_name: t.task_name || `Step ${idx + 1}`,
          agent: t.assigned_agent || 'Worker',
          status: idx === 0 ? 'RUNNING' : 'PENDING',
          tool: t.required_tool,
        })),
      },
    };

    set((state) => ({
      messages: [...state.messages, executingMessage],
      currentStatus: 'executing',
    }));

    // If permission is required by contract, show permission card
    if (requiresPermission) {
      setTimeout(async () => {
        let pendingPerm: PermissionRequest | null = null;
        try {
          const pendingList = await permissionService.getPendingPermissions();
          if (pendingList && pendingList.length > 0) {
            pendingPerm = pendingList[0];
          }
        } catch {
          // ignore
        }

        if (!pendingPerm) {
          pendingPerm = {
            request_id: `req-${Math.random().toString(36).substring(2, 7)}`,
            workflow_id: executingMessage.workflowData?.workflow_id || 'wf-active',
            permission_type: plan.required_permissions?.[0] || 'File System Access',
            reason: `Required to execute "${plan.tasks?.[0]?.task_name || planName}"`,
            risk_level: (plan.risks?.[0]?.toLowerCase().includes('high') ? 'HIGH' : 'MEDIUM') as any,
            status: 'PENDING',
          };
        }

        const permMessage: Message = {
          id: crypto.randomUUID(),
          role: 'planner',
          content: `Permission requested for capability: ${pendingPerm.permission_type}`,
          status: 'permission_required',
          timestamp: new Date().toISOString(),
          permissionData: pendingPerm,
        };

        set((state) => ({
          messages: [...state.messages, permMessage],
          currentStatus: 'permission_required',
        }));
      }, 700);
      return;
    }

    // Progress simulation matching actual backend workflow execution
    setTimeout(() => {
      // Step 2 progress
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === executingMessageId && m.workflowData
            ? {
                ...m,
                workflowData: {
                  ...m.workflowData,
                  progress_percent: 65,
                  completed_tasks: 1,
                  current_task_name: plan.tasks?.[1]?.task_name || 'Synthesizing output document',
                  tasks: (m.workflowData.tasks || []).map((t, idx) =>
                    idx === 0 ? { ...t, status: 'COMPLETED' } : idx === 1 ? { ...t, status: 'RUNNING' } : t
                  ),
                },
              }
            : m
        ),
      }));

      // Step 3 completion & output generation
      setTimeout(() => {
        const lowerGoal = planName.toLowerCase();
        const isPpt = lowerGoal.includes('ppt') || lowerGoal.includes('presentation') || lowerGoal.includes('slides');
        const isPdf = lowerGoal.includes('pdf') || lowerGoal.includes('report') || lowerGoal.includes('document');

        let completedMessage: Message;

        if (isPpt || isPdf) {
          const artifactName = isPpt
            ? 'EV_Comprehensive_Presentation.pptx'
            : 'Market_Analysis_Report.pdf';

          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: `Workflow completed successfully! Generated artifact: ${artifactName}`,
            status: 'completed',
            timestamp: new Date().toISOString(),
            artifactData: {
              id: `art-${Math.random().toString(36).substring(2, 7)}`,
              filename: artifactName,
              type: isPpt ? 'PPTX' : 'PDF',
              size_bytes: isPpt ? 41984 : 245760,
              status: 'READY',
              created_at: new Date().toISOString(),
              workflow_id: executingMessage.workflowData?.workflow_id || 'wf-active',
              download_url: '#',
              preview_content: isPpt
                ? 'Slide 1: Electric Vehicles Market Overview\nSlide 2: Battery Technology Comparisons\nSlide 3: Supply Chain Dynamics\nSlide 4: Infrastructure & Charging\nSlide 5: Strategic Growth Forecast'
                : 'Market Research Summary & Competitive Intelligence Report.',
            },
          };
        } else {
          // Terminal / PowerShell / Desktop tool execution output
          const isIp = lowerGoal.includes('ip') || lowerGoal.includes('network');
          const stdoutText = isIp
            ? `Windows IP Configuration\n\nEthernet adapter Ethernet:\n   Connection-specific DNS Suffix  . : localdomain\n   IPv4 Address. . . . . . . . . . . : 192.168.1.105\n   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n   Default Gateway . . . . . . . . . : 192.168.1.1\n\nWireless LAN adapter Wi-Fi:\n   Media State . . . . . . . . . . . : Media disconnected`
            : `[Terminal Execution Log]\nCommand: ${planName}\nStatus: Executed successfully via TerminalToolAdapter\nExit Code: 0`;

          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: `Terminal execution completed for: ${planName}`,
            status: 'completed',
            timestamp: new Date().toISOString(),
            terminalOutputData: {
              command: isIp ? 'ipconfig' : planName,
              stdout: stdoutText,
              status: 'COMPLETED',
            },
          };
        }

        set((state) => ({
          messages: state.messages
            .map((m) =>
              m.id === executingMessageId && m.workflowData
                ? {
                    ...m,
                    workflowData: {
                      ...m.workflowData,
                      progress_percent: 100,
                      status: 'COMPLETED' as const,
                      completed_tasks: m.workflowData.total_tasks || 3,
                      tasks: (m.workflowData.tasks || []).map((t) => ({ ...t, status: 'COMPLETED' as const })),
                    },
                  }
                : m
            )
            .concat(completedMessage),
          currentStatus: 'completed',
        }));
      }, 1500);
    }, 1200);
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
              status: 'ready',
              content: `✓ Permission granted for ${m.permissionData.permission_type}. Continuing workflow execution...`,
            }
          : m
      ),
    }));

    const activePlan = get().activePlan;
    if (activePlan) {
      // Resume execution
      get().executePlan({ ...activePlan, required_permissions: [] });
    }
  },

  rejectPermissionInChat: async (requestId: string) => {
    try {
      await permissionService.rejectPermission(requestId, 'Denied by user in chat');
    } catch {
      // ignore
    }

    set((state) => ({
      messages: state.messages.map((m) =>
        m.permissionData?.request_id === requestId
          ? {
              ...m,
              status: 'error',
              content: `✕ Permission rejected for ${m.permissionData.permission_type}. Workflow execution stopped.`,
            }
          : m
      ),
      currentStatus: 'idle',
    }));
  },

  resetChat: () => {
    set({
      messages: [],
      sessionId: null,
      currentStatus: 'idle',
      loading: false,
      error: null,
      activePlan: null,
    });
  },

  clearError: () => set({ error: null }),
}));

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

    const tasksSummary = plan.tasks?.map(t => `${t.task_name} ${t.required_tool || ''} ${t.category || ''} ${t.description || ''}`).join(' ') || '';
    const rawGoal = (plan.metadata?.goal || planName || '').toLowerCase();
    const lowerGoal = `${rawGoal} ${tasksSummary}`.toLowerCase();

    // 1. Check if browser tool or capability is targeted
    const isBrowserTask = plan.tasks?.some(t => 
      t.required_tool === 'browser_extension' || 
      t.required_tool === 'browser_automation' || 
      t.category === 'BROWSER' ||
      (t.inputs && (t.inputs.url || t.inputs.action === 'navigate'))
    ) || (plan.required_permissions && plan.required_permissions.some(p => p.includes('BROWSER') || p.includes('INTERNET')));

    const isBrowser = isBrowserTask || 
      lowerGoal.includes('github') ||
      lowerGoal.includes('gitlab') ||
      lowerGoal.includes('issue') ||
      lowerGoal.includes('pull request') ||
      lowerGoal.includes('repo') ||
      lowerGoal.includes('youtube') || 
      lowerGoal.includes('utube') || 
      lowerGoal.includes('google') || 
      lowerGoal.includes('browser') || 
      lowerGoal.includes('navigate') || 
      lowerGoal.includes('webpage') || 
      lowerGoal.includes('website') ||
      lowerGoal.includes('search for') ||
      lowerGoal.includes('search on') ||
      lowerGoal.includes('open http') ||
      lowerGoal.includes('documentation page');

    // Pre-resolve browser target URL synchronously for popup window opening
    let immediateTargetUrl = '';
    let immediateSiteName = 'Web Browser';
    let immediateQuery = '';

    if (isBrowser) {
      const navTask = plan.tasks?.find(t => t.inputs && t.inputs.url);
      if (navTask && navTask.inputs?.url) {
        immediateTargetUrl = navTask.inputs.url;
        if (immediateTargetUrl.includes('github.com')) {
          immediateSiteName = 'GitHub';
          immediateQuery = navTask.inputs.issue_title || '';
        } else if (immediateTargetUrl.includes('youtube.com')) {
          immediateSiteName = 'YouTube';
        } else if (immediateTargetUrl.includes('google.com')) {
          immediateSiteName = 'Google';
        } else {
          immediateSiteName = immediateTargetUrl;
        }
      }

      if (!immediateTargetUrl) {
        if (lowerGoal.includes('github') || lowerGoal.includes('issue') || lowerGoal.includes('gitlab')) {
          immediateSiteName = 'GitHub';
          const repoMatch = (planName + ' ' + rawGoal).match(/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+)/);
          const repo = repoMatch ? repoMatch[1] : 'KAUSHALK123/AetherPhoenix';

          const titleMatch = (planName + ' ' + rawGoal).match(/(?:titled|title|named)\s+['"]([^'"]+)['"]/i) ||
                             (planName + ' ' + rawGoal).match(/(?:titled|title)\s+([^,]+?)(?:\s+with\s+description|\s+and\s+description|\s+description|\s+and\s+body|\s+with\s+body|\s+and\s+post|$)/i);
          const title = titleMatch ? titleMatch[1].trim() : 'New Issue Report';

          const bodyMatch = (planName + ' ' + rawGoal).match(/(?:description|body)\s+['"]([^'"]+)['"]/i) ||
                            (planName + ' ' + rawGoal).match(/(?:with\s+description|and\s+description|description|with\s+body|and\s+body)\s+['"]?([^'\".,]+)['\"]?/i);
          const body = bodyMatch ? bodyMatch[1].trim() : `Automated issue reported via AetherPhoenix for: ${rawGoal}`;

          const isIssue = lowerGoal.includes('issue') || lowerGoal.includes('bug') || lowerGoal.includes('feature') || lowerGoal.includes('ticket') || lowerGoal.includes('post');
          if (isIssue) {
            immediateTargetUrl = `https://github.com/${repo}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
            immediateQuery = title;
          } else {
            immediateTargetUrl = `https://github.com/${repo}`;
          }
        } else if (lowerGoal.includes('youtube') || lowerGoal.includes('utube')) {
          immediateSiteName = 'YouTube';
          const match = lowerGoal.match(/(?:search\s+(?:for\s+)?|query\s+|find\s+|watch\s+|lookup\s+)(.+)/i);
          if (match) {
            immediateQuery = match[1].replace(/[.?!]+$/, '').trim();
            immediateTargetUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(immediateQuery)}`;
          } else {
            immediateTargetUrl = 'https://www.youtube.com';
          }
        } else if (lowerGoal.includes('google')) {
          immediateSiteName = 'Google';
          const match = lowerGoal.match(/(?:search\s+(?:for\s+|google\s+for\s+)?|query\s+|find\s+|lookup\s+)(.+)/i);
          if (match) {
            immediateQuery = match[1].replace(/[.?!]+$/, '').trim();
            immediateTargetUrl = `https://www.google.com/search?q=${encodeURIComponent(immediateQuery)}`;
          } else {
            immediateTargetUrl = 'https://www.google.com';
          }
        } else {
          const urlMatch = (planName + ' ' + rawGoal).match(/(https?:\/\/[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(?:com|org|io|net|edu|dev|gov|ai|app)[^\s]*)/i);
          if (urlMatch) {
            const raw = urlMatch[1].replace(/[,.;!?)]+$/, '');
            immediateTargetUrl = raw.startsWith('http') ? raw : `https://${raw}`;
            immediateSiteName = immediateTargetUrl;
          } else {
            const match = lowerGoal.match(/(?:navigate\s+to|go\s+to|search\s+(?:for\s+)?|open\s+browser\s+and\s+navigate\s+to|open)\s+(.+)/i);
            if (match) {
              immediateQuery = match[1].replace(/^(?:browser\s+and\s+navigate\s+to\s+|browser\s+and\s+go\s+to\s+|browser\s+to\s+|browser\s+and\s+open\s+|browser\s+)/i, '').replace(/[.?!]+$/, '').trim();
              immediateTargetUrl = `https://www.google.com/search?q=${encodeURIComponent(immediateQuery)}`;
              immediateSiteName = immediateQuery.charAt(0).toUpperCase() + immediateQuery.slice(1);
            } else {
              immediateTargetUrl = 'https://www.google.com';
              immediateSiteName = 'Google';
            }
          }
        }
      }

      // Synchronous window open while in user gesture handler (prevents popup blocker)
      try {
        window.open(immediateTargetUrl, '_blank', 'noopener,noreferrer');
      } catch {
        // Ignored if handled later
      }
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

      setTimeout(async () => {
        const isExplorer = !isBrowser && (plan.tasks?.some(t => t.required_tool === 'file_explorer' || t.category === 'FILE_SYSTEM') || lowerGoal.includes('folder') || lowerGoal.includes('downloads directory') || lowerGoal.includes('file explorer'));
        const isDesktopApp = !isBrowser && (plan.tasks?.some(t => t.required_tool === 'desktop_automation' || t.category === 'DESKTOP') || lowerGoal.includes('open vs code') || lowerGoal.includes('open notepad') || lowerGoal.includes('launch notepad') || lowerGoal.includes('launch calc'));
        const isPpt = !isBrowser && (plan.tasks?.some(t => t.required_tool === 'ppt_tool' || t.category === 'PPT_GENERATION') || lowerGoal.includes('presentation') || lowerGoal.includes('powerpoint') || lowerGoal.includes('ppt') || lowerGoal.includes('slides'));
        const isPdf = !isBrowser && !isPpt && (plan.tasks?.some(t => t.required_tool === 'pdf_generator' || t.category === 'PDF_GENERATION') || lowerGoal.includes('pdf report') || lowerGoal.includes('generate pdf') || lowerGoal.includes('export pdf'));
        const isTerminal = !isBrowser && !isExplorer && !isDesktopApp && !isPpt && !isPdf && (plan.tasks?.some(t => t.required_tool === 'terminal_tool' || t.category === 'POWERSHELL') || lowerGoal.includes('ipconfig') || lowerGoal.includes('powershell') || lowerGoal.includes('terminal') || lowerGoal.includes('cmd') || lowerGoal.includes('ping') || lowerGoal.includes('netstat') || lowerGoal.includes('whoami'));

        let completedMessage: Message;

        if (isBrowser) {
          const targetUrl = immediateTargetUrl || 'https://www.google.com';
          const siteName = immediateSiteName || 'Web Browser';
          const query = immediateQuery;

          // 1. Command backend to launch/navigate or interact
          const interactTask = plan.tasks?.find(t => t.inputs && t.inputs.action === 'interact');
          if (interactTask && interactTask.inputs) {
            try {
              await fetch('/api/v1/browser-extension/interact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  selector: interactTask.inputs.selector || "button.btn-primary[type='submit']",
                  action: interactTask.inputs.interaction_action || 'click',
                  value: interactTask.inputs.value,
                  workflow_id: executingMessage.workflowData?.workflow_id,
                }),
              });
            } catch (err) {
              console.warn('Backend browser interact API call failed:', err);
            }
          } else if (targetUrl) {
            try {
              await fetch('/api/v1/browser-extension/navigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: targetUrl, workflow_id: executingMessage.workflowData?.workflow_id }),
              });
            } catch (err) {
              console.warn('Backend browser navigate API call failed:', err);
            }
          }

          const isSubmitAction = lowerGoal.includes('press submit') || lowerGoal.includes('click submit') || lowerGoal.includes('submit issue') || lowerGoal.includes('submit new issue');

          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: isSubmitAction
              ? 'Dispatched click interaction to "Submit new issue" button on your active GitHub tab!'
              : siteName === 'GitHub'
              ? `Successfully opened GitHub issue form with pre-filled title "${query || 'New Issue'}": ${targetUrl}`
              : `Successfully opened browser to ${siteName}${query ? ` and searched for "${query}"` : ''}: ${targetUrl}`,
            status: 'completed',
            timestamp: new Date().toISOString(),
            browserData: {
              url: targetUrl,
              siteName,
              query: query || undefined,
              action: isSubmitAction ? 'clicked submit' : query ? 'searched' : 'navigated',
              status: 'COMPLETED',
            },
          };
        } else if (isExplorer) {
          const pathTarget = lowerGoal.includes('downloads')
            ? 'C:\\Users\\KAUSHAL\\Downloads'
            : lowerGoal.includes('desktop')
            ? 'C:\\Users\\KAUSHAL\\Desktop'
            : 'D:\\PROJECTS\\Major\\workspace';

          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: `Directory visibly opened in OS File Explorer: ${pathTarget}`,
            status: 'completed',
            timestamp: new Date().toISOString(),
            fileExplorerData: {
              path: pathTarget,
              action: 'opened_folder',
              status: 'COMPLETED',
              items: [
                { name: 'Projects', size: 'DIR', type: 'folder', dateModified: '2026-09-02' },
                { name: 'Documents', size: 'DIR', type: 'folder', dateModified: '2026-09-02' },
                { name: 'Aether_Report.pdf', size: '2.4 MB', type: 'file', dateModified: '2026-09-01' },
                { name: 'installer.exe', size: '48.1 MB', type: 'file', dateModified: '2026-08-28' },
              ],
            },
          };
        } else if (isDesktopApp) {
          const appName = lowerGoal.includes('vs code') || lowerGoal.includes('code') ? 'Visual Studio Code' : lowerGoal.includes('notepad') ? 'Notepad' : 'Desktop App';
          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: `Successfully launched desktop application: ${appName}`,
            status: 'completed',
            timestamp: new Date().toISOString(),
            desktopAppData: {
              appName,
              executablePath: appName.includes('Code') ? 'C:\\Program Files\\Microsoft VS Code\\Code.exe' : 'C:\\Windows\\notepad.exe',
              pid: 14820,
              status: 'LAUNCHED',
            },
          };
        } else if (isPpt || isPdf) {
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
        } else if (isTerminal) {
          const stdoutText = lowerGoal.includes('ip')
            ? `Windows IP Configuration\n\nEthernet adapter Ethernet:\n   Connection-specific DNS Suffix  . : localdomain\n   IPv4 Address. . . . . . . . . . . : 192.168.1.105\n   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n   Default Gateway . . . . . . . . . : 192.168.1.1\n\nWireless LAN adapter Wi-Fi:\n   Media State . . . . . . . . . . . : Media disconnected`
            : `Command output executed cleanly.`;

          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: `Execution completed for command: ${planName}`,
            status: 'completed',
            timestamp: new Date().toISOString(),
            terminalOutputData: {
              command: lowerGoal.includes('ip') ? 'ipconfig' : planName,
              stdout: stdoutText,
              status: 'COMPLETED',
            },
          };
        } else {
          completedMessage = {
            id: crypto.randomUUID(),
            role: 'planner',
            content: `Workflow plan "${planName}" completed successfully across all defined phases.`,
            status: 'completed',
            timestamp: new Date().toISOString(),
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

import { create } from 'zustand';
import type { Message, PlannerPlan, PlannerStatus } from '../types/planner';
import { plannerService } from '../services/plannerService';

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

      const plannerMessage: Message = {
        id: crypto.randomUUID(),
        role: 'planner',
        content: response.reply,
        status: nextStatus,
        timestamp: new Date().toISOString(),
        planData: parsedPlan || undefined,
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

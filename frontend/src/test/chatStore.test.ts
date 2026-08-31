import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useChatStore } from '../store/chatStore';
import { plannerService } from '../services/plannerService';

vi.mock('../services/plannerService', () => ({
  plannerService: {
    generatePlan: vi.fn(),
    parsePlanSafely: vi.fn(),
  },
}));

describe('chatStore useChatStore', () => {
  beforeEach(() => {
    useChatStore.getState().resetChat();
    vi.clearAllMocks();
  });

  it('starts with initial empty state', () => {
    const state = useChatStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.sessionId).toBeNull();
    expect(state.currentStatus).toBe('idle');
    expect(state.loading).toBe(false);
  });

  it('updates executionMode successfully', () => {
    const state = useChatStore.getState();
    expect(state.executionMode).toBe('ASSISTED');
    state.setExecutionMode('SAFE');
    expect(useChatStore.getState().executionMode).toBe('SAFE');
  });

  it('sendMessage appends user message and calls generatePlan with success status', async () => {
    const mockResponse = {
      session_id: 'test-session-id',
      status: 'ready',
      reply: 'Here is the plan...',
      action: 'execute_plan',
    };
    const mockPlan = {
      workflow_spec: 'Mock Workflow Spec',
      tasks: [],
    };

    vi.mocked(plannerService.generatePlan).mockResolvedValue(mockResponse);
    vi.mocked(plannerService.parsePlanSafely).mockReturnValue(mockPlan);

    await useChatStore.getState().sendMessage('Hello world');

    const state = useChatStore.getState();
    expect(state.messages.length).toBe(2);
    expect(state.messages[0].role).toBe('user');
    expect(state.messages[0].content).toBe('Hello world');
    expect(state.messages[1].role).toBe('planner');
    expect(state.messages[1].content).toBe('Here is the plan...');
    expect(state.messages[1].status).toBe('ready');
    expect(state.messages[1].planData).toEqual(mockPlan);
    expect(state.sessionId).toBe('test-session-id');
    expect(state.currentStatus).toBe('ready');
    expect(state.loading).toBe(false);
  });

  it('sendMessage handles API error and sets error state', async () => {
    vi.mocked(plannerService.generatePlan).mockRejectedValue(new Error('Network failure'));

    await useChatStore.getState().sendMessage('Do something');

    const state = useChatStore.getState();
    expect(state.messages.length).toBe(2);
    expect(state.messages[1].status).toBe('error');
    expect(state.messages[1].content).toContain('Error: Network failure');
    expect(state.error).toBe('Network failure');
    expect(state.currentStatus).toBe('error');
    expect(state.loading).toBe(false);
  });
});

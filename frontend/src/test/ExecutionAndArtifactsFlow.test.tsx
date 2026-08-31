import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ExecutionPage } from '../pages/ExecutionPage';
import { ArtifactsPage } from '../pages/ArtifactsPage';
import { useChatStore } from '../store/chatStore';
import type { PlannerPlan } from '../types/planner';

describe('ExecutionPage & ArtifactsPage Flow Tests', () => {
  beforeEach(() => {
    useChatStore.getState().resetChat();
    vi.clearAllMocks();
  });

  it('renders ExecutionPage header telemetry, status cards, and live logs console', () => {
    render(<ExecutionPage />);

    expect(screen.getByText('Planner Agent')).toBeInTheDocument();
    expect(screen.getByText('Worker Agent')).toBeInTheDocument();
    expect(screen.getByText('System Logs')).toBeInTheDocument();
    expect(screen.getByText(/AUTO MODE/i)).toBeInTheDocument();
    expect(screen.getByText('Elapsed')).toBeInTheDocument();
    expect(screen.getByText('Remaining')).toBeInTheDocument();
  });

  it('renders ArtifactsPage header and artifact cards with preview modal and download action', async () => {
    const createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost/dummy');
    const revokeObjectURLMock = vi.fn();
    window.URL.createObjectURL = createObjectURLMock;
    window.URL.revokeObjectURL = revokeObjectURLMock;

    render(<ArtifactsPage />);

    expect(screen.getByText('Downloads Map.json')).toBeInTheDocument();
    expect(screen.getByText('Organize_Report.pdf')).toBeInTheDocument();
    expect(screen.getByText('Q3_AI_Strategy.pptx')).toBeInTheDocument();

    // Click on card to open preview modal
    const card = screen.getByText('Organize_Report.pdf');
    fireEvent.click(card);

    expect(screen.getAllByText('Summary PDF document with category breakdowns.').length).toBeGreaterThan(1);
    expect(screen.getByText('Status: Verified by Supervisor Agent')).toBeInTheDocument();

    // Click download button inside preview modal
    const downloadBtns = screen.getAllByRole('button', { name: /Download/i });
    const modalDownloadBtn = downloadBtns[downloadBtns.length - 1];
    fireEvent.click(modalDownloadBtn);

    expect(createObjectURLMock).toHaveBeenCalled();
    expect(revokeObjectURLMock).toHaveBeenCalled();
  });

  it('executes full chatStore execution flow producing completing status and generated artifact', async () => {
    vi.useFakeTimers();

    const plan: PlannerPlan = {
      workflow_spec: 'Create EV Presentation',
      tasks: [
        { task_id: 't1', task_name: 'Collect Market Data', description: 'Search market facts', assigned_agent: 'Worker', required_tool: 'web_search' },
        { task_id: 't2', task_name: 'Build Presentation Deck', description: 'Generate pptx deck', assigned_agent: 'Worker', required_tool: 'ppt_generator' },
      ],
    };

    useChatStore.getState().executePlan(plan);

    expect(useChatStore.getState().currentStatus).toBe('executing');
    expect(useChatStore.getState().messages.length).toBe(1);

    // Fast-forward progress simulation timers
    await vi.advanceTimersByTimeAsync(3000);

    const state = useChatStore.getState();
    expect(state.currentStatus).toBe('completed');
    expect(state.messages.length).toBe(2);
    expect(state.messages[1].artifactData?.filename).toBe('EV_Comprehensive_Presentation.pptx');
    expect(state.messages[1].artifactData?.type).toBe('PPTX');

    vi.useRealTimers();
  });
});

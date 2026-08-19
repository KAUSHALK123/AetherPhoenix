import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PlanViewer } from '../components/chat/PlanViewer';
import type { PlannerPlan } from '../types/planner';

const mockPlan: PlannerPlan = {
  workflow_spec: 'Market Intelligence Deck Workflow',
  estimated_time_seconds: 45,
  confidence_score: 0.95,
  tasks: [
    {
      task_id: 'task-1',
      task_name: 'Scrape Market Competitors',
      description: 'Use Playwright to extract price tables',
      assigned_agent: 'Worker Agent',
      required_tool: 'browser_automation',
      risk_level: 'LOW',
      priority: 'HIGH',
      expected_output: 'Extracted JSON table',
    },
    {
      task_id: 'task-2',
      task_name: 'Generate PowerPoint Slides',
      description: 'Build 5 slides with executive chart',
      assigned_agent: 'Worker Agent',
      required_tool: 'ppt_generator',
      risk_level: 'MEDIUM',
      priority: 'HIGH',
      expected_output: 'Generated .pptx file',
    },
  ],
  required_permissions: ['BROWSER_ACCESS'],
  risks: ['External site rate limits'],
};

describe('PlanViewer', () => {
  it('renders task names, agents, and tools', () => {
    render(<PlanViewer plan={mockPlan} />);

    expect(screen.getByText('Market Intelligence Deck Workflow')).toBeInTheDocument();
    expect(screen.getByText('Scrape Market Competitors')).toBeInTheDocument();
    expect(screen.getByText('Generate PowerPoint Slides')).toBeInTheDocument();
    expect(screen.getByText('browser_automation')).toBeInTheDocument();
    expect(screen.getByText('ppt_generator')).toBeInTheDocument();
  });

  it('toggles between Visual View and Raw JSON view', () => {
    render(<PlanViewer plan={mockPlan} />);

    const toggleButton = screen.getByRole('button', { name: /Raw JSON/i });
    fireEvent.click(toggleButton);

    expect(screen.getByText(/JSON Contract/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Visual View/i })).toBeInTheDocument();
  });

  it('calls onApprove callback when Approve button is clicked', () => {
    const handleApprove = vi.fn();
    render(<PlanViewer plan={mockPlan} onApprove={handleApprove} />);

    const approveButton = screen.getByRole('button', { name: /Approve & Execute Plan/i });
    fireEvent.click(approveButton);
    expect(handleApprove).toHaveBeenCalledOnce();
  });
});

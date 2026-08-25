import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { PlanReviewPage } from '../pages/PlanReviewPage';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('PlanReviewPage (Stitch Fidelity)', () => {
  it('renders workflow DAG steps, analysis panel, and permissions', () => {
    render(
      <BrowserRouter>
        <PlanReviewPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Plan Review')).toBeInTheDocument();
    expect(screen.getByText('Execution Workflow')).toBeInTheDocument();
    expect(screen.getByText('Scan Downloads Directory')).toBeInTheDocument();
    expect(screen.getByText('Analysis')).toBeInTheDocument();
    expect(screen.getByText('File System Access')).toBeInTheDocument();
  });

  it('navigates to execution on Approve & Execute click', () => {
    render(
      <BrowserRouter>
        <PlanReviewPage />
      </BrowserRouter>
    );

    const approveBtn = screen.getByRole('button', { name: /Approve & Execute/i });
    fireEvent.click(approveBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/execution');
  });
});

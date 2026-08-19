import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { LandingPage } from '../pages/LandingPage';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('LandingPage (Stitch Fidelity)', () => {
  it('renders brand title and Stitch hero headline', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getAllByText(/AetherPhoenix/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Open Source • Runs on your machine/i)).toBeInTheDocument();
    expect(screen.getByText(/The AI that/i)).toBeInTheDocument();
  });

  it('navigates to chat when Get started button is clicked', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    const startButton = screen.getByRole('button', { name: /Get started/i });
    fireEvent.click(startButton);
    expect(mockNavigate).toHaveBeenCalledWith('/chat');
  });

  it('displays System Capabilities and Generated Artifacts', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Browser Automation/i)).toBeInTheDocument();
    expect(screen.getByText(/Desktop Control/i)).toBeInTheDocument();
    expect(screen.getByText(/CLI Executor/i)).toBeInTheDocument();
    expect(screen.getByText(/Web Research/i)).toBeInTheDocument();
    expect(screen.getByText(/Q3 AI Strategy Overview/i)).toBeInTheDocument();
    expect(screen.getByText(/Market Analysis Report/i)).toBeInTheDocument();
  });
});

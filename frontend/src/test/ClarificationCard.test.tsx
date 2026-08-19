import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClarificationCard } from '../components/chat/ClarificationCard';

describe('ClarificationCard', () => {
  it('renders question and suggested options', () => {
    const handleSubmit = vi.fn();
    render(
      <ClarificationCard
        question="Should I include historical trend analysis?"
        options={['Yes, include 5 years', 'No, current year only']}
        onSubmit={handleSubmit}
      />
    );

    expect(
      screen.getByText('Should I include historical trend analysis?')
    ).toBeInTheDocument();
    expect(screen.getByText('Yes, include 5 years')).toBeInTheDocument();
  });

  it('selects option and submits answer on submit click', () => {
    const handleSubmit = vi.fn();
    render(
      <ClarificationCard
        question="Select output format"
        options={['PowerPoint Presentation', 'PDF Report']}
        onSubmit={handleSubmit}
      />
    );

    const optionButton = screen.getByText('PowerPoint Presentation');
    fireEvent.click(optionButton);

    const submitButton = screen.getByRole('button', { name: /Submit/i });
    fireEvent.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledWith('PowerPoint Presentation');
  });
});

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PermissionsPage } from '../pages/PermissionsPage';

describe('PermissionsPage (Stitch Fidelity)', () => {
  it('renders Active Requests, System Shield, and History', () => {
    render(<PermissionsPage />);

    expect(screen.getByText('Permission Center')).toBeInTheDocument();
    expect(screen.getByText('System Shield Active')).toBeInTheDocument();
    expect(screen.getByText('Active Requests')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
  });

  it('handles Allow and Deny button clicks', () => {
    render(<PermissionsPage />);

    const allowBtn = screen.getByRole('button', { name: /ALLOW/i });
    expect(allowBtn).toBeInTheDocument();
    fireEvent.click(allowBtn);

    const denyBtn = screen.getByRole('button', { name: /DENY/i });
    expect(denyBtn).toBeInTheDocument();
    fireEvent.click(denyBtn);
  });
});

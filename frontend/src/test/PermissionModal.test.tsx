import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PermissionModal } from '../components/permissions/PermissionModal';
import type { PermissionRequest } from '../types/permission';

const mockRequest: PermissionRequest = {
  request_id: 'req-test-123',
  workflow_id: 'wf-test-456',
  task_id: 'task-test-789',
  permission_type: 'DESKTOP_AUTOMATION',
  reason: 'Simulate mouse clicks in login window',
  risk_level: 'HIGH',
  status: 'PENDING',
};

describe('PermissionModal', () => {
  it('renders permission details and risk badge', () => {
    render(
      <PermissionModal
        request={mockRequest}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    );

    expect(screen.getByText('Security Permission Required')).toBeInTheDocument();
    expect(screen.getByText('DESKTOP_AUTOMATION')).toBeInTheDocument();
    expect(screen.getByText('Simulate mouse clicks in login window')).toBeInTheDocument();
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument();
  });

  it('calls onApprove when Allow Action is clicked', async () => {
    const handleApprove = vi.fn().mockResolvedValue(undefined);
    render(
      <PermissionModal
        request={mockRequest}
        onApprove={handleApprove}
        onReject={vi.fn()}
      />
    );

    const allowButton = screen.getByRole('button', { name: /Allow Action/i });
    await act(async () => {
      fireEvent.click(allowButton);
    });

    expect(handleApprove).toHaveBeenCalledWith('req-test-123');
  });

  it('reveals reason input on first Deny click and calls onReject on confirmation', async () => {
    const handleReject = vi.fn().mockResolvedValue(undefined);
    render(
      <PermissionModal
        request={mockRequest}
        onApprove={vi.fn()}
        onReject={handleReject}
      />
    );

    const denyButton = screen.getByRole('button', { name: /^Deny$/i });
    await act(async () => {
      fireEvent.click(denyButton);
    });

    const confirmDenyButton = screen.getByRole('button', { name: /Confirm Deny/i });
    await act(async () => {
      fireEvent.click(confirmDenyButton);
    });

    expect(handleReject).toHaveBeenCalledWith('req-test-123', undefined);
  });
});

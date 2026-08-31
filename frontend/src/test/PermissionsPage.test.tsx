import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PermissionsPage } from '../pages/PermissionsPage';
import { permissionService } from '../services/permissionService';

vi.mock('../services/permissionService', () => ({
  permissionService: {
    getPendingPermissions: vi.fn(),
    getAllPermissions: vi.fn(),
    approvePermission: vi.fn(),
    rejectPermission: vi.fn(),
  },
}));

describe('PermissionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(permissionService.getPendingPermissions).mockResolvedValue([]);
    vi.mocked(permissionService.getAllPermissions).mockResolvedValue([]);
  });

  it('renders Active Requests, System Shield, and History sections', async () => {
    render(<PermissionsPage />);

    expect(screen.getByText('Permission Center')).toBeInTheDocument();
    expect(screen.getByText('System Shield Active')).toBeInTheDocument();
    expect(screen.getByText('Active Requests')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();

    await waitFor(() => {
      expect(permissionService.getPendingPermissions).toHaveBeenCalled();
    });
  });

  it('handles Allow and Deny button clicks on fallback/active requests', async () => {
    render(<PermissionsPage />);

    const allowBtn = screen.getByRole('button', { name: /ALLOW/i });
    expect(allowBtn).toBeInTheDocument();
    fireEvent.click(allowBtn);

    const denyBtn = screen.getByRole('button', { name: /DENY/i });
    expect(denyBtn).toBeInTheDocument();
    fireEvent.click(denyBtn);
  });
});

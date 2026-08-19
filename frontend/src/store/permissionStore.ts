import { create } from 'zustand';
import type { PermissionRequest } from '../types/permission';
import { permissionService } from '../services/permissionService';

interface PermissionState {
  pendingRequests: PermissionRequest[];
  history: PermissionRequest[];
  loading: boolean;
  error: string | null;
  activeModalRequest: PermissionRequest | null;

  // Actions
  fetchPending: () => Promise<void>;
  fetchAll: () => Promise<void>;
  approveRequest: (requestId: string, message?: string) => Promise<void>;
  rejectRequest: (requestId: string, message?: string) => Promise<void>;
  dismissModal: () => void;
}

export const usePermissionStore = create<PermissionState>((set, get) => ({
  pendingRequests: [],
  history: [],
  loading: false,
  error: null,
  activeModalRequest: null,

  fetchPending: async () => {
    try {
      const data = await permissionService.getPendingPermissions();
      set({
        pendingRequests: data,
        activeModalRequest: data.length > 0 ? data[0] : null,
      });
    } catch (err) {
      console.error('Failed to fetch pending permissions', err);
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null });
    try {
      const data = await permissionService.getAllPermissions();
      set({ history: data, loading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch permission history';
      set({ error: message, loading: false });
    }
  },

  approveRequest: async (requestId: string, message?: string) => {
    try {
      await permissionService.approvePermission(requestId, message);
      set((state) => {
        const remaining = state.pendingRequests.filter((p) => p.request_id !== requestId);
        return {
          pendingRequests: remaining,
          activeModalRequest: remaining.length > 0 ? remaining[0] : null,
        };
      });
      // Refresh list
      get().fetchAll();
    } catch (err) {
      console.error('Failed to approve permission', err);
    }
  },

  rejectRequest: async (requestId: string, message?: string) => {
    try {
      await permissionService.rejectPermission(requestId, message);
      set((state) => {
        const remaining = state.pendingRequests.filter((p) => p.request_id !== requestId);
        return {
          pendingRequests: remaining,
          activeModalRequest: remaining.length > 0 ? remaining[0] : null,
        };
      });
      // Refresh list
      get().fetchAll();
    } catch (err) {
      console.error('Failed to reject permission', err);
    }
  },

  dismissModal: () => {
    set({ activeModalRequest: null });
  },
}));

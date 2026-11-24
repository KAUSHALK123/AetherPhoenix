import { request, API_BASE_URL } from './apiClient';

export interface TabInfo {
  index: number;
  url: string;
  title: string;
}

export interface LiveBrowserState {
  active: boolean;
  session_id: string | null;
  state: 'idle' | 'loading' | 'ready' | 'acting' | 'verifying' | 'error' | 'closed';
  current_url: string;
  page_title: string;
  tab_count: number;
  active_tab_index: number;
  tabs: TabInfo[];
  last_action: string | null;
  last_action_status: 'SUCCESS' | 'FAILED' | null;
  last_verification: string | null;
  live_frame_base64: string | null;
  interactive_elements_count: number;
}

export interface InteractiveElementInfo {
  selector: string;
  tag_name: string;
  text: string;
  role: string;
  is_visible: boolean;
  is_enabled: boolean;
  attributes: Record<string, string>;
  rect: { x: number; y: number; width: number; height: number };
}

export const browserService = {
  getLiveSession: async (): Promise<LiveBrowserState> => {
    return request<LiveBrowserState>('/api/v1/browser/session');
  },

  startSession: async (headless?: boolean, authProfile?: string) => {
    return request<{ success: boolean; data?: any; live_state: LiveBrowserState }>(
      '/api/v1/browser/session/start',
      {
        method: 'POST',
        body: JSON.stringify({ headless, auth_profile: authProfile }),
      }
    );
  },

  closeSession: async () => {
    return request<{ success: boolean; error?: string }>('/api/v1/browser/session/close', {
      method: 'POST',
    });
  },

  navigate: async (url: string, timeoutMs: number = 30000) => {
    return request<{ success: boolean; data?: any; live_state: LiveBrowserState }>(
      '/api/v1/browser/navigate',
      {
        method: 'POST',
        body: JSON.stringify({ url, timeout_ms: timeoutMs }),
      }
    );
  },

  interact: async (selector: string, action: string = 'click', value?: string) => {
    return request<{ success: boolean; data?: any; live_state: LiveBrowserState }>(
      '/api/v1/browser/interact',
      {
        method: 'POST',
        body: JSON.stringify({ selector, action, value }),
      }
    );
  },

  executeStep: async (
    action: string,
    target: string,
    value?: string,
    expectedOutcome?: string
  ) => {
    return request<{ success: boolean; data?: any; live_state: LiveBrowserState }>(
      '/api/v1/browser/step',
      {
        method: 'POST',
        body: JSON.stringify({ action, target, value, expected_outcome: expectedOutcome }),
      }
    );
  },

  manageTabs: async (
    action: 'new' | 'switch' | 'close' | 'list',
    url?: string,
    tabIndex?: number
  ) => {
    return request<{ success: boolean; data?: any; live_state: LiveBrowserState }>(
      '/api/v1/browser/tabs',
      {
        method: 'POST',
        body: JSON.stringify({ action, url, tab_index: tabIndex }),
      }
    );
  },

  getInteractiveElements: async (
    limit: number = 50
  ): Promise<{ elements: InteractiveElementInfo[]; count: number }> => {
    return request<{ elements: InteractiveElementInfo[]; count: number }>(
      `/api/v1/browser/elements?limit=${limit}`
    );
  },

  getStreamUrl: (): string => {
    return `${API_BASE_URL}/api/v1/browser/stream`;
  },
};

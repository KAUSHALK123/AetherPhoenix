import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LiveBrowserPanel } from '../components/browser/LiveBrowserPanel';
import { browserService } from '../services/browserService';

vi.mock('../services/browserService', () => ({
  browserService: {
    getLiveSession: vi.fn(),
    startSession: vi.fn(),
    closeSession: vi.fn(),
    navigate: vi.fn(),
    interact: vi.fn(),
    executeStep: vi.fn(),
    manageTabs: vi.fn(),
    getInteractiveElements: vi.fn(),
    getStreamUrl: vi.fn(() => 'http://localhost:8000/api/v1/browser/stream'),
  },
}));

describe('LiveBrowserPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders idle state with launch button when no session is active', async () => {
    vi.mocked(browserService.getLiveSession).mockResolvedValue({
      active: false,
      session_id: null,
      state: 'idle',
      current_url: 'about:blank',
      page_title: '',
      tab_count: 0,
      active_tab_index: 0,
      tabs: [],
      last_action: null,
      last_action_status: null,
      last_verification: null,
      live_frame_base64: null,
      interactive_elements_count: 0,
    });

    render(<LiveBrowserPanel />);

    expect(screen.getByText('Live Browser Session')).toBeDefined();
    expect(screen.getByText('IDLE')).toBeDefined();
    expect(screen.getByText('Browser Idle')).toBeDefined();
    expect(screen.getByText('Launch Browser Session')).toBeDefined();
  });

  it('renders active browser session with URL and status badge', async () => {
    vi.mocked(browserService.getLiveSession).mockResolvedValue({
      active: true,
      session_id: 'session-123',
      state: 'ready',
      current_url: 'https://www.canva.com',
      page_title: 'Canva - Visual Suite for Everyone',
      tab_count: 1,
      active_tab_index: 0,
      tabs: [{ index: 0, url: 'https://www.canva.com', title: 'Canva' }],
      last_action: 'Navigated to https://www.canva.com',
      last_action_status: 'SUCCESS',
      last_verification: 'Page navigated to https://www.canva.com',
      live_frame_base64: null,
      interactive_elements_count: 5,
    });

    render(<LiveBrowserPanel />);

    await waitFor(() => {
      expect(screen.getByText('READY')).toBeDefined();
      expect(screen.getByText('Canva - Visual Suite for Everyone')).toBeDefined();
      expect(screen.getByText('Action:')).toBeDefined();
      expect(screen.getByText('Navigated to https://www.canva.com')).toBeDefined();
    });
  });

  it('navigates to URL when user submits address bar form', async () => {
    vi.mocked(browserService.getLiveSession).mockResolvedValue({
      active: true,
      session_id: 'session-123',
      state: 'ready',
      current_url: 'about:blank',
      page_title: 'Blank Page',
      tab_count: 1,
      active_tab_index: 0,
      tabs: [],
      last_action: null,
      last_action_status: null,
      last_verification: null,
      live_frame_base64: null,
      interactive_elements_count: 0,
    });

    vi.mocked(browserService.navigate).mockResolvedValue({
      success: true,
      live_state: {
        active: true,
        session_id: 'session-123',
        state: 'ready',
        current_url: 'https://github.com',
        page_title: 'GitHub',
        tab_count: 1,
        active_tab_index: 0,
        tabs: [{ index: 0, url: 'https://github.com', title: 'GitHub' }],
        last_action: 'Navigated to https://github.com',
        last_action_status: 'SUCCESS',
        last_verification: 'GitHub loaded',
        live_frame_base64: null,
        interactive_elements_count: 10,
      },
    });

    render(<LiveBrowserPanel />);

    const input = screen.getByPlaceholderText(/Enter website URL/i);
    fireEvent.change(input, { target: { value: 'https://github.com' } });

    const goButton = screen.getByRole('button', { name: /^Go$/i });
    fireEvent.click(goButton);

    await waitFor(() => {
      expect(browserService.navigate).toHaveBeenCalledWith('https://github.com');
    });
  });

  it('toggles interactive DOM elements drawer', async () => {
    vi.mocked(browserService.getLiveSession).mockResolvedValue({
      active: true,
      session_id: 'session-123',
      state: 'ready',
      current_url: 'https://docs.python.org/3/',
      page_title: 'Python Documentation',
      tab_count: 1,
      active_tab_index: 0,
      tabs: [],
      last_action: null,
      last_action_status: null,
      last_verification: null,
      live_frame_base64: null,
      interactive_elements_count: 2,
    });

    vi.mocked(browserService.getInteractiveElements).mockResolvedValue({
      elements: [
        {
          selector: 'input[name="q"]',
          tag_name: 'input',
          text: 'Quick search',
          role: 'searchbox',
          is_visible: true,
          is_enabled: true,
          attributes: { name: 'q' },
          rect: { x: 10, y: 10, width: 200, height: 30 },
        },
      ],
      count: 1,
    });

    render(<LiveBrowserPanel />);

    const inspectBtn = screen.getByTitle('Inspect Interactive DOM Elements');
    fireEvent.click(inspectBtn);

    await waitFor(() => {
      expect(browserService.getInteractiveElements).toHaveBeenCalled();
      expect(screen.getByText('Quick search')).toBeDefined();
    });
  });
});

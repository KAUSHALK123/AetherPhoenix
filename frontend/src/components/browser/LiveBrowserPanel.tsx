import React, { useState, useEffect, useRef } from 'react';
import { browserService, type LiveBrowserState, type InteractiveElementInfo } from '../../services/browserService';

interface LiveBrowserPanelProps {
  onClose?: () => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export const LiveBrowserPanel: React.FC<LiveBrowserPanelProps> = ({
  onClose,
  isExpanded = false,
  onToggleExpand,
}) => {
  const [browserState, setBrowserState] = useState<LiveBrowserState>({
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

  const [urlInput, setUrlInput] = useState('');
  const [isNavigating, setIsNavigating] = useState(false);
  const [showElementsDrawer, setShowElementsDrawer] = useState(false);
  const [elements, setElements] = useState<InteractiveElementInfo[]>([]);
  const [loadingElements, setLoadingElements] = useState(false);
  const [activeTab, setActiveTab] = useState<number>(0);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Poll or connect to SSE stream
  useEffect(() => {
    // 1. Initial fetch
    browserService.getLiveSession().then((st) => {
      setBrowserState(st);
      if (st.current_url && st.current_url !== 'about:blank') {
        setUrlInput(st.current_url);
      }
      setActiveTab(st.active_tab_index || 0);
    }).catch(() => {});

    // 2. Setup Server-Sent Events stream for high-frequency live frame & status updates
    try {
      const sseUrl = browserService.getStreamUrl();
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data: LiveBrowserState = JSON.parse(event.data);
          if (data && data.state) {
            setBrowserState((prev) => ({
              ...prev,
              ...data,
              live_frame_base64: data.live_frame_base64 || prev.live_frame_base64,
            }));
            if (data.current_url && data.current_url !== 'about:blank') {
              setUrlInput(data.current_url);
            }
            setActiveTab(data.active_tab_index || 0);
          }
        } catch {
          // ignore stream parse errors
        }
      };

      es.onerror = () => {
        // Fallback polling if SSE disconnects
      };
    } catch {
      // ignore
    }

    // 3. Fallback polling interval every 2.5 seconds
    const interval = setInterval(() => {
      browserService.getLiveSession().then((st) => {
        if (st) {
          setBrowserState((prev) => ({
            ...prev,
            ...st,
            live_frame_base64: st.live_frame_base64 || prev.live_frame_base64,
          }));
        }
      }).catch(() => {});
    }, 2500);

    return () => {
      clearInterval(interval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleNavigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!urlInput.trim()) return;

    let target = urlInput.trim();
    if (!target.startsWith('http://') && !target.startsWith('https://')) {
      target = `https://${target}`;
    }

    setIsNavigating(true);
    try {
      const res = await browserService.navigate(target);
      if (res.live_state) {
        setBrowserState(res.live_state);
      }
    } catch {
      // error handled
    } finally {
      setIsNavigating(false);
    }
  };

  const handleStartSession = async () => {
    setIsNavigating(true);
    try {
      const res = await browserService.startSession();
      if (res.live_state) {
        setBrowserState(res.live_state);
      }
    } catch {
      // error handled
    } finally {
      setIsNavigating(false);
    }
  };

  const handleCloseSession = async () => {
    try {
      await browserService.closeSession();
      setBrowserState((prev) => ({
        ...prev,
        active: false,
        state: 'closed',
        live_frame_base64: null,
      }));
    } catch {
      // error handled
    }
  };

  const handleFetchElements = async () => {
    setShowElementsDrawer((prev) => !prev);
    if (!showElementsDrawer) {
      setLoadingElements(true);
      try {
        const res = await browserService.getInteractiveElements(40);
        setElements(res.elements || []);
      } catch {
        setElements([]);
      } finally {
        setLoadingElements(false);
      }
    }
  };

  const handleTabSwitch = async (index: number) => {
    setActiveTab(index);
    try {
      const res = await browserService.manageTabs('switch', undefined, index);
      if (res.live_state) {
        setBrowserState(res.live_state);
      }
    } catch {
      // error handled
    }
  };

  const handleNewTab = async () => {
    try {
      const res = await browserService.manageTabs('new', 'https://www.google.com');
      if (res.live_state) {
        setBrowserState(res.live_state);
      }
    } catch {
      // error handled
    }
  };

  const getStatusBadge = () => {
    const s = browserState.state.toLowerCase();
    if (s === 'ready') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          READY
        </span>
      );
    }
    if (s === 'loading') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
          LOADING
        </span>
      );
    }
    if (s === 'acting' || s === 'verifying') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" />
          {s.toUpperCase()}
        </span>
      );
    }
    if (s === 'error') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
          ERROR
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
        IDLE
      </span>
    );
  };

  return (
    <div
      className={`flex flex-col bg-slate-950/95 backdrop-blur-2xl border border-indigo-500/30 rounded-3xl shadow-2xl overflow-hidden transition-all duration-300 shrink-0 z-30 mb-6 mr-6 ${
        isExpanded ? 'w-[750px] h-[calc(100vh-8rem)]' : 'w-[480px] h-[calc(100vh-10rem)]'
      }`}
    >
      {/* 1. Header Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800/80 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <span className="material-symbols-outlined text-base">public</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold font-mono text-white tracking-wide">
                Live Browser Session
              </h3>
              {getStatusBadge()}
            </div>
            <p className="text-[10px] text-slate-400 truncate max-w-[200px]">
              {browserState.page_title || 'Chromium Engine'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={handleFetchElements}
            className={`p-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
              showElementsDrawer
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-indigo-300 hover:bg-slate-800'
            }`}
            title="Inspect Interactive DOM Elements"
          >
            <span className="material-symbols-outlined text-sm">view_in_ar</span>
          </button>

          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-xs transition-colors cursor-pointer"
              title={isExpanded ? 'Collapse Panel' : 'Expand Panel'}
            >
              <span className="material-symbols-outlined text-sm">
                {isExpanded ? 'close_fullscreen' : 'open_in_full'}
              </span>
            </button>
          )}

          {browserState.active ? (
            <button
              onClick={handleCloseSession}
              className="p-1.5 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-950/40 text-xs transition-colors cursor-pointer"
              title="Terminate Browser Session"
            >
              <span className="material-symbols-outlined text-sm">power_settings_new</span>
            </button>
          ) : (
            <button
              onClick={handleStartSession}
              className="p-1.5 rounded-lg text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/40 text-xs transition-colors cursor-pointer"
              title="Start Browser Session"
            >
              <span className="material-symbols-outlined text-sm">play_arrow</span>
            </button>
          )}

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-xs transition-colors cursor-pointer"
              title="Close Panel"
            >
              <span className="material-symbols-outlined text-sm">close</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. Browser Tabs Bar */}
      {browserState.tabs && browserState.tabs.length > 0 && (
        <div className="flex items-center gap-1 px-3 py-1.5 bg-slate-900/60 border-b border-slate-800/60 overflow-x-auto no-scrollbar shrink-0 text-xs font-mono">
          {browserState.tabs.map((tab) => (
            <button
              key={tab.index}
              onClick={() => handleTabSwitch(tab.index)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] truncate max-w-[140px] cursor-pointer transition-colors ${
                activeTab === tab.index
                  ? 'bg-slate-800 text-white font-bold border border-indigo-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <span className="material-symbols-outlined text-xs text-indigo-400">tab</span>
              <span className="truncate">{tab.title || `Tab ${tab.index + 1}`}</span>
            </button>
          ))}
          <button
            onClick={handleNewTab}
            className="p-1 rounded text-slate-400 hover:text-indigo-400 hover:bg-slate-800 text-xs transition-colors cursor-pointer ml-1"
            title="Open New Tab"
          >
            <span className="material-symbols-outlined text-xs">add</span>
          </button>
        </div>
      )}

      {/* 3. Address / URL Bar */}
      <form
        onSubmit={handleNavigate}
        className="flex items-center gap-2 px-3 py-2 bg-slate-900/40 border-b border-slate-800/80 shrink-0"
      >
        <button
          type="button"
          onClick={() => handleNavigate()}
          className="p-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
          title="Reload"
        >
          <span className={`material-symbols-outlined text-sm ${isNavigating ? 'animate-spin' : ''}`}>
            refresh
          </span>
        </button>

        <div className="flex-1 flex items-center gap-2 bg-slate-950/80 border border-slate-800 focus-within:border-indigo-500/70 rounded-xl px-2.5 py-1 text-xs">
          <span className="material-symbols-outlined text-xs text-emerald-400">lock</span>
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="Enter website URL (e.g. https://www.canva.com, https://github.com)..."
            className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 focus:outline-none font-mono text-[11px]"
          />
        </div>

        <button
          type="submit"
          disabled={isNavigating || !urlInput.trim()}
          className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-lg text-xs font-semibold cursor-pointer transition-colors shadow-sm"
        >
          Go
        </button>
      </form>

      {/* 4. Observe-Act-Verify Action Telemetry Banner */}
      {browserState.last_action && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900/70 border-b border-indigo-500/20 text-[11px] font-mono shrink-0">
          <div className="flex items-center gap-1.5 truncate text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-cyan-400 font-bold">Action:</span>
            <span className="truncate">{browserState.last_action}</span>
          </div>
          {browserState.last_action_status && (
            <span
              className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                browserState.last_action_status === 'SUCCESS'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-red-500/10 text-red-400 border border-red-500/30'
              }`}
            >
              {browserState.last_action_status}
            </span>
          )}
        </div>
      )}

      {/* 5. Live Browser Viewport */}
      <div className="flex-1 relative bg-black/90 flex items-center justify-center overflow-hidden">
        {browserState.live_frame_base64 ? (
          <img
            src={`data:image/jpeg;base64,${browserState.live_frame_base64}`}
            alt="Live Browser Page"
            className="w-full h-full object-contain select-none"
          />
        ) : browserState.active ? (
          <div className="flex flex-col items-center justify-center space-y-3 p-6 text-center">
            <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs font-mono text-slate-400">Loading browser session frame...</p>
            <p className="text-[11px] text-slate-500">Connecting to live Chromium viewport</p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-4 p-8 text-center">
            <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
              <span className="material-symbols-outlined text-3xl">desktop_windows</span>
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-white">Browser Idle</h4>
              <p className="text-xs text-slate-400 max-w-xs">
                Launch a browser session or ask AetherPhoenix to open Canva, GitHub, or documentation.
              </p>
            </div>
            <button
              onClick={handleStartSession}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/30 cursor-pointer transition-all active:scale-95 flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-sm">open_in_browser</span>
              Launch Browser Session
            </button>
          </div>
        )}

        {/* Action Verification Toast Overlay */}
        {browserState.last_verification && (
          <div className="absolute bottom-3 left-3 right-3 bg-slate-900/95 backdrop-blur-md border border-emerald-500/40 rounded-xl p-2.5 shadow-xl flex items-center gap-2 text-xs font-mono text-emerald-300">
            <span className="material-symbols-outlined text-emerald-400 text-sm">verified</span>
            <span className="truncate flex-1">{browserState.last_verification}</span>
          </div>
        )}
      </div>

      {/* 6. Interactive Element Discovery Drawer (Collapsible) */}
      {showElementsDrawer && (
        <div className="h-44 bg-slate-950 border-t border-slate-800 p-3 overflow-y-auto space-y-2 shrink-0">
          <div className="flex items-center justify-between pb-1 border-b border-slate-800">
            <h5 className="text-[11px] font-bold font-mono text-slate-300 uppercase">
              Discovered Interactive DOM Elements ({elements.length})
            </h5>
            <button
              onClick={handleFetchElements}
              className="text-[10px] text-indigo-400 hover:underline cursor-pointer"
            >
              Refresh
            </button>
          </div>

          {loadingElements ? (
            <p className="text-xs text-slate-500 font-mono py-2 text-center">Scanning page DOM...</p>
          ) : elements.length === 0 ? (
            <p className="text-xs text-slate-500 font-mono py-2 text-center">No interactive elements detected on active page.</p>
          ) : (
            <div className="space-y-1.5">
              {elements.map((el, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] font-mono hover:border-indigo-500/40 transition-colors"
                >
                  <div className="flex items-center gap-2 truncate max-w-[320px]">
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-500/20 text-indigo-300">
                      {el.tag_name}
                    </span>
                    <span className="text-slate-200 truncate">{el.text || el.selector}</span>
                  </div>
                  <span className="text-[10px] text-slate-500 truncate max-w-[100px]">{el.selector}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

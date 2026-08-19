import React from 'react';
import { Sliders, Shield, Terminal, Save } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { Button } from '../components/common/Button';

export const SettingsPage: React.FC = () => {
  const executionMode = useChatStore((state) => state.executionMode);
  const setExecutionMode = useChatStore((state) => state.setExecutionMode);

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-sky-400" />
            Preferences & System Settings
          </h2>
          <p className="text-xs text-slate-400">
            Configure agent runtime behavior, security sandboxing & UI preferences
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => alert('Settings saved')}>
          <Save className="w-4 h-4 mr-1" />
          Save Changes
        </Button>
      </div>

      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
        {/* Execution Mode Setting */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Shield className="w-4 h-4 text-sky-400" />
            Default Execution Security Mode
          </label>
          <p className="text-xs text-slate-400">
            Controls how aggressively the system pauses for interactive human authorization.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            {[
              {
                mode: 'SAFE',
                desc: 'Prompt for all tool actions (mouse, browser, shell).',
              },
              {
                mode: 'ASSISTED',
                desc: 'Auto-run read-only tools; prompt for high-risk actions.',
              },
              {
                mode: 'AUTONOMOUS',
                desc: 'Full autonomy within sandboxed parameters.',
              },
            ].map(({ mode, desc }) => (
              <button
                key={mode}
                type="button"
                onClick={() =>
                  setExecutionMode(mode as 'SAFE' | 'ASSISTED' | 'AUTONOMOUS')
                }
                className={`p-4 rounded-xl border text-left transition-all ${
                  executionMode === mode
                    ? 'bg-sky-500/10 border-sky-500/50 shadow-md shadow-sky-500/10'
                    : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="text-xs font-mono font-bold text-slate-200 mb-1">
                  {mode}
                </div>
                <div className="text-[11px] text-slate-400 leading-relaxed">{desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Backend API Configuration */}
        <div className="space-y-2 pt-4 border-t border-slate-800">
          <label className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-sky-400" />
            Backend API Endpoint
          </label>
          <input
            type="text"
            readOnly
            value={import.meta.env.VITE_API_URL || 'http://localhost:8000'}
            className="glass-input text-xs font-mono w-full px-3.5 py-2.5 rounded-xl text-slate-400 cursor-not-allowed"
          />
          <span className="text-[11px] font-mono text-slate-500">
            Configured via VITE_API_URL environment variable
          </span>
        </div>
      </div>
    </div>
  );
};

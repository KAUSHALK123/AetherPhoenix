import React, { useState, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';

export const ExecutionPage: React.FC = () => {
  const activePlan = useChatStore((state) => state.activePlan);
  const [logs, setLogs] = useState<string[]>([
    'Initializing Workflow #83a2...',
    '[Planner] Analyzing goal: ORGANIZE DOWNLOADS',
    '[System] Scanning directory structure...',
    '[Worker] Found 142 files in /Downloads',
    '[Supervisor] Validating path integrity... OK',
    '[Worker] Creating directory: /Downloads/Images',
    '[Worker] Creating directory: /Downloads/Documents',
    '[Worker] Moving high_res_render.png to /Images...',
  ]);

  const [elapsed, setElapsed] = useState(8);

  useEffect(() => {
    const logInterval = setInterval(() => {
      setLogs((prev) => {
        const randId = Math.floor(Math.random() * 1000);
        const next = [...prev, `[Worker] Moved item_${randId}.pdf to /Documents`];
        if (next.length > 20) next.shift();
        return next;
      });
    }, 2500);

    const timerInterval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => {
      clearInterval(logInterval);
      clearInterval(timerInterval);
    };
  }, []);

  const goalTitle = activePlan?.workflow_spec || 'ORGANIZE DOWNLOADS';
  const formattedElapsed = `00:${elapsed < 10 ? '0' : ''}${elapsed}s`;
  const remaining = Math.max(0, 15 - elapsed);
  const formattedRemaining = `00:${remaining < 10 ? '0' : ''}${remaining}s`;

  return (
    <div className="flex flex-col flex-1 min-h-[calc(100vh-4rem)]">
      <main className="p-6 md:p-10 max-w-6xl mx-auto w-full flex flex-col gap-8 flex-1">
        {/* Header telemetry */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-surface-container-high border border-outline-variant rounded-full text-[10px] font-mono text-on-surface-muted">
                Workflow: #{activePlan ? 'active' : '83a2'}...
              </span>
              <span className="px-3 py-1 bg-primary/10 border border-primary/30 rounded-full text-accent-electric text-[10px] font-bold flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] animate-spin">autorenew</span> AUTO MODE
              </span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white uppercase">{goalTitle}</h1>
          </div>
          <div className="flex gap-8 text-right">
            <div>
              <p className="text-[10px] uppercase font-bold text-on-surface-muted">Elapsed</p>
              <p className="font-mono text-white text-lg">{formattedElapsed}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-on-surface-muted">Remaining</p>
              <p className="font-mono text-accent-electric text-lg">{formattedRemaining}</p>
            </div>
          </div>
        </div>

        {/* Agent Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Planner Agent Card */}
          <div className="glass-panel p-6 rounded-xl flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant">
                  <span className="material-symbols-outlined text-primary text-sm">account_tree</span>
                </div>
                <h3 className="font-bold text-white">Planner Agent</h3>
              </div>
              <span className="material-symbols-outlined text-accent-electric">check_circle</span>
            </div>
            <div className="mt-auto border-t border-outline-variant/20 pt-3">
              <p className="text-[10px] uppercase text-on-surface-muted font-bold">Status</p>
              <p className="text-sm text-emerald-400 font-semibold">Completed</p>
            </div>
          </div>

          {/* Worker Agent Card */}
          <div className="md:col-span-2 glass-panel p-6 rounded-xl border-primary/30 shadow-lg relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent pointer-events-none" />
            <div className="flex justify-between items-center relative z-10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center pulse-glow">
                  <span className="material-symbols-outlined text-white text-sm">build</span>
                </div>
                <h3 className="font-bold text-accent-electric">Worker Agent</h3>
              </div>
              <span className="px-3 py-1 bg-primary/20 text-accent-electric rounded text-[10px] font-bold">
                RUNNING
              </span>
            </div>
            <div className="mt-4 space-y-2 relative z-10">
              <div className="flex items-center gap-2 text-on-surface-muted text-sm line-through">
                <span className="material-symbols-outlined text-sm text-primary">check</span>
                Scan Directory
              </div>
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <div className="w-2 h-2 rounded-full bg-accent-electric animate-pulse" />
                Moving Files & Executing Pipeline...
              </div>
              <div className="flex items-center gap-2 text-on-surface-muted text-sm opacity-50">
                <span className="material-symbols-outlined text-sm">radio_button_unchecked</span>
                Cleanup & Supervisor Audit
              </div>
            </div>
          </div>
        </div>

        {/* Live System Logs Console */}
        <div className="flex-grow bg-surface-deep rounded-xl border border-outline-variant/30 flex flex-col overflow-hidden shadow-inner min-h-[250px]">
          <div className="bg-surface-container px-4 py-2 border-b border-outline-variant/30 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm text-on-surface-muted">terminal</span>
              <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-muted">
                System Logs
              </span>
            </div>
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-outline-variant" />
              <div className="w-2.5 h-2.5 rounded-full bg-outline-variant" />
            </div>
          </div>
          <div className="p-4 font-mono text-xs text-on-surface-muted space-y-1.5 overflow-y-auto no-scrollbar flex-1">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-4">
                <span className="text-outline-variant">12:04:{20 + (i % 60)}</span>
                <span
                  className={
                    log.includes('[Worker]')
                      ? 'text-accent-electric'
                      : log.includes('[Supervisor]')
                      ? 'text-emerald-400'
                      : 'text-primary'
                  }
                >
                  {log}
                </span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

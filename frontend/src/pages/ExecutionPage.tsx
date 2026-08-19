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
              <span className="px-3 py-1 bg-white/10 border border-white/20 rounded-full text-[10px] font-mono text-slate-300 backdrop-blur-md">
                Workflow: #{activePlan ? 'active' : '83a2'}...
              </span>
              <span className="px-3 py-1 bg-cyan-500/20 border border-cyan-400/40 rounded-full text-cyan-300 text-[10px] font-bold flex items-center gap-1 backdrop-blur-md">
                <span className="material-symbols-outlined text-[12px] animate-spin">autorenew</span> AUTO MODE
              </span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white uppercase drop-shadow">{goalTitle}</h1>
          </div>
          <div className="flex gap-8 text-right">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-300">Elapsed</p>
              <p className="font-mono text-white text-lg drop-shadow">{formattedElapsed}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-300">Remaining</p>
              <p className="font-mono text-cyan-300 text-lg drop-shadow">{formattedRemaining}</p>
            </div>
          </div>
        </div>

        {/* Agent Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Planner Agent Card */}
          <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
                  <span className="material-symbols-outlined text-cyan-300 text-sm">account_tree</span>
                </div>
                <h3 className="font-bold text-white">Planner Agent</h3>
              </div>
              <span className="material-symbols-outlined text-emerald-400">check_circle</span>
            </div>
            <div className="mt-6 border-t border-white/10 pt-3">
              <p className="text-[10px] uppercase text-slate-400 font-bold">Status</p>
              <p className="text-sm text-emerald-400 font-semibold">Completed</p>
            </div>
          </div>

          {/* Worker Agent Card */}
          <div className="md:col-span-2 glass-card p-6 rounded-2xl relative overflow-hidden">
            <div className="flex justify-between items-center relative z-10">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center">
                  <span className="material-symbols-outlined text-cyan-300 text-sm">build</span>
                </div>
                <h3 className="font-bold text-white">Worker Agent</h3>
              </div>
              <span className="px-3 py-1 bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 rounded-full text-[10px] font-bold font-mono">
                RUNNING
              </span>
            </div>
            <div className="mt-4 space-y-2 relative z-10">
              <div className="flex items-center gap-2 text-slate-400 text-sm line-through">
                <span className="material-symbols-outlined text-sm text-cyan-400">check</span>
                Scan Directory
              </div>
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                Moving Files & Executing Pipeline...
              </div>
              <div className="flex items-center gap-2 text-slate-400 text-sm opacity-50">
                <span className="material-symbols-outlined text-sm">radio_button_unchecked</span>
                Cleanup & Supervisor Audit
              </div>
            </div>
          </div>
        </div>

        {/* Live System Logs Console */}
        <div className="flex-grow glass-card rounded-2xl flex flex-col overflow-hidden min-h-[250px]">
          <div className="px-5 py-3 border-b border-white/10 flex justify-between items-center bg-black/20">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm text-cyan-400">terminal</span>
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-300 font-mono">
                System Logs
              </span>
            </div>
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
              <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
            </div>
          </div>
          <div className="p-5 font-mono text-xs text-slate-300 space-y-2 overflow-y-auto no-scrollbar flex-1 bg-black/30">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-4">
                <span className="text-slate-500">12:04:{20 + (i % 60)}</span>
                <span
                  className={
                    log.includes('[Worker]')
                      ? 'text-cyan-300'
                      : log.includes('[Supervisor]')
                      ? 'text-emerald-400'
                      : 'text-purple-300'
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

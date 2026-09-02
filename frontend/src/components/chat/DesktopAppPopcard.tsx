import React from 'react';
import type { DesktopAppData } from '../../types/planner';

interface DesktopAppPopcardProps {
  data: DesktopAppData;
}

export const DesktopAppPopcard: React.FC<DesktopAppPopcardProps> = ({ data }) => {
  return (
    <div className="bg-slate-900/90 backdrop-blur-xl border border-indigo-500/30 rounded-2xl p-4 shadow-xl space-y-3 font-sans max-w-md text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <span className="material-symbols-outlined text-lg">open_in_new</span>
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200">Desktop App Automation</h4>
            <p className="text-xs text-indigo-300 font-medium">{data.appName}</p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          ✓ LAUNCHED
        </span>
      </div>

      {/* App Details */}
      <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800/80 space-y-1.5 font-mono text-xs">
        <div className="flex justify-between text-slate-400">
          <span>Application:</span>
          <span className="text-slate-200 font-bold">{data.appName}</span>
        </div>
        {data.executablePath && (
          <div className="flex justify-between text-slate-400">
            <span>Executable:</span>
            <span className="text-indigo-400 truncate max-w-[200px]">{data.executablePath}</span>
          </div>
        )}
        <div className="flex justify-between text-slate-400">
          <span>Process Status:</span>
          <span className="text-emerald-400 font-bold">Active Desktop Window</span>
        </div>
      </div>

      <div className="text-[11px] font-mono text-slate-400 text-center">
        Executed via Desktop Automation Executor
      </div>
    </div>
  );
};

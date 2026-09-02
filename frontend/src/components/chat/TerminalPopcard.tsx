import React, { useState } from 'react';
import type { TerminalOutputData } from '../../types/planner';

export interface TerminalPopcardProps {
  terminalData: TerminalOutputData;
}

export const TerminalPopcard: React.FC<TerminalPopcardProps> = ({ terminalData }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(terminalData.stdout);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-950/95 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-5 shadow-2xl space-y-3.5 max-w-xl w-full">
      {/* Top Title Bar styled like a terminal header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-rose-500/80" />
            <div className="w-3 h-3 rounded-full bg-amber-500/80" />
            <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
          </div>
          <span className="text-xs font-bold font-mono text-emerald-400 flex items-center gap-1.5 ml-2">
            <span className="material-symbols-outlined text-sm">terminal</span>
            Command Output: {terminalData.command}
          </span>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-emerald-400 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
        >
          <span className="material-symbols-outlined text-xs">
            {copied ? 'check' : 'content_copy'}
          </span>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Monospace Output Shell Box */}
      <div className="bg-black/90 rounded-xl p-4 border border-slate-900 font-mono text-xs text-emerald-300/90 whitespace-pre-wrap max-h-64 overflow-y-auto leading-relaxed scrollbar-thin scrollbar-thumb-slate-800">
        {terminalData.stdout || 'Command completed with no stdout.'}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
        <span>Status: 0 (Success)</span>
        <span>Executed via WorkerAgent</span>
      </div>
    </div>
  );
};

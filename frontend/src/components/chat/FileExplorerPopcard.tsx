import React from 'react';
import type { FileExplorerData } from '../../types/planner';

interface FileExplorerPopcardProps {
  data: FileExplorerData;
}

export const FileExplorerPopcard: React.FC<FileExplorerPopcardProps> = ({ data }) => {
  const defaultItems = data.items || [
    { name: 'Documents', size: 'DIR', type: 'folder', dateModified: '2026-09-02' },
    { name: 'Projects', size: 'DIR', type: 'folder', dateModified: '2026-09-02' },
    { name: 'Report_Draft.pdf', size: '1.2 MB', type: 'file', dateModified: '2026-09-01' },
    { name: 'System_Config.json', size: '4 KB', type: 'file', dateModified: '2026-08-30' },
  ];

  return (
    <div className="bg-slate-900/90 backdrop-blur-xl border border-sky-500/30 rounded-2xl p-4 shadow-xl space-y-3 font-sans max-w-lg text-slate-100">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <span className="material-symbols-outlined text-lg">folder_open</span>
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200">OS File Explorer</h4>
            <p className="text-[11px] font-mono text-sky-400/90 truncate max-w-[240px]">
              {data.path}
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          ✓ VISIBLY OPENED
        </span>
      </div>

      {/* Directory Item Grid / List */}
      <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800/80 space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pb-1 border-b border-slate-800">
          <span>NAME</span>
          <span>SIZE / TYPE</span>
        </div>
        <div className="space-y-1.5 max-h-36 overflow-y-auto font-mono text-xs">
          {defaultItems.map((item, idx) => (
            <div key={idx} className="flex items-center justify-between text-slate-300 hover:bg-slate-900/60 px-1.5 py-1 rounded transition-colors">
              <div className="flex items-center gap-2">
                <span className={`material-symbols-outlined text-sm ${item.type === 'folder' ? 'text-amber-400' : 'text-slate-400'}`}>
                  {item.type === 'folder' ? 'folder' : 'description'}
                </span>
                <span className="truncate max-w-[180px]">{item.name}</span>
              </div>
              <span className="text-[11px] text-slate-400">{item.size}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span>Path: <strong className="text-slate-300">{data.path}</strong></span>
        <span className="text-emerald-400 font-semibold">Active Windows Shell</span>
      </div>
    </div>
  );
};

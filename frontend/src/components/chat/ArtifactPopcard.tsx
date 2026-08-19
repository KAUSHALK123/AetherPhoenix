import React from 'react';
import type { ArtifactItem } from '../../types/artifact';

export interface ArtifactPopcardProps {
  artifact: ArtifactItem;
}

export const ArtifactPopcard: React.FC<ArtifactPopcardProps> = ({ artifact }) => {
  const getIconAndColor = (type: string) => {
    switch (type.toUpperCase()) {
      case 'PPTX':
      case 'PRESENTATION':
        return { icon: 'co_present', bg: 'bg-indigo-500/20', text: 'text-indigo-400', border: 'border-indigo-500/30' };
      case 'PDF':
        return { icon: 'picture_as_pdf', bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' };
      case 'CSV':
        return { icon: 'table_chart', bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' };
      default:
        return { icon: 'description', bg: 'bg-slate-800', text: 'text-slate-300', border: 'border-slate-700' };
    }
  };

  const { icon, bg, text, border } = getIconAndColor(artifact.type);
  const sizeFormatted = artifact.size_bytes
    ? `${(artifact.size_bytes / 1024).toFixed(1)} KB`
    : '41 KB';

  const handleDownload = () => {
    const content = artifact.preview_content || `Generated artifact content for ${artifact.filename}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-4 max-w-xl w-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-11 h-11 rounded-xl ${bg} ${text} ${border} border flex items-center justify-center`}>
            <span className="material-symbols-outlined text-2xl">{icon}</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold font-mono uppercase px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ✓ Generated
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                {sizeFormatted}
              </span>
            </div>
            <h3 className="text-sm font-bold text-white truncate max-w-[280px] sm:max-w-sm mt-0.5">
              {artifact.filename}
            </h3>
          </div>
        </div>
        <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 text-[10px] font-bold font-mono">
          {artifact.type}
        </span>
      </div>

      {artifact.preview_content && (
        <div className="bg-slate-950/80 rounded-xl p-3.5 border border-slate-800/80 text-xs font-mono text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto leading-relaxed">
          {artifact.preview_content}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleDownload}
          className="flex-1 py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow cursor-pointer flex items-center justify-center gap-1.5"
        >
          <span className="material-symbols-outlined text-sm">download</span>
          Download
        </button>
        <button
          onClick={() => {
            alert(`Preview for ${artifact.filename}:\n\n${artifact.preview_content || 'Content is ready'}`);
          }}
          className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-sm">visibility</span>
          Preview
        </button>
      </div>
    </div>
  );
};

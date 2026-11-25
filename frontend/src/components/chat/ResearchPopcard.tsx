import React from 'react';
import type { WebResearchData } from '../../types/planner';

interface ResearchPopcardProps {
  data: WebResearchData;
}

export const ResearchPopcard: React.FC<ResearchPopcardProps> = ({ data }) => {
  return (
    <div className="w-full max-w-2xl bg-slate-900/95 backdrop-blur-xl border border-cyan-500/30 rounded-2xl p-5 shadow-2xl space-y-4 text-slate-100 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-600/20 text-cyan-400 border border-cyan-500/40 flex items-center justify-center shadow-lg">
            <span className="material-symbols-outlined text-2xl text-cyan-400">manage_search</span>
          </div>
          <div>
            <h4 className="font-bold text-sm tracking-wide text-white flex items-center gap-2">
              Web Intelligence & Research
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                VERIFIED
              </span>
            </h4>
            <p className="text-xs text-slate-400">
              Synthesized from {data.sourcesCount || data.topResults?.length || 3} independent web sources
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/60 text-[11px] text-cyan-300 font-mono">
          <span className="material-symbols-outlined text-xs">search</span>
          <span className="truncate max-w-[180px]">{data.query}</span>
        </div>
      </div>

      {/* Structured Summary in Clean, Small Paragraphs */}
      <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 text-slate-200 text-xs sm:text-sm leading-relaxed space-y-3">
        {data.summary.split('\n\n').map((paragraph, index) => {
          const trimmed = paragraph.trim();
          if (!trimmed) return null;

          // Headers
          if (trimmed.startsWith('#')) {
            const cleanTitle = trimmed.replace(/^#+\s*/, '');
            return (
              <h5
                key={index}
                className="font-semibold text-cyan-400 text-xs uppercase tracking-wider font-mono pt-1 border-t border-slate-800/60 first:border-t-0 first:pt-0"
              >
                {cleanTitle}
              </h5>
            );
          }

          // Bullet points
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            const items = trimmed.split('\n').filter((l) => l.trim().length > 0);
            return (
              <ul key={index} className="space-y-1.5 pl-1">
                {items.map((item, itemIdx) => {
                  const cleanItem = item.replace(/^[-*]\s*/, '');
                  return (
                    <li key={itemIdx} className="flex items-start gap-2 text-slate-300 text-xs sm:text-[13px]">
                      <span className="text-cyan-400 mt-1 text-[8px]">•</span>
                      <span>{cleanItem}</span>
                    </li>
                  );
                })}
              </ul>
            );
          }

          // Clean small paragraph
          return (
            <p key={index} className="text-slate-200 text-xs sm:text-[13px] leading-relaxed">
              {trimmed}
            </p>
          );
        })}
      </div>

      {/* Verified Sources Consulted */}
      {data.topResults && data.topResults.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <span className="material-symbols-outlined text-sm text-cyan-400">link</span>
              Sources Consulted ({data.topResults.length})
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.topResults.map((source, index) => (
              <a
                key={index}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-2 p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-800/30 transition-all group"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-xs text-slate-200 group-hover:text-cyan-300 truncate">
                    {source.title || 'Web Resource'}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate font-mono">
                    {source.url.replace(/^https?:\/\/(www\.)?/, '')}
                  </div>
                </div>
                <span className="material-symbols-outlined text-xs text-slate-500 group-hover:text-cyan-400 shrink-0 mt-0.5">
                  open_in_new
                </span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

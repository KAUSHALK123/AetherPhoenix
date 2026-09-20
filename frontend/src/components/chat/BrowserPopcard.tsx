import React from 'react';
import type { BrowserAutomationData } from '../../types/planner';

interface BrowserPopcardProps {
  data: BrowserAutomationData;
}

export const BrowserPopcard: React.FC<BrowserPopcardProps> = ({ data }) => {
  const isYouTube = data.url.toLowerCase().includes('youtube.com') || (data.siteName && data.siteName.toLowerCase().includes('youtube'));
  const isGoogle = data.url.toLowerCase().includes('google.com') || (data.siteName && data.siteName.toLowerCase().includes('google'));

  const handleOpenBrowser = () => {
    window.open(data.url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="w-full max-w-xl bg-slate-900/90 backdrop-blur-xl border border-indigo-500/30 rounded-2xl p-5 shadow-2xl space-y-4 text-slate-100 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
              isYouTube
                ? 'bg-red-600/20 text-red-400 border border-red-500/40'
                : isGoogle
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40'
                : 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/40'
            }`}
          >
            {isYouTube ? (
              <span className="material-symbols-outlined text-2xl text-red-500">smart_display</span>
            ) : isGoogle ? (
              <span className="material-symbols-outlined text-2xl text-blue-400">travel_explore</span>
            ) : (
              <span className="material-symbols-outlined text-2xl text-indigo-400">open_in_browser</span>
            )}
          </div>
          <div>
            <h4 className="font-bold text-sm tracking-wide text-white flex items-center gap-2">
              {data.siteName || (isYouTube ? 'YouTube Live Search' : isGoogle ? 'Google Search' : 'Browser Automation')}
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {data.status}
              </span>
            </h4>
            <p className="text-xs text-slate-400">
              {data.action === 'searched' ? 'Executed search query in web browser' : 'Navigated active browser tab'}
            </p>
          </div>
        </div>
      </div>

      {/* Query & Target Details */}
      <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800 space-y-2.5">
        {data.query && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm text-indigo-400">search</span>
              Search Query:
            </span>
            <span className="px-2.5 py-1 rounded-md bg-indigo-500/20 border border-indigo-500/40 font-semibold text-indigo-200">
              "{data.query}"
            </span>
          </div>
        )}

        <div className="flex items-center justify-between text-xs gap-2 pt-1">
          <span className="text-slate-400 font-medium shrink-0 flex items-center gap-1.5">
            <span className="material-symbols-outlined text-sm text-cyan-400">link</span>
            Target URL:
          </span>
          <a
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-400 hover:text-cyan-300 font-mono text-[11px] truncate underline underline-offset-2 max-w-[280px]"
            title={data.url}
          >
            {data.url}
          </a>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-slate-400 flex items-center gap-1">
          <span className="material-symbols-outlined text-sm text-emerald-400">check_circle</span>
          Browser tab loaded successfully
        </span>

        <button
          onClick={handleOpenBrowser}
          className="px-3.5 py-2 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 cursor-pointer transition-all active:scale-95"
        >
          <span className="material-symbols-outlined text-sm">open_in_new</span>
          Open in Browser
        </button>
      </div>
    </div>
  );
};

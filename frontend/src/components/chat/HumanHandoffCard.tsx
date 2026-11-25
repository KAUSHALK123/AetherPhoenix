import React, { useState } from 'react';

export interface HumanHandoffCardProps {
  reason: string;
  url?: string;
  screenshot?: string;
  workflowId?: string;
  taskId?: string;
  onResume?: () => void;
}

export const HumanHandoffCard: React.FC<HumanHandoffCardProps> = ({
  reason,
  url,
  screenshot,
  workflowId,
  taskId,
  onResume,
}) => {
  const [isResuming, setIsResuming] = useState(false);
  const [resumed, setResumed] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleResume = async () => {
    setIsResuming(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/v1/browser/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: workflowId,
          task_id: taskId,
        }),
      });
      if (res.ok) {
        setResumed(true);
        if (onResume) {
          onResume();
        }
      } else {
        const data = await res.json().catch(() => ({}));
        setErrorMsg(data.message || 'Failed to send resume signal.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Network error while attempting to resume.');
    } finally {
      setIsResuming(false);
    }
  };

  return (
    <div className="w-full max-w-xl bg-amber-950/40 backdrop-blur-xl border border-amber-500/40 rounded-2xl p-5 shadow-2xl space-y-4 text-slate-100 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-lg">
            <span className="material-symbols-outlined text-2xl text-amber-400">person_alert</span>
          </div>
          <div>
            <h4 className="font-bold text-sm tracking-wide text-white flex items-center gap-2">
              Waiting for you: please sign in, then press Resume
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                HUMAN HANDOFF
              </span>
            </h4>
            <p className="text-xs text-amber-200/70">
              The browser window is open. Complete authentication or captcha, then click Resume to continue.
            </p>
          </div>
        </div>
      </div>

      {/* Barrier Details */}
      <div className="bg-slate-950/70 rounded-xl p-3.5 border border-amber-500/20 space-y-2">
        <div className="text-xs text-slate-300">
          <span className="font-semibold text-amber-300">Detection Reason: </span>
          {reason}
        </div>
        {url && (
          <div className="text-[11px] font-mono text-cyan-400 truncate">
            <span className="text-slate-400 font-sans">Target: </span>
            {url}
          </div>
        )}
      </div>

      {/* Screenshot Preview if present */}
      {screenshot && (
        <div className="rounded-xl overflow-hidden border border-slate-800 max-h-56 bg-black/40">
          <img
            src={`data:image/png;base64,${screenshot}`}
            alt="Human Handoff Screenshot"
            className="w-full object-cover object-top"
          />
        </div>
      )}

      {errorMsg && (
        <div className="text-xs text-rose-400 bg-rose-950/40 p-2.5 rounded-lg border border-rose-500/30">
          {errorMsg}
        </div>
      )}

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="material-symbols-outlined text-sm text-amber-400">hourglass_top</span>
          10-minute timeout active
        </span>

        <button
          onClick={handleResume}
          disabled={isResuming || resumed}
          className={`px-4 py-2 rounded-xl text-xs font-semibold shadow-lg flex items-center gap-2 cursor-pointer transition-all active:scale-95 ${
            resumed
              ? 'bg-emerald-600 text-white'
              : 'bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white shadow-amber-600/30'
          }`}
        >
          {isResuming ? (
            <>
              <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
              Checking barrier...
            </>
          ) : resumed ? (
            <>
              <span className="material-symbols-outlined text-sm">check_circle</span>
              Resumed!
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-sm">play_arrow</span>
              I've Signed In — Resume
            </>
          )}
        </button>
      </div>
    </div>
  );
};

import React from 'react';
import type { PermissionRequest } from '../../types/permission';

export interface PermissionPopcardProps {
  permission: PermissionRequest;
  onApprove: (requestId: string) => void;
  onReject: (requestId: string) => void;
  disabled?: boolean;
}

export const PermissionPopcard: React.FC<PermissionPopcardProps> = ({
  permission,
  onApprove,
  onReject,
  disabled = false,
}) => {
  const getRiskBadge = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return (
          <span className="px-2.5 py-1 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-400 text-[10px] font-bold tracking-wider uppercase font-mono flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">shield</span>
            {level} RISK
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2.5 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-400 text-[10px] font-bold tracking-wider uppercase font-mono flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">warning</span>
            MEDIUM RISK
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 text-[10px] font-bold tracking-wider uppercase font-mono flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">verified</span>
            LOW RISK
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-amber-500/40 rounded-2xl p-5 shadow-2xl shadow-black/60 space-y-4 max-w-xl w-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <span className="material-symbols-outlined text-xl">gpp_maybe</span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Permission Request
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Req ID: {permission.request_id}
            </p>
          </div>
        </div>
        {getRiskBadge(permission.risk_level)}
      </div>

      <div className="bg-slate-950/80 rounded-xl p-4 border border-slate-800 space-y-2">
        <div className="text-xs text-slate-300">
          <span className="text-slate-500 font-mono">Action Requested: </span>
          <code className="text-indigo-300 font-mono font-semibold bg-indigo-950/50 px-2 py-0.5 rounded border border-indigo-500/30">
            {permission.permission_type}
          </code>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed italic">
          "{permission.reason}"
        </p>
      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={() => onReject(permission.request_id)}
          disabled={disabled}
          className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-semibold transition-all cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1.5"
        >
          <span className="material-symbols-outlined text-sm">block</span>
          Reject
        </button>
        <button
          onClick={() => onApprove(permission.request_id)}
          disabled={disabled}
          className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold transition-all shadow-lg shadow-indigo-600/30 cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1.5 active:scale-95"
        >
          <span className="material-symbols-outlined text-sm">verified_user</span>
          Approve Permission
        </button>
      </div>
    </div>
  );
};

import React from 'react';
import { Shield, Sparkles, Activity, Bell } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { usePermissionStore } from '../store/permissionStore';
import { Badge } from '../components/common/Badge';

export const Topbar: React.FC = () => {
  const executionMode = useChatStore((state) => state.executionMode);
  const setExecutionMode = useChatStore((state) => state.setExecutionMode);
  const pendingCount = usePermissionStore((state) => state.pendingRequests.length);

  return (
    <header className="h-16 shrink-0 glass-panel border-b border-slate-800 px-6 flex items-center justify-between z-10 sticky top-0">
      {/* Active Pipeline Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-mono font-medium text-slate-300">
            System State:
          </span>
          <Badge variant="success">READY</Badge>
        </div>

        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-800 text-xs text-slate-400 font-mono">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Multi-Agent Orchestrator (Planner + Worker + Supervisor + Healing)</span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Execution Mode Selector */}
        <div className="flex items-center gap-2 text-xs">
          <Shield className="w-4 h-4 text-slate-400" />
          <select
            value={executionMode}
            onChange={(e) =>
              setExecutionMode(e.target.value as 'SAFE' | 'ASSISTED' | 'AUTONOMOUS')
            }
            className="bg-slate-900 border border-slate-700 text-sky-300 text-xs font-mono rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-sky-500 cursor-pointer"
          >
            <option value="SAFE">SAFE (Ask All)</option>
            <option value="ASSISTED">ASSISTED (Ask High Risk)</option>
            <option value="AUTONOMOUS">AUTONOMOUS (Self Direct)</option>
          </select>
        </div>

        {/* Pending Permissions Alert */}
        {pendingCount > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/60 border border-amber-500/40 px-3 py-1.5 rounded-lg animate-pulse">
            <Bell className="w-3.5 h-3.5" />
            <span>{pendingCount} Auth Required</span>
          </div>
        )}
      </div>
    </header>
  );
};

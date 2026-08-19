import React from 'react';
import { Brain, Database } from 'lucide-react';
import { Badge } from '../components/common/Badge';

export const MemoryPage: React.FC = () => {
  const contextItems = [
    {
      key: 'user_preferred_format',
      value: 'PowerPoint (.pptx) corporate theme with high contrast',
      scope: 'Global',
      last_updated: '10 mins ago',
    },
    {
      key: 'browser_session_auth_cache',
      value: 'Active token valid for *.example.com domain boundaries',
      scope: 'Session',
      last_updated: '25 mins ago',
    },
    {
      key: 'active_planner_goal',
      value: 'Market research extraction & multi-agent workflow synthesis',
      scope: 'Workflow',
      last_updated: '1 hour ago',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-sky-400" />
            Agent Context & Episodic Memory
          </h2>
          <p className="text-xs text-slate-400">
            Persistent episodic memory, active conversation context & workflow state retention
          </p>
        </div>

        <Badge variant="primary">MEMORY: ACTIVE</Badge>
      </div>

      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="text-xs font-mono uppercase text-slate-400 font-semibold flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400" />
          Active Episodic Memory Slots
        </div>

        <div className="space-y-3">
          {contextItems.map((item, idx) => (
            <div
              key={idx}
              className="glass-card rounded-xl p-4 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 font-mono text-xs"
            >
              <div>
                <span className="text-sky-400 font-bold">{item.key}</span>
                <p className="text-slate-300 font-sans text-xs mt-0.5">{item.value}</p>
              </div>

              <div className="flex items-center gap-3 shrink-0 text-slate-500">
                <Badge variant="neutral">{item.scope}</Badge>
                <span>{item.last_updated}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

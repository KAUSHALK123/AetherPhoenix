import React, { useState } from 'react';
import { Activity, Terminal, Clock, CheckCircle2, PlayCircle, Layers } from 'lucide-react';
import { Badge } from '../components/common/Badge';

export const RuntimePage: React.FC = () => {
  const [selectedTaskLog, setSelectedTaskLog] = useState<number>(0);

  const tasks = [
    {
      id: 't-101',
      name: 'Planner Agent Decomposing Goal',
      agent: 'Planner Agent',
      tool: 'goal_decomposer',
      status: 'COMPLETED',
      duration: '1.2s',
      risk: 'LOW',
      logs: [
        '[19:28:10] Initializing planner context...',
        '[19:28:10] Parsing user goal constraints and permissions...',
        '[19:28:11] Generating 4 sub-tasks DAG with topological ordering.',
        '[19:28:11] Plan verified and ready for execution.',
      ],
    },
    {
      id: 't-102',
      name: 'Launch Browser Session & Scrape Market Data',
      agent: 'Worker Agent',
      tool: 'browser_automation',
      status: 'COMPLETED',
      duration: '14.8s',
      risk: 'MEDIUM',
      logs: [
        '[19:28:12] Requesting BROWSER_ACCESS permission...',
        '[19:28:12] Permission pre-authorized by user in ASSISTED mode.',
        '[19:28:13] Launching headless Playwright Chromium instance.',
        '[19:28:15] Navigating to target domains and capturing DOM tree.',
        '[19:28:26] Data extraction complete. 28 items parsed.',
      ],
    },
    {
      id: 't-103',
      name: 'Build Presentation Deck & Charts',
      agent: 'Worker Agent',
      tool: 'ppt_generator',
      status: 'RUNNING',
      duration: '6.4s',
      risk: 'LOW',
      logs: [
        '[19:28:27] Initializing python-pptx engine with corporate theme.',
        '[19:28:28] Generating slide 1: Title & Executive Summary.',
        '[19:28:30] Generating slide 2: Market Analysis & Competitor Comparison.',
        '[19:28:32] Generating slide 3: Financial Projections & Next Steps...',
      ],
    },
    {
      id: 't-104',
      name: 'Supervisor Quality & Safety Validation',
      agent: 'Supervisor Agent',
      tool: 'output_validator',
      status: 'PENDING',
      duration: '—',
      risk: 'LOW',
      logs: ['Waiting for upstream task t-103 completion...'],
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            Runtime Execution Monitor
          </h2>
          <p className="text-xs text-slate-400">
            Real-time multi-agent execution kernel and live task stream
          </p>
        </div>

        <Badge variant="success" size="md">
          KERNEL: ACTIVE
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tasks List */}
        <div className="space-y-3 lg:col-span-2">
          <div className="text-xs font-mono uppercase text-slate-400 font-semibold flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            Live Execution Stream
          </div>

          <div className="space-y-3">
            {tasks.map((task, idx) => (
              <div
                key={task.id}
                onClick={() => setSelectedTaskLog(idx)}
                className={`glass-card rounded-xl p-4 border transition-all cursor-pointer ${
                  selectedTaskLog === idx
                    ? 'border-sky-500/50 bg-slate-900/90 shadow-lg shadow-sky-500/10'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {task.status === 'COMPLETED' ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : task.status === 'RUNNING' ? (
                      <PlayCircle className="w-5 h-5 text-sky-400 shrink-0 animate-pulse" />
                    ) : (
                      <Clock className="w-5 h-5 text-slate-500 shrink-0" />
                    )}

                    <div>
                      <h4 className="text-sm font-semibold text-slate-200">
                        {task.name}
                      </h4>
                      <div className="text-xs text-slate-400 font-mono flex items-center gap-3 mt-1">
                        <span className="text-orange-300">{task.agent}</span>
                        <span>• Tool: {task.tool}</span>
                        <span>• Duration: {task.duration}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        task.status === 'COMPLETED'
                          ? 'success'
                          : task.status === 'RUNNING'
                          ? 'planner'
                          : 'neutral'
                      }
                    >
                      {task.status}
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Streaming Task Logs */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col h-[500px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs font-mono">
            <span className="text-slate-300 flex items-center gap-1.5 font-bold">
              <Terminal className="w-4 h-4 text-sky-400" />
              Runtime Logs [{tasks[selectedTaskLog].id}]
            </span>
            <span className="text-slate-500">{tasks[selectedTaskLog].agent}</span>
          </div>

          <div className="flex-1 bg-black/50 rounded-xl p-3.5 mt-3 overflow-y-auto font-mono text-xs text-sky-300/90 space-y-1.5 border border-slate-900">
            {tasks[selectedTaskLog].logs.map((line, idx) => (
              <div key={idx} className="leading-relaxed">
                {line}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

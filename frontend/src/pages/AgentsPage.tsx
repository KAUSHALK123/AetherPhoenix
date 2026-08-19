import React from 'react';
import { Users, Bot, Zap, Activity, ShieldCheck, Cpu } from 'lucide-react';
import type { AgentInfo } from '../types/agent';
import { Badge } from '../components/common/Badge';

export const AgentsPage: React.FC = () => {
  const agents: AgentInfo[] = [
    {
      id: 'agent-planner',
      name: 'Planner Agent',
      role: 'Planner',
      status: 'ONLINE',
      version: '1.0.0',
      description:
        'Analyzes human intent, parses constraints, performs risk assessment, and structures topological task execution DAGs.',
      capabilities: [
        'Goal Extraction',
        'Task Decomposition',
        'Dependency Resolution',
        'Permission Risk Analysis',
        'Interactive Clarification',
      ],
      assigned_tasks_count: 142,
    },
    {
      id: 'agent-worker',
      name: 'Worker Agent',
      role: 'Worker',
      status: 'ONLINE',
      version: '1.0.0',
      description:
        'Executes granular tasks by dispatching sandboxed tool adapters for web browsing, desktop actions, and file generation.',
      capabilities: [
        'Playwright Headless Browser',
        'Desktop Mouse & Keyboard Emulation',
        'PowerPoint (.pptx) Deck Builder',
        'PDF Generation & Table Layout',
        'Web Scraping & DOM Automation',
      ],
      assigned_tasks_count: 489,
    },
    {
      id: 'agent-supervisor',
      name: 'Supervisor Agent',
      role: 'Supervisor',
      status: 'ONLINE',
      version: '1.0.0',
      description:
        'Monitors worker task outputs, validates schema compliance, checks timeout violations, and raises escalation triggers.',
      capabilities: [
        'Task Output Validation',
        'Timeout & Deadlock Detection',
        'Execution Sandboxing Enforcement',
        'Observability Event Telemetry',
      ],
      assigned_tasks_count: 512,
    },
    {
      id: 'agent-healing',
      name: 'Healing Agent',
      role: 'Healing',
      status: 'STANDBY',
      version: '1.0.0',
      description:
        'Evaluates runtime task failures, analyzes root cause exceptions, dynamically modifies task parameters, and initiates self-healing retries.',
      capabilities: [
        'Root Cause Analysis',
        'Dynamic Retry Engine',
        'Parameter Mutation',
        'Autonomous Recovery Planning',
      ],
      assigned_tasks_count: 18,
    },
  ];

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'Planner':
        return <Bot className="w-5 h-5 text-sky-400" />;
      case 'Worker':
        return <Zap className="w-5 h-5 text-orange-400" />;
      case 'Supervisor':
        return <Activity className="w-5 h-5 text-purple-400" />;
      case 'Healing':
        return <ShieldCheck className="w-5 h-5 text-rose-400" />;
      default:
        return <Cpu className="w-5 h-5 text-indigo-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-sky-400" />
            Agent Registry & Subsystem Architecture
          </h2>
          <p className="text-xs text-slate-400">
            Registered autonomous agents coordinating in the AetherPhoenix kernel
          </p>
        </div>

        <Badge variant="primary" size="md">
          4 REGISTERED AGENTS
        </Badge>
      </div>

      {/* Agents Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4 hover:border-slate-700 transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center">
                  {getRoleIcon(agent.role)}
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">{agent.name}</h3>
                  <span className="text-[11px] font-mono text-slate-500">v{agent.version}</span>
                </div>
              </div>

              <Badge variant={agent.status === 'ONLINE' ? 'success' : 'warning'}>
                {agent.status}
              </Badge>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {agent.description}
            </p>

            <div className="space-y-2 pt-2 border-t border-slate-800/80">
              <div className="text-[11px] font-mono uppercase text-slate-500 font-semibold">
                Core Capabilities
              </div>
              <div className="flex flex-wrap gap-1.5">
                {agent.capabilities.map((cap, idx) => (
                  <span
                    key={idx}
                    className="bg-slate-900/80 text-slate-300 text-[11px] font-mono px-2.5 py-1 rounded-md border border-slate-800"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs font-mono text-slate-500">
              <span>Lifetime Tasks Processed:</span>
              <span className="text-sky-400 font-bold">{agent.assigned_tasks_count}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Workflow,
  Bot,
  Zap,
  Activity,
  ShieldCheck,
  RotateCw,
} from 'lucide-react';
import { workflowService } from '../services/workflowService';
import type { WorkflowState } from '../types/workflow';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const WorkflowPage: React.FC = () => {
  const [, setWorkflows] = useState<WorkflowState[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowState | null>(null);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const data = await workflowService.getWorkflows();
      if (data && data.length > 0) {
        setWorkflows(data);
        setSelectedWorkflow(data[0]);
      } else {
        // Provide sample active workflow model if backend queue is idle
        const sample: WorkflowState = {
          workflow_id: 'wf-8f40082f-8ed4-4dc8-ac8c-5c3ce01911f3',
          goal: 'Automated Competitor Intelligence & Slide Deck Compilation',
          execution_mode: 'ASSISTED',
          status: 'RUNNING',
          progress_percent: 65,
          started_at: new Date(Date.now() - 45000).toISOString(),
          elapsed_seconds: 45,
          total_tasks: 4,
          completed_tasks: 2,
          failed_tasks: 0,
          current_task_name: 'Generate PowerPoint Presentation',
          tasks: [
            {
              task_id: 't-1',
              task_name: 'Parse Requirements & Strategy',
              agent: 'Planner',
              tool: 'goal_decomposer',
              status: 'COMPLETED',
              duration_ms: 1200,
              logs: ['Goal parsed with 0.88 confidence', 'Tasks generated'],
            },
            {
              task_id: 't-2',
              task_name: 'Extract Competitor Pricing & Data',
              agent: 'Worker',
              tool: 'browser_automation',
              status: 'COMPLETED',
              duration_ms: 18400,
              logs: ['Playwright initialized', 'Scraped 14 data points'],
            },
            {
              task_id: 't-3',
              task_name: 'Generate PowerPoint Presentation',
              agent: 'Worker',
              tool: 'ppt_generator',
              status: 'RUNNING',
              duration_ms: 5400,
              logs: ['Building slides 1 through 5', 'Formatting charts'],
            },
            {
              task_id: 't-4',
              task_name: 'Validate Output & Security Audit',
              agent: 'Supervisor',
              tool: 'output_validator',
              status: 'PENDING',
              logs: ['Queued for supervisor verification'],
            },
          ],
        };
        setWorkflows([sample]);
        setSelectedWorkflow(sample);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Workflow className="w-5 h-5 text-sky-400" />
            Workflow Pipeline Visualizer
          </h2>
          <p className="text-xs text-slate-400">
            End-to-end execution flow: Planner → Worker → Supervisor → Healing
          </p>
        </div>

        <Button variant="secondary" size="sm" onClick={fetchWorkflows} isLoading={loading}>
          <RotateCw className="w-3.5 h-3.5 mr-1" />
          Refresh Workflows
        </Button>
      </div>

      {/* Multi-Agent Sequential DAG Pipeline Visualizer */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
          Agent Coordination Pipeline
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
          {/* Planner Node */}
          <div className="glass-card rounded-xl p-4 border-sky-500/40 relative">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sky-400 font-bold text-xs">
                <Bot className="w-4 h-4" />
                Planner Agent
              </div>
              <Badge variant="success">READY</Badge>
            </div>
            <div className="text-xs text-slate-400">Decomposes goals into tasks & requirements</div>
          </div>

          {/* Worker Node */}
          <div className="glass-card rounded-xl p-4 border-orange-500/40 relative">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-orange-400 font-bold text-xs">
                <Zap className="w-4 h-4" />
                Worker Agent
              </div>
              <Badge variant="worker">ACTIVE</Badge>
            </div>
            <div className="text-xs text-slate-400">Executes browser, desktop, PPT & PDF tools</div>
          </div>

          {/* Supervisor Node */}
          <div className="glass-card rounded-xl p-4 border-purple-500/40 relative">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-purple-400 font-bold text-xs">
                <Activity className="w-4 h-4" />
                Supervisor Agent
              </div>
              <Badge variant="supervisor">STANDBY</Badge>
            </div>
            <div className="text-xs text-slate-400">Monitors timeouts, errors & output schemas</div>
          </div>

          {/* Healing Node */}
          <div className="glass-card rounded-xl p-4 border-rose-500/40 relative">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-rose-400 font-bold text-xs">
                <ShieldCheck className="w-4 h-4" />
                Healing Agent
              </div>
              <Badge variant="healing">READY</Badge>
            </div>
            <div className="text-xs text-slate-400">Autonomous retry strategies & error mitigation</div>
          </div>
        </div>
      </div>

      {/* Selected Workflow Details */}
      {selectedWorkflow && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Workflow Details & Progress */}
          <div className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase">
                  Workflow ID: {selectedWorkflow.workflow_id}
                </span>
                <h3 className="text-base font-bold text-slate-100 mt-0.5">
                  {selectedWorkflow.goal}
                </h3>
              </div>
              <Badge variant="primary">{selectedWorkflow.status}</Badge>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>Execution Progress</span>
                <span className="text-sky-400 font-bold">{selectedWorkflow.progress_percent}%</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                <div
                  className="bg-gradient-to-r from-sky-500 to-indigo-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${selectedWorkflow.progress_percent}%` }}
                />
              </div>
            </div>

            {/* Task Execution Tree */}
            <div className="space-y-3 pt-2">
              <div className="text-xs font-mono uppercase text-slate-400">Task Execution Nodes</div>
              <div className="space-y-2">
                {selectedWorkflow.tasks.map((task, idx) => (
                  <div
                    key={task.task_id || idx}
                    className="glass-card rounded-xl p-4 border border-slate-800 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-md bg-slate-900 border border-slate-700 text-slate-400 text-xs font-mono flex items-center justify-center">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-slate-200">
                          {task.task_name}
                        </div>
                        <div className="text-xs text-slate-500 font-mono flex items-center gap-2">
                          <span>Agent: {task.agent}</span>
                          {task.tool && <span>• Tool: {task.tool}</span>}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {task.duration_ms && (
                        <span className="text-xs font-mono text-slate-400">
                          {(task.duration_ms / 1000).toFixed(1)}s
                        </span>
                      )}
                      <Badge
                        variant={
                          task.status === 'COMPLETED'
                            ? 'success'
                            : task.status === 'RUNNING'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {task.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Workflow Stats Sidebar */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <h4 className="text-xs font-mono uppercase text-slate-400 font-semibold">
              Execution Statistics
            </h4>

            <div className="space-y-3 text-xs font-mono">
              <div className="flex justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500">Total Tasks:</span>
                <span className="text-slate-200 font-bold">{selectedWorkflow.total_tasks}</span>
              </div>
              <div className="flex justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500">Completed Tasks:</span>
                <span className="text-emerald-400 font-bold">{selectedWorkflow.completed_tasks}</span>
              </div>
              <div className="flex justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500">Failed Tasks:</span>
                <span className="text-slate-200 font-bold">{selectedWorkflow.failed_tasks}</span>
              </div>
              <div className="flex justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500">Execution Mode:</span>
                <span className="text-sky-300 font-bold">{selectedWorkflow.execution_mode}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

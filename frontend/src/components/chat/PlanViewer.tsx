import React, { useState } from 'react';
import {
  CheckCircle2,
  Code2,
  Clock,
  ShieldAlert,
  Bot,
  Wrench,
  ArrowRight,
  Edit3,
  Play,
  XCircle,
  Layers,
} from 'lucide-react';
import type { PlannerPlan, PlannerTask } from '../../types/planner';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';

export interface PlanViewerProps {
  plan: PlannerPlan;
  rawJsonString?: string;
  onApprove?: () => void;
  onModifyTask?: (taskId: string, instruction: string) => void;
  onCancel?: () => void;
}

export const PlanViewer: React.FC<PlanViewerProps> = ({
  plan,
  rawJsonString,
  onApprove,
  onModifyTask,
  onCancel,
}) => {
  const [showJson, setShowJson] = useState(false);
  const [modifyingTaskId, setModifyingTaskId] = useState<string | null>(null);
  const [modificationPrompt, setModificationPrompt] = useState('');

  const tasks: PlannerTask[] = plan.tasks || [];

  const handleModifySubmit = (taskId: string) => {
    if (!modificationPrompt.trim()) return;
    if (onModifyTask) {
      onModifyTask(taskId, modificationPrompt.trim());
    }
    setModifyingTaskId(null);
    setModificationPrompt('');
  };

  const getRiskVariant = (risk?: string) => {
    switch (risk?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return 'danger';
      case 'MEDIUM':
        return 'warning';
      case 'LOW':
        return 'success';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="glass-panel border-sky-500/30 rounded-2xl p-6 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sky-400 font-mono text-xs uppercase tracking-widest font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Generated Execution Plan
            </span>
            {plan.metadata?.execution_mode && (
              <Badge variant="primary">{plan.metadata.execution_mode} MODE</Badge>
            )}
          </div>
          <h2 className="text-xl font-bold text-slate-100">
            {plan.workflow_spec || 'Autonomous Workflow Plan'}
          </h2>
        </div>

        <div className="flex items-center gap-3">
          {plan.estimated_time_seconds && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800">
              <Clock className="w-3.5 h-3.5 text-sky-400" />
              <span>Est: ~{plan.estimated_time_seconds}s</span>
            </div>
          )}
          <button
            onClick={() => setShowJson(!showJson)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>{showJson ? 'Visual View' : 'Raw JSON'}</span>
          </button>
        </div>
      </div>

      {/* Raw JSON View */}
      {showJson ? (
        <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>JSON Contract</span>
            <span>PlannerOutput</span>
          </div>
          <pre className="text-xs font-mono text-sky-300 p-3 bg-black/40 rounded-lg overflow-x-auto max-h-[400px]">
            {rawJsonString || JSON.stringify(plan, null, 2)}
          </pre>
        </div>
      ) : (
        /* Visual Task Cards View */
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 uppercase tracking-wider font-mono">
            <span className="flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-sky-400" />
              Task Execution Pipeline ({tasks.length} Steps)
            </span>
          </div>

          <div className="space-y-3">
            {tasks.map((task, index) => {
              const isModifying = modifyingTaskId === task.task_id;

              return (
                <div
                  key={task.task_id || index}
                  className="relative group bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition-all duration-200"
                >
                  {/* Step connector indicator */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="w-7 h-7 rounded-lg bg-sky-950/80 border border-sky-600/40 text-sky-400 font-mono text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {index + 1}
                      </div>

                      <div className="space-y-1.5 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-sm font-semibold text-slate-100">
                            {task.task_name}
                          </h4>
                          {task.risk_level && (
                            <Badge variant={getRiskVariant(task.risk_level)}>
                              {task.risk_level} RISK
                            </Badge>
                          )}
                          {task.priority && (
                            <Badge variant="neutral">{task.priority}</Badge>
                          )}
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed">
                          {task.description}
                        </p>

                        {/* Metadata badges */}
                        <div className="flex flex-wrap items-center gap-3 pt-2 text-xs text-slate-400 font-mono">
                          <div className="flex items-center gap-1 text-slate-300">
                            <Bot className="w-3.5 h-3.5 text-orange-400" />
                            <span>{task.assigned_agent || 'Worker Agent'}</span>
                          </div>

                          {task.required_tool && (
                            <div className="flex items-center gap-1 text-slate-300">
                              <Wrench className="w-3.5 h-3.5 text-sky-400" />
                              <span>{task.required_tool}</span>
                            </div>
                          )}

                          {task.estimated_duration_seconds && (
                            <div className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5 text-slate-500" />
                              <span>~{task.estimated_duration_seconds}s</span>
                            </div>
                          )}
                        </div>

                        {/* Expected Output */}
                        {task.expected_output && (
                          <div className="text-xs text-slate-400 bg-slate-950/50 rounded-md p-2 border border-slate-800/80 mt-2 font-mono">
                            <span className="text-slate-500">Output: </span>
                            <span className="text-slate-300">{task.expected_output}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Task Actions */}
                    <div className="shrink-0">
                      <button
                        onClick={() =>
                          setModifyingTaskId(isModifying ? null : task.task_id)
                        }
                        className="text-xs text-slate-400 hover:text-sky-300 p-1.5 rounded-lg hover:bg-slate-800 transition-colors flex items-center gap-1"
                        title="Modify Task"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Modify</span>
                      </button>
                    </div>
                  </div>

                  {/* Inline Task Modification Form */}
                  {isModifying && (
                    <div className="mt-4 pt-4 border-t border-slate-800/80 bg-slate-950/40 p-3 rounded-lg">
                      <div className="text-xs font-semibold text-sky-400 mb-2 flex items-center gap-1.5">
                        <Edit3 className="w-3.5 h-3.5" />
                        Modify Step {index + 1}: {task.task_name}
                      </div>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={modificationPrompt}
                          onChange={(e) => setModificationPrompt(e.target.value)}
                          placeholder="e.g. Include detailed table of contents and PDF download"
                          className="glass-input text-xs flex-1 px-3 py-2 rounded-lg"
                        />
                        <Button
                          size="sm"
                          variant="planner"
                          onClick={() => handleModifySubmit(task.task_id)}
                          disabled={!modificationPrompt.trim()}
                        >
                          Update
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setModifyingTaskId(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Arrow to next step */}
                  {index < tasks.length - 1 && (
                    <div className="flex justify-center -mb-5 mt-2 text-slate-700">
                      <ArrowRight className="w-4 h-4 rotate-90" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Permissions and Risks Footer */}
      {((plan.required_permissions && plan.required_permissions.length > 0) ||
        (plan.risks && plan.risks.length > 0)) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-slate-800 text-xs">
          {plan.required_permissions && plan.required_permissions.length > 0 && (
            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 space-y-1.5">
              <div className="font-semibold text-slate-300 flex items-center gap-1">
                <Wrench className="w-3.5 h-3.5 text-sky-400" />
                Required Permissions
              </div>
              <div className="flex flex-wrap gap-1.5">
                {plan.required_permissions.map((perm, idx) => (
                  <span
                    key={idx}
                    className="bg-slate-800 text-sky-300 font-mono text-[11px] px-2 py-0.5 rounded border border-slate-700"
                  >
                    {perm}
                  </span>
                ))}
              </div>
            </div>
          )}

          {plan.risks && plan.risks.length > 0 && (
            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 space-y-1.5">
              <div className="font-semibold text-amber-300 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                Identified Risks
              </div>
              <ul className="text-slate-400 space-y-1 list-disc list-inside">
                {plan.risks.map((risk, idx) => (
                  <li key={idx} className="truncate">
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Plan Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-800">
        <div className="text-xs text-slate-400 font-mono">
          Confidence Score: <span className="text-emerald-400 font-semibold">{plan.confidence_score ? `${Math.round(plan.confidence_score * 100)}%` : '92%'}</span>
        </div>

        <div className="flex items-center gap-3">
          {onCancel && (
            <Button variant="ghost" size="sm" onClick={onCancel}>
              <XCircle className="w-4 h-4 mr-1" />
              Discard Plan
            </Button>
          )}
          {onApprove && (
            <Button variant="success" size="md" onClick={onApprove}>
              <Play className="w-4 h-4 mr-1 fill-current" />
              Approve & Execute Plan
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import type { PlannerPlan } from '../../types/planner';

export interface PlanPopcardProps {
  plan: PlannerPlan;
  onApprove: (plan: PlannerPlan) => void;
  onEdit: (instruction: string) => void;
  onDiscard?: () => void;
}

export const PlanPopcard: React.FC<PlanPopcardProps> = ({
  plan,
  onApprove,
  onEdit,
  onDiscard,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editPrompt, setEditPrompt] = useState('');

  const tasks = plan.tasks || [];
  const confidence = plan.confidence_score
    ? `${Math.round(plan.confidence_score * 100)}%`
    : '95%';
  const duration = plan.estimated_time_seconds
    ? `${plan.estimated_time_seconds}s`
    : '10s';

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editPrompt.trim()) return;
    onEdit(editPrompt.trim());
    setIsEditing(false);
    setEditPrompt('');
  };

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-indigo-500/40 rounded-2xl p-5 shadow-2xl shadow-black/60 space-y-4 max-w-xl w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <span className="material-symbols-outlined text-xl">account_tree</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold font-mono uppercase px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Plan Generated
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                ~{duration} • {tasks.length} Steps
              </span>
            </div>
            <h3 className="text-sm font-bold text-white truncate max-w-sm mt-0.5">
              {plan.workflow_spec || 'Autonomous Workflow Plan'}
            </h3>
          </div>
        </div>
        <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-500/30">
          {confidence}
        </span>
      </div>

      {/* Task DAG List */}
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {tasks.map((task, idx) => (
          <div
            key={task.task_id || idx}
            className="flex items-start gap-3 bg-slate-950/70 p-3 rounded-xl border border-slate-800/80"
          >
            <div className="w-5 h-5 rounded-md bg-indigo-950 border border-indigo-500/40 text-indigo-400 text-[10px] font-mono font-bold flex items-center justify-center shrink-0 mt-0.5">
              {idx + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-xs font-bold text-slate-200 truncate">
                  {task.task_name}
                </h4>
                {task.risk_level && (
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    {task.risk_level}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2 leading-relaxed">
                {task.description}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Permissions / Risks notification */}
      {plan.required_permissions && plan.required_permissions.length > 0 && (
        <div className="bg-amber-950/30 border border-amber-500/30 rounded-xl p-3 flex items-center gap-2.5 text-xs text-amber-300">
          <span className="material-symbols-outlined text-base shrink-0 text-amber-400">shield</span>
          <span>Requires: <strong>{plan.required_permissions.join(', ')}</strong></span>
        </div>
      )}

      {/* Edit Form or Action Buttons */}
      {isEditing ? (
        <form onSubmit={handleEditSubmit} className="space-y-2 pt-1">
          <div className="text-xs font-semibold text-indigo-300">
            What would you like to change in this plan?
          </div>
          <input
            type="text"
            value={editPrompt}
            onChange={(e) => setEditPrompt(e.target.value)}
            placeholder="e.g. Change slide 3 and add battery comparison"
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            autoFocus
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!editPrompt.trim()}
              className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-40"
            >
              Regenerate Plan
            </button>
          </div>
        </form>
      ) : (
        <div className="flex items-center gap-2 pt-1">
          {onDiscard && (
            <button
              onClick={onDiscard}
              className="py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 text-xs font-semibold transition-all cursor-pointer flex items-center justify-center"
              title="Discard Plan"
            >
              <span className="material-symbols-outlined text-base">delete</span>
            </button>
          )}
          <button
            onClick={() => setIsEditing(true)}
            className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5"
          >
            <span className="material-symbols-outlined text-sm">edit</span>
            Edit Plan
          </button>
          <button
            onClick={() => onApprove(plan)}
            className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold transition-all shadow-lg shadow-indigo-600/30 cursor-pointer flex items-center justify-center gap-1.5 active:scale-95"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
            Approve & Execute
          </button>
        </div>
      )}
    </div>
  );
};

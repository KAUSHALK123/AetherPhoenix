import React from 'react';
import type { WorkflowState } from '../../types/workflow';

export interface WorkflowStatusPopcardProps {
  workflow: Partial<WorkflowState>;
}

export const WorkflowStatusPopcard: React.FC<WorkflowStatusPopcardProps> = ({ workflow }) => {
  const tasks = workflow.tasks || [];
  const percent = workflow.progress_percent || 0;
  const isDone = workflow.status === 'COMPLETED';

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-4 max-w-xl w-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <span className={`material-symbols-outlined text-lg ${!isDone ? 'animate-spin' : ''}`}>
              {isDone ? 'check_circle' : 'autorenew'}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              {isDone ? 'Workflow Completed' : 'Executing Workflow'}
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              {workflow.current_task_name || 'Processing pipeline steps...'}
            </p>
          </div>
        </div>
        <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/60 px-2.5 py-1 rounded-full border border-indigo-500/30">
          {percent}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
        <div
          className="bg-gradient-to-r from-indigo-500 to-violet-400 h-full transition-all duration-500 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Task Steps */}
      <div className="space-y-2 pt-1">
        {tasks.map((task, idx) => {
          const isTaskDone = task.status === 'COMPLETED';
          const isTaskRunning = task.status === 'RUNNING';

          return (
            <div
              key={task.task_id || idx}
              className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-all ${
                isTaskDone
                  ? 'bg-slate-950/40 border-emerald-500/30 text-emerald-300'
                  : isTaskRunning
                  ? 'bg-indigo-950/40 border-indigo-500/50 text-indigo-200 shadow-sm'
                  : 'bg-slate-950/20 border-slate-800/60 text-slate-500'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-sm shrink-0">
                  {isTaskDone ? 'check_circle' : isTaskRunning ? 'pending' : 'radio_button_unchecked'}
                </span>
                <span className="font-medium truncate max-w-[280px]">
                  {task.task_name}
                </span>
              </div>
              <span className="text-[10px] font-mono uppercase shrink-0">
                {task.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

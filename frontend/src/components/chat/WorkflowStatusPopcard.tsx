import React from 'react';
import type { WorkflowState } from '../../types/workflow';

export interface WorkflowStatusPopcardProps {
  workflow: Partial<WorkflowState>;
}

export const WorkflowStatusPopcard: React.FC<WorkflowStatusPopcardProps> = ({ workflow }) => {
  const tasksRaw = workflow.tasks;
  const taskList = tasksRaw
    ? Array.isArray(tasksRaw)
      ? tasksRaw
      : Object.values(tasksRaw)
    : [];

  const percent = Math.round(
    (workflow as Record<string, unknown>).progress_percentage as number ??
    (workflow as Record<string, unknown>).progress_percent as number ??
    0
  );

  const status = workflow.status ?? 'RUNNING';
  const isDone = status === 'COMPLETED';
  const isFailed = status === 'FAILED' || status === 'BLOCKED';

  const runningTaskName =
    workflow.current_task_name ||
    taskList.find(
      (t) =>
        t.status === 'RUNNING' ||
        ((workflow.running_tasks as string[] | undefined) ?? []).includes(t.task_id)
    )?.task_name ||
    'Processing pipeline steps…';

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-4 max-w-xl w-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-xl flex items-center justify-center border ${
              isDone
                ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                : isFailed
                ? 'bg-red-500/20 border-red-500/30 text-red-400'
                : 'bg-indigo-500/20 border-indigo-500/30 text-indigo-400'
            }`}
          >
            <span
              className={`material-symbols-outlined text-lg ${
                !isDone && !isFailed ? 'animate-spin' : ''
              }`}
            >
              {isDone ? 'check_circle' : isFailed ? 'error' : 'autorenew'}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              {isDone ? 'Workflow Completed' : isFailed ? 'Workflow Failed' : 'Executing Workflow'}
            </h3>
            <p className="text-[11px] text-slate-400 font-mono truncate max-w-[280px]">
              {isDone ? 'All tasks finished' : isFailed ? 'Execution halted' : runningTaskName}
            </p>
          </div>
        </div>
        <span
          className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full border ${
            isDone
              ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30'
              : isFailed
              ? 'text-red-400 bg-red-950/60 border-red-500/30'
              : 'text-indigo-400 bg-indigo-950/60 border-indigo-500/30'
          }`}
        >
          {percent}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
        <div
          className={`h-full transition-all duration-500 ease-out ${
            isDone
              ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
              : isFailed
              ? 'bg-gradient-to-r from-red-500 to-rose-400'
              : 'bg-gradient-to-r from-indigo-500 to-violet-400'
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Task Steps */}
      {taskList.length > 0 && (
        <div className="space-y-2 pt-1 max-h-64 overflow-y-auto">
          {taskList.map((task, idx) => {
            const taskStatus = String(task.status || 'PENDING').toUpperCase().replace(/.*\./, '');
            const isTaskDone = taskStatus === 'COMPLETED';
            const isTaskRunning = taskStatus === 'RUNNING';
            const isTaskFailed = taskStatus === 'FAILED' || taskStatus === 'BLOCKED';

            return (
              <div
                key={task.task_id || idx}
                className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-all ${
                  isTaskDone
                    ? 'bg-slate-950/40 border-emerald-500/30 text-emerald-300'
                    : isTaskRunning
                    ? 'bg-indigo-950/40 border-indigo-500/50 text-indigo-200 shadow-sm'
                    : isTaskFailed
                    ? 'bg-red-950/40 border-red-500/30 text-red-300'
                    : 'bg-slate-950/20 border-slate-800/60 text-slate-500'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="material-symbols-outlined text-sm shrink-0">
                    {isTaskDone
                      ? 'check_circle'
                      : isTaskRunning
                      ? 'pending'
                      : isTaskFailed
                      ? 'error'
                      : 'radio_button_unchecked'}
                  </span>
                  <span className="font-medium truncate max-w-[280px]">
                    {task.task_name}
                  </span>
                </div>
                <span className="text-[10px] font-mono uppercase shrink-0">
                  {taskStatus}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Synthesized Answer & Collapsible Raw Output */}
      {isDone && (workflow.answer || workflow.final_response?.answer) && (
        <div className="pt-2 border-t border-slate-800/80 space-y-3">
          <div className="bg-slate-950/70 border border-indigo-500/30 p-3.5 rounded-xl text-slate-100 text-xs sm:text-sm whitespace-pre-wrap leading-relaxed shadow-inner">
            <div className="flex items-center gap-1.5 text-indigo-400 font-semibold text-[11px] mb-1.5 uppercase tracking-wider font-mono">
              <span className="material-symbols-outlined text-sm">smart_toy</span>
              <span>Result Summary</span>
            </div>
            {workflow.answer || workflow.final_response?.answer}
          </div>

          {(workflow.raw_output || workflow.final_response?.raw_output) &&
            Object.keys(workflow.raw_output || workflow.final_response?.raw_output || {}).length > 0 && (
              <details className="group border border-slate-800 rounded-xl bg-slate-950/40 overflow-hidden text-xs">
                <summary className="flex items-center justify-between p-2.5 px-3 cursor-pointer text-slate-400 hover:text-slate-200 select-none font-mono text-[11px] transition-colors">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm text-slate-500">terminal</span>
                    <span>Raw Tool Output</span>
                  </div>
                  <span className="material-symbols-outlined text-sm transition-transform group-open:rotate-180">
                    expand_more
                  </span>
                </summary>
                <div className="p-3 border-t border-slate-800/80 bg-slate-950/80 max-h-60 overflow-y-auto">
                  <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] text-slate-300">
                    {JSON.stringify(
                      workflow.raw_output || workflow.final_response?.raw_output,
                      null,
                      2
                    )}
                  </pre>
                </div>
              </details>
            )}
        </div>
      )}
    </div>
  );
};

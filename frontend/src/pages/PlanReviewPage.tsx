import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChatStore } from '../store/chatStore';

export const PlanReviewPage: React.FC = () => {
  const navigate = useNavigate();
  const activePlan = useChatStore((state) => state.activePlan);
  const [modifyingStep, setModifyingStep] = useState<number | null>(null);
  const [modifiedPrompt, setModifiedPrompt] = useState('');

  // Fallback sample plan if no active plan in store
  const defaultSteps = [
    { num: 1, title: 'Scan Downloads Directory', desc: 'Identify all files and categorize them by extension.' },
    { num: 2, title: 'Analyze Metadata', desc: 'Read file names and sizes to confirm categorization accuracy.' },
    { num: 3, title: 'Create Subfolders', desc: 'Generate system directories: /Images, /Documents, /Executables.' },
    { num: 4, title: 'Execute Migration', desc: 'Safely move files to their respective target destinations.' },
  ];

  const steps = activePlan?.tasks?.length
    ? activePlan.tasks.map((t, idx) => ({
        num: idx + 1,
        title: t.task_name || `Task ${idx + 1}`,
        desc: t.description || 'Automated agent execution task step.',
      }))
    : defaultSteps;

  const title = activePlan?.workflow_spec || 'Organize Downloads Folder';
  const confidence = activePlan?.confidence_score
    ? `${Math.round(activePlan.confidence_score * 100)}%`
    : '99%';
  const duration = activePlan?.estimated_time_seconds
    ? `${activePlan.estimated_time_seconds} sec`
    : '12 sec';
  const permissions = activePlan?.required_permissions?.length
    ? activePlan.required_permissions
    : ['File System Access'];

  return (
    <div className="flex flex-col flex-1 min-h-[calc(100vh-4rem)]">
      <main className="p-6 md:p-10 max-w-5xl mx-auto w-full pb-32 flex-1">
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-accent-electric text-sm">account_tree</span>
            <span className="text-[10px] text-accent-electric uppercase font-bold tracking-widest">
              Plan Review
            </span>
          </div>
          <h2 className="text-3xl font-bold mb-3 text-white">{title}</h2>
          <p className="text-on-surface-muted max-w-2xl text-base md:text-lg">
            AetherPhoenix has generated a workflow based on your preferences. Review the steps below before proceeding.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Workflow DAG Column */}
          <div className="lg:col-span-8 glass-panel rounded-xl p-6 md:p-8">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xl font-bold text-primary">Execution Workflow</h3>
              <span className="px-3 py-1 bg-surface-variant rounded-full text-xs border border-outline-variant text-white">
                {steps.length} Steps
              </span>
            </div>

            <div className="relative space-y-8">
              <div className="absolute left-[19px] top-6 bottom-6 w-[2px] bg-gradient-to-b from-primary via-surface-variant to-surface-variant opacity-50" />

              {steps.map((step, idx) => (
                <div key={idx} className="flex gap-6 relative z-10 group">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border-2 transition-all ${
                      idx === 0
                        ? 'bg-surface-container-high border-primary shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                        : 'bg-surface-container border-outline-variant'
                    }`}
                  >
                    <span className={`text-sm font-bold ${idx === 0 ? 'text-primary' : 'text-on-surface-muted'}`}>
                      {step.num}
                    </span>
                  </div>

                  <div className="flex-1 bg-surface-container-low p-4 rounded-lg border border-outline-variant/60 hover:border-primary/50 transition-all">
                    <div className="flex justify-between items-start mb-1">
                      <h4 className="font-bold text-white text-base">{step.title}</h4>
                      <button
                        onClick={() => {
                          setModifyingStep(step.num);
                          setModifiedPrompt(step.desc);
                        }}
                        className="text-xs text-on-surface-muted hover:text-accent-electric transition-colors cursor-pointer"
                      >
                        Modify
                      </button>
                    </div>
                    {modifyingStep === step.num ? (
                      <div className="mt-2 flex flex-col gap-2">
                        <textarea
                          className="w-full p-2 bg-surface-deep rounded border border-primary text-xs text-white focus:outline-none"
                          value={modifiedPrompt}
                          onChange={(e) => setModifiedPrompt(e.target.value)}
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setModifyingStep(null)}
                            className="px-3 py-1 rounded bg-surface-container text-xs text-on-surface-muted cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => {
                              step.desc = modifiedPrompt;
                              setModifyingStep(null);
                            }}
                            className="px-3 py-1 rounded bg-primary text-white text-xs font-bold cursor-pointer"
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-on-surface-muted">{step.desc}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analysis Column */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <div className="glass-panel p-6 rounded-xl border border-outline-variant">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-2 text-white">
                <span className="material-symbols-outlined text-primary">monitoring</span>
                Analysis
              </h3>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/30">
                  <p className="text-[10px] uppercase font-bold text-on-surface-muted">Est. Time</p>
                  <p className="text-2xl font-bold text-white">{duration}</p>
                </div>
                <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/30">
                  <p className="text-[10px] uppercase font-bold text-on-surface-muted">Confidence</p>
                  <p className="text-2xl font-bold text-accent-electric">{confidence}</p>
                </div>
              </div>
              <div className="space-y-4">
                <p className="text-[10px] uppercase font-bold text-on-surface-muted tracking-widest">
                  Permissions Needed
                </p>
                {permissions.map((perm, pIdx) => (
                  <div
                    key={pIdx}
                    className="flex items-center gap-3 p-3 bg-surface-container-highest/40 rounded-lg border border-outline-variant/30"
                  >
                    <span className="material-symbols-outlined text-primary">folder_open</span>
                    <span className="text-xs font-semibold text-white">{perm}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 md:left-64 right-0 bg-surface-bright/90 backdrop-blur-md border-t border-outline-variant p-4 z-50">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
          <span className="text-sm text-on-surface-muted hidden sm:block">
            Review plan details before execution.
          </span>
          <div className="flex gap-3 w-full sm:w-auto">
            <button
              onClick={() => navigate('/chat')}
              className="flex-1 sm:flex-none px-6 py-2.5 rounded-lg border border-error/50 text-error hover:bg-error/10 text-sm font-bold transition-all cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={() => navigate('/execution')}
              className="flex-1 sm:flex-none px-8 py-2.5 rounded-lg bg-primary text-white hover:bg-accent-electric shadow-[0_0_15px_rgba(168,85,247,0.4)] text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-lg">play_arrow</span>
              Approve & Execute
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

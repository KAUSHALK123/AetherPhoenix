import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { ClarificationPopcard } from '../components/chat/ClarificationPopcard';
import { PlanPopcard } from '../components/chat/PlanPopcard';
import { PermissionPopcard } from '../components/chat/PermissionPopcard';
import { ArtifactPopcard } from '../components/chat/ArtifactPopcard';
import { WorkflowStatusPopcard } from '../components/chat/WorkflowStatusPopcard';

import { TerminalPopcard } from '../components/chat/TerminalPopcard';

export const ChatPage: React.FC = () => {
  const messages = useChatStore((state) => state.messages);
  const loading = useChatStore((state) => state.loading);
  const sendMessage = useChatStore((state) => state.sendMessage);
  const submitClarification = useChatStore((state) => state.submitClarification);
  const executePlan = useChatStore((state) => state.executePlan);
  const approvePermission = useChatStore((state) => state.approvePermissionInChat);
  const rejectPermission = useChatStore((state) => state.rejectPermissionInChat);

  const [inputVal, setInputVal] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);

  // Active terminal or tool output payload for right side inspector panel
  const latestTerminalData = [...messages].reverse().find((m) => m.terminalOutputData)?.terminalOutputData;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputVal.trim();
    if (!text || loading) return;

    setInputVal('');
    setSelectedFile(null);
    await sendMessage(text);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  // Real backend capabilities discovered from CapabilityDiscoveryEngine and ToolRegistry
  const realCapabilities = [
    { label: 'Create PowerPoint Presentation', query: 'Create a PowerPoint presentation about electric vehicles with 5 slides' },
    { label: 'Generate PDF Research Report', query: 'Generate a comprehensive PDF market research report on AI automation' },
    { label: 'Search the Web & Scrape', query: 'Search the web for top renewable energy innovations in 2026' },
    { label: 'Local File Organizer', query: 'Organize files in the downloads directory by file type and date' },
    { label: 'Run PowerShell Command', query: 'List active system processes and resource usage via PowerShell' },
    { label: 'Browser Automation Task', query: 'Open browser and navigate to documentation page for verification' },
  ];

  return (
    <div
      className="flex flex-col h-screen w-full text-slate-100 overflow-hidden relative select-none bg-cover bg-center"
      style={{
        backgroundImage: `url('https://images.unsplash.com/photo-1518837695005-2083093ee35b?q=80&w=2070&auto=format&fit=crop')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {/* Split View Container: Left Chat + Right Live Tool Output Inspector Panel */}
      <div className="flex-1 flex w-full overflow-hidden z-10 pt-16">
        {/* Left Column: Chat Conversation Stream */}
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto w-full px-4 sm:px-6 md:px-8 pb-6 space-y-6 max-w-4xl mx-auto no-scrollbar"
        >
          {messages.length === 0 ? (
            /* Empty State / Copilot Stitch View */
            <div className="min-h-[calc(100vh-14rem)] flex flex-col items-center justify-center space-y-8 my-auto py-8">
              {/* Greeting */}
              <div className="text-center space-y-3">
                <div className="w-20 h-20 rounded-3xl bg-white border border-slate-200 p-2 mx-auto mb-4 shadow-2xl shadow-black/30 flex items-center justify-center hover:scale-105 transition-transform">
                  <img src="/logo.png" alt="AetherPhoenix" className="w-16 h-16 object-contain drop-shadow" />
                </div>
                <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                  How can AetherPhoenix help today?
                </h2>
                <p className="text-sm text-slate-300 max-w-md mx-auto drop-shadow">
                  Decomposes complex requests into real executable tasks with permissions, telemetry, and artifacts.
                </p>
              </div>

              {/* Quick Action Pills - Glassmorphism style with see-through transparency */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5 w-full max-w-2xl pt-2">
                {realCapabilities.map((cap, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(cap.query)}
                    className="flex flex-col items-start p-4 rounded-2xl glass-card-hover text-left cursor-pointer active:scale-98"
                  >
                    <span className="text-xs font-bold text-white group-hover:text-cyan-200 transition-colors drop-shadow">
                      {cap.label}
                    </span>
                    <span className="text-[11px] text-slate-200/80 truncate w-full mt-1.5 font-normal">
                      {cap.query}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Live Messages Stream */
            <div className="space-y-6 pt-2 pb-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} w-full`}
                >
                  {msg.role !== 'user' && (
                    <div className="w-8 h-8 rounded-xl bg-slate-900 border border-indigo-500/30 flex items-center justify-center shrink-0 shadow mt-1">
                      <img src="/logo.png" alt="Agent" className="w-5 h-5 object-contain" />
                    </div>
                  )}

                  <div className={`space-y-3 max-w-[90%] sm:max-w-[80%]`}>
                    {/* User Bubble */}
                    {msg.role === 'user' && (
                      <div className="bg-indigo-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm shadow-md text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    )}

                    {/* Clarification Popcard */}
                    {msg.role !== 'user' && msg.status === 'clarifying' && (
                      <ClarificationPopcard
                        question={msg.content}
                        options={msg.options}
                        onSubmit={(ans) => submitClarification(ans)}
                      />
                    )}

                    {/* Plan Popcard */}
                    {msg.role !== 'user' && msg.planData && msg.status === 'ready' && (
                      <PlanPopcard
                        plan={msg.planData}
                        onApprove={(plan) => executePlan(plan)}
                        onEdit={(instruction) => handleSend(`Modify the plan: ${instruction}`)}
                      />
                    )}

                    {/* Permission Popcard */}
                    {msg.role !== 'user' && msg.permissionData && (
                      <PermissionPopcard
                        permission={msg.permissionData}
                        onApprove={(reqId) => approvePermission(reqId)}
                        onReject={(reqId) => rejectPermission(reqId)}
                      />
                    )}

                    {/* Workflow Live Progress Popcard */}
                    {msg.role !== 'user' && msg.workflowData && (
                      <WorkflowStatusPopcard workflow={msg.workflowData} />
                    )}

                    {/* Terminal Output Popcard */}
                    {msg.role !== 'user' && msg.terminalOutputData && (
                      <TerminalPopcard terminalData={msg.terminalOutputData} />
                    )}

                    {/* Artifact Popcard */}
                    {msg.role !== 'user' && msg.artifactData && (
                      <ArtifactPopcard artifact={msg.artifactData} />
                    )}

                    {/* Standard Agent Text Message */}
                    {msg.role !== 'user' &&
                      !msg.planData &&
                      !msg.permissionData &&
                      !msg.workflowData &&
                      !msg.artifactData &&
                      !msg.terminalOutputData &&
                      msg.status !== 'clarifying' && (
                        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 text-slate-200 px-5 py-3.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed whitespace-pre-wrap shadow-md">
                          {msg.content}
                        </div>
                      )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0 shadow text-slate-300 mt-1">
                      <span className="material-symbols-outlined text-sm">person</span>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex gap-3.5 items-center">
                  <div className="w-8 h-8 rounded-xl bg-slate-900 border border-indigo-500/30 flex items-center justify-center shrink-0 shadow">
                    <img src="/logo.png" alt="Agent" className="w-5 h-5 object-contain animate-pulse" />
                  </div>
                  <div className="bg-slate-900/90 border border-slate-800 px-4 py-3 rounded-2xl flex items-center gap-2 shadow">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" />
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 rounded-full bg-indigo-300 animate-bounce [animation-delay:0.4s]" />
                    <span className="text-xs text-slate-400 font-mono ml-2">Planner formulating response...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Right Column: Live External Tool & Terminal Execution Inspector Workspace (Right Red Box) */}
        {latestTerminalData && (
          <div className="hidden lg:flex flex-col w-96 mr-6 mb-6 bg-slate-950/90 backdrop-blur-2xl border border-slate-800 rounded-3xl p-5 shadow-2xl space-y-4 shrink-0 h-[calc(100vh-10rem)]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500 animate-ping" />
                <h3 className="text-xs font-bold font-mono text-emerald-400 uppercase tracking-wider">
                  Live Tool Execution Inspector
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                ACTIVE DOM / SHELL
              </span>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
                <span>Tool Target:</span>
                <span className="text-indigo-400 font-bold">TerminalToolAdapter</span>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
                <span>Executed Command:</span>
                <span className="text-emerald-400 font-bold">{latestTerminalData.command}</span>
              </div>
            </div>

            <div className="flex-1 bg-black/95 rounded-2xl p-4 border border-slate-900 font-mono text-xs text-emerald-300/90 overflow-y-auto leading-relaxed whitespace-pre-wrap">
              {latestTerminalData.stdout}
            </div>

            <div className="text-[11px] font-mono text-slate-400 text-center bg-slate-900/60 p-2 rounded-xl border border-slate-800/60">
              ✓ Direct live output capture complete
            </div>
          </div>
        )}
      </div>

      {/* Floating Composer Bottom Bar */}
      <footer className="p-4 sm:p-6 z-20 shrink-0">
        <div className="max-w-4xl mx-auto space-y-2">
          {selectedFile && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/80 backdrop-blur-md border border-indigo-500/30 rounded-xl text-xs text-indigo-300 w-fit">
              <span className="material-symbols-outlined text-sm">attachment</span>
              <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              <button onClick={() => setSelectedFile(null)} className="hover:text-white cursor-pointer ml-1">
                <span className="material-symbols-outlined text-xs">close</span>
              </button>
            </div>
          )}

          <div className="bg-slate-900/80 backdrop-blur-2xl border border-slate-700/60 focus-within:border-indigo-500/80 rounded-2xl p-2.5 flex items-center gap-2.5 shadow-2xl transition-all">
            {/* Hidden native file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />

            {/* Attachment Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-9 h-9 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-indigo-400 border border-slate-700/60 flex items-center justify-center transition-colors cursor-pointer shrink-0"
              title="Attach File"
            >
              <span className="material-symbols-outlined text-lg">attach_file</span>
            </button>

            {/* Main Input Text */}
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask AetherPhoenix or assign a desktop automation goal..."
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-400 focus:outline-none px-2"
            />

            {/* Send Button */}
            <button
              onClick={() => handleSend()}
              disabled={(!inputVal.trim() && !selectedFile) || loading}
              className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-30 text-white flex items-center justify-center transition-all cursor-pointer shadow-md shadow-indigo-600/30 shrink-0 active:scale-95"
            >
              <span className="material-symbols-outlined text-lg">arrow_upward</span>
            </button>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-2 font-mono drop-shadow">
            <span>Powered by AetherPhoenix Agent Engine</span>
            <span>Enter to Send</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

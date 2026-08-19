import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChatStore } from '../store/chatStore';

export const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const messages = useChatStore((state) => state.messages);
  const loading = useChatStore((state) => state.loading);
  const currentStatus = useChatStore((state) => state.currentStatus);
  const activePlan = useChatStore((state) => state.activePlan);
  const sendMessage = useChatStore((state) => state.sendMessage);

  const [inputVal, setInputVal] = useState('');
  const [selectedClarification, setSelectedClarification] = useState<string | null>(null);
  const [customClarificationText, setCustomClarificationText] = useState('');
  const [dismissClarification, setDismissClarification] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputVal.trim();
    if (!text || loading) return;

    setInputVal('');
    setDismissClarification(false);
    await sendMessage(text);
  };

  const handleClarificationSubmit = async () => {
    const answer =
      selectedClarification === 'custom'
        ? customClarificationText
        : selectedClarification === 'type'
        ? 'Categorize files by file type (Images, Documents, Videos)'
        : selectedClarification === 'date'
        ? 'Categorize files by date modified'
        : selectedClarification || '';

    if (!answer) return;
    setDismissClarification(true);
    setSelectedClarification(null);
    setCustomClarificationText('');
    await sendMessage(answer);
  };

  const chips = [
    'Compose a song',
    'Brainstorm ideas',
    'Learn something new',
    'Take a quiz',
    'Organize my Downloads folder',
  ];

  const lastPlannerMessage = messages.filter((m) => m.role === 'planner').slice(-1)[0];
  const lastUserMessage = messages.filter((m) => m.role === 'user').slice(-1)[0];
  const isClarifying = currentStatus === 'clarifying' && !dismissClarification && !!lastPlannerMessage;

  return (
    <div className="flex flex-col flex-1 min-h-[calc(100vh-4rem)] relative">
      {/* If no conversation has started, show Stitch HomePage Hero */}
      {messages.length === 0 ? (
        <section className="flex flex-col items-center justify-center text-center gap-8 py-16 px-4 flex-1">
          <h1 className="text-3xl md:text-5xl font-bold text-white tracking-tight max-w-2xl leading-tight">
            Hi KAUSHAL, what should we dive into today?
          </h1>

          {/* Stitch Search & Input Container */}
          <div className="w-full max-w-[720px] bg-surface-container-low/60 backdrop-blur-xl border border-outline-variant/30 rounded-[32px] p-4 flex flex-col gap-4 shadow-2xl">
            <div className="flex items-center w-full px-2">
              <input
                className="bg-transparent border-none text-white w-full focus:outline-none focus:ring-0 placeholder:text-on-surface-variant text-lg"
                placeholder="Message AetherPhoenix"
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
            </div>
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-3">
                <button className="w-8 h-8 rounded-full border border-outline-variant/40 flex items-center justify-center text-on-surface-variant hover:text-white hover:bg-white/10 transition-colors">
                  <span className="material-symbols-outlined text-[20px]">add</span>
                </button>
                <button className="px-4 py-1.5 rounded-full border border-outline-variant/40 flex items-center gap-1 text-on-surface-variant text-sm hover:text-white hover:bg-white/10 transition-colors">
                  Smart <span className="material-symbols-outlined text-[16px]">expand_more</span>
                </button>
              </div>
              <div className="flex items-center gap-4 text-on-surface-variant px-2">
                <span className="material-symbols-outlined text-[20px] cursor-pointer hover:text-white">
                  center_focus_strong
                </span>
                <span className="material-symbols-outlined text-[20px] cursor-pointer hover:text-white">
                  mic
                </span>
                <button
                  onClick={() => handleSend()}
                  disabled={!inputVal.trim() || loading}
                  className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center disabled:opacity-40 hover:bg-accent-electric transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">arrow_upward</span>
                </button>
              </div>
            </div>
          </div>

          {/* Suggestion Chips */}
          <div className="flex flex-wrap justify-center gap-2 max-w-[800px] mt-4">
            {chips.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="px-4 py-2 rounded-full bg-surface-container-low/40 backdrop-blur-md border border-outline-variant/20 text-on-surface-variant hover:text-white text-sm hover:bg-surface-container-highest/60 transition-all cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>
        </section>
      ) : (
        /* Active Conversation Flow */
        <div className="flex flex-col flex-1 max-w-4xl mx-auto w-full p-4 md:p-6 pb-32">
          <div className="flex flex-col gap-6 flex-1">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'planner' && (
                  <div className="w-9 h-9 rounded-full bg-surface-container-highest flex items-center justify-center border border-primary/30 shrink-0 overflow-hidden">
                    <img src="/logo.png" alt="Logo" className="w-6 h-6 object-contain" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl p-5 ${
                    msg.role === 'user'
                      ? 'bg-primary text-white shadow-lg'
                      : 'glass-panel text-white'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">
                    {msg.content}
                  </p>

                  {/* Plan CTA Card */}
                  {(msg.planData || activePlan) && (
                    <div className="mt-4 pt-4 border-t border-outline-variant/40 flex justify-between items-center">
                      <div>
                        <span className="text-xs font-bold uppercase text-accent-electric">Plan Generated</span>
                        <h4 className="text-sm font-semibold">
                          {(msg.planData || activePlan)?.workflow_spec || 'Execution Plan'}
                        </h4>
                      </div>
                      <button
                        onClick={() => navigate('/plan')}
                        className="px-4 py-2 rounded-lg bg-primary hover:bg-accent-electric text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-sm">visibility</span>
                        Review Plan
                      </button>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-9 h-9 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant/40 shrink-0">
                    <span className="material-symbols-outlined text-white text-sm">person</span>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-4 items-center">
                <div className="w-9 h-9 rounded-full bg-surface-container-highest flex items-center justify-center border border-primary/30 shrink-0">
                  <img src="/logo.png" alt="Logo" className="w-6 h-6 object-contain animate-pulse" />
                </div>
                <div className="glass-panel px-4 py-3 rounded-2xl flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce" />
                  <div className="w-2 h-2 rounded-full bg-accent-electric animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Sticky Bottom Input for Active Chat */}
          <div className="fixed bottom-16 md:bottom-6 left-0 md:left-64 right-0 px-4 z-30">
            <div className="max-w-4xl mx-auto bg-surface-deep/90 backdrop-blur-xl border border-outline-variant/30 rounded-[28px] p-2.5 flex items-center gap-3 shadow-2xl">
              <input
                className="bg-transparent border-none text-white w-full focus:outline-none px-4 text-sm md:text-base placeholder:text-on-surface-variant"
                placeholder="Ask AetherPhoenix a follow-up or command..."
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button
                onClick={() => handleSend()}
                disabled={!inputVal.trim() || loading}
                className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center disabled:opacity-40 hover:bg-accent-electric transition-colors shrink-0 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">arrow_upward</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stitch Clarification Modal Popup */}
      {isClarifying && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-[500px] rounded-xl overflow-hidden flex flex-col glow-active animate-fade-in-up">
            <div className="p-6 border-b border-outline-variant/50 flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-full flex items-center justify-center">
                <span className="material-symbols-outlined text-accent-electric icon-fill">help</span>
              </div>
              <h2 className="text-xl font-bold text-on-surface">Clarification Needed</h2>
            </div>
            <div className="p-6 flex flex-col gap-6">
              {lastUserMessage && (
                <div className="bg-surface-container-low p-4 rounded-lg border-l-4 border-l-accent-electric">
                  <p className="text-[10px] text-on-surface-muted uppercase tracking-widest font-bold mb-1">
                    Context:
                  </p>
                  <p className="text-on-surface italic">"{lastUserMessage.content}"</p>
                </div>
              )}
              <div>
                <h3 className="text-lg font-semibold text-on-surface mb-4">
                  {lastPlannerMessage?.content || 'How should we categorize files?'}
                </h3>
                <div className="space-y-3">
                  {[
                    { id: 'type', label: 'By file type', subtext: 'e.g., Images, Documents, Videos' },
                    { id: 'date', label: 'By date', subtext: 'e.g., Today, Last Week, Older' },
                    { id: 'custom', label: 'Custom', subtext: 'Describe your structure...' },
                  ].map((opt) => (
                    <label
                      key={opt.id}
                      className={`flex items-center gap-4 p-4 rounded-lg border transition-all cursor-pointer ${
                        selectedClarification === opt.id
                          ? 'border-primary bg-primary/10'
                          : 'border-outline-variant/50 hover:bg-surface-container-highest'
                      }`}
                    >
                      <input
                        type="radio"
                        name="clarification_method"
                        className="w-4 h-4 text-primary bg-transparent border-outline-variant focus:ring-primary"
                        onChange={() => setSelectedClarification(opt.id)}
                        checked={selectedClarification === opt.id}
                      />
                      <div className="flex flex-col flex-1">
                        <span className="font-semibold text-white">{opt.label}</span>
                        {opt.id === 'custom' && selectedClarification === 'custom' ? (
                          <input
                            className="mt-2 w-full p-2 bg-surface-deep rounded border border-outline-variant text-sm focus:border-primary outline-none text-white"
                            placeholder={opt.subtext}
                            value={customClarificationText}
                            onChange={(e) => setCustomClarificationText(e.target.value)}
                            autoFocus
                          />
                        ) : (
                          <span className="text-xs text-on-surface-muted">{opt.subtext}</span>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-outline-variant/50 flex justify-end gap-3 bg-surface-container-low/30">
              <button
                onClick={() => setDismissClarification(true)}
                className="px-6 py-2 rounded-lg border border-outline-variant text-on-surface-muted hover:bg-surface-variant transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleClarificationSubmit}
                disabled={!selectedClarification || (selectedClarification === 'custom' && !customClarificationText.trim())}
                className={`px-6 py-2 rounded-lg font-bold transition-all ${
                  selectedClarification
                    ? 'bg-primary text-white hover:bg-accent-electric shadow-lg cursor-pointer'
                    : 'bg-surface-container text-on-surface-muted cursor-not-allowed'
                }`}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

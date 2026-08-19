import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChatStore } from '../store/chatStore';

export const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const messages = useChatStore((state) => state.messages);
  const loading = useChatStore((state) => state.loading);
  const activePlan = useChatStore((state) => state.activePlan);
  const sendMessage = useChatStore((state) => state.sendMessage);

  const [inputVal, setInputVal] = useState('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputVal.trim();
    if (!text || loading) return;

    setInputVal('');
    await sendMessage(text);
  };

  const chips = [
    'Compose a song',
    'Brainstorm Ideas',
    'Learn something new',
    'Take a quiz',
    'Get advice',
    'Practice a language',
  ];

  return (
    <div
      className="flex-1 relative flex flex-col justify-between overflow-hidden min-h-screen bg-cover bg-center"
      style={{
        backgroundImage: `radial-gradient(circle at center, rgba(15, 23, 42, 0.65), rgba(2, 6, 23, 0.95)), url('https://images.unsplash.com/photo-1518837695005-2083093ee35b?q=80&w=2070&auto=format&fit=crop')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {messages.length === 0 ? (
        /* Copilot-style Chat UI Empty State */
        <div className="max-w-4xl mx-auto w-full px-6 pt-16 pb-20 flex-1 flex flex-col items-center justify-center space-y-8 z-10">
          {/* Greeting */}
          <h1 className="text-3xl sm:text-4xl font-semibold text-white tracking-tight text-center">
            Nice to see you, <span className="font-bold">KAUSHAL</span>. What's new?
          </h1>

          {/* Floating Glass Input Box */}
          <div className="w-full max-w-2xl bg-slate-900/80 backdrop-blur-2xl border border-slate-700/60 rounded-3xl p-4 shadow-2xl shadow-black/50 space-y-3">
            <input
              type="text"
              placeholder="Message Copilot..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-400 focus:outline-none px-2"
            />
            
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/50 text-slate-400">
              <div className="flex items-center gap-2">
                <button className="p-1.5 hover:bg-slate-800 rounded-full transition-colors">
                  <span className="material-symbols-outlined text-lg">add</span>
                </button>
                <button className="flex items-center gap-1 text-xs px-2.5 py-1 bg-slate-800/80 hover:bg-slate-800 rounded-full border border-slate-700/50 transition-colors">
                  <span>Smart</span>
                  <span className="material-symbols-outlined text-sm">expand_more</span>
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-1.5 hover:bg-slate-800 rounded-full transition-colors">
                  <span className="material-symbols-outlined text-lg">glasses</span>
                </button>
                <button className="p-1.5 hover:bg-slate-800 rounded-full transition-colors">
                  <span className="material-symbols-outlined text-lg">graphic_eq</span>
                </button>
                <button
                  onClick={() => handleSend()}
                  disabled={!inputVal.trim() || loading}
                  className="p-1.5 hover:bg-slate-800 rounded-full text-indigo-400 hover:text-indigo-300 disabled:opacity-40 transition-colors"
                >
                  <span className="material-symbols-outlined text-lg">send</span>
                </button>
              </div>
            </div>
          </div>

          {/* Quick Suggestion Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
            {chips.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="px-3.5 py-1.5 rounded-full bg-slate-900/60 hover:bg-slate-800/80 border border-slate-700/40 text-xs text-slate-300 backdrop-blur-md transition-all cursor-pointer hover:border-indigo-500/50 hover:text-white"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Bottom Recent Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl pt-6">
            {/* Attached Files Card */}
            <div className="bg-slate-900/70 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">attach_file</span> Attach a recent file to chat
                </span>
                <span className="material-symbols-outlined text-sm">info</span>
              </div>
              <div className="space-y-2">
                <div
                  onClick={() => handleSend("Analyze the main_dash.txt file")}
                  className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300">
                      <span className="material-symbols-outlined text-base">description</span>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-slate-200">main_dash.txt</div>
                      <div className="text-[10px] text-slate-500">Yesterday</div>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-slate-500 text-sm">more_horiz</span>
                </div>
                <div
                  onClick={() => handleSend("Look at aether_logo_bg.png")}
                  className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                      <span className="material-symbols-outlined text-base">image</span>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-slate-200">aether_logo_bg.png</div>
                      <div className="text-[10px] text-slate-500">Yesterday</div>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-slate-500 text-sm">more_horiz</span>
                </div>
              </div>
            </div>

            {/* Keep Talking Card */}
            <div className="bg-slate-900/70 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">chat_bubble_outline</span> Keep talking to Copilot
                </span>
              </div>
              <div className="space-y-2">
                <div
                  onClick={() => handleSend("Explain Color Bandwidth Limitation in TV")}
                  className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300">
                      <span className="material-symbols-outlined text-base">chat</span>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-slate-200 line-clamp-1">Color Bandwidth Limitation in TV</div>
                      <div className="text-[10px] text-slate-500">Tuesday, May 5</div>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-slate-500 text-sm">more_horiz</span>
                </div>
                <div
                  onClick={() => handleSend("What is the Chessboard Square Color Logic?")}
                  className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300">
                      <span className="material-symbols-outlined text-base">chat</span>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-slate-200 line-clamp-1">Chessboard Square Color Logic</div>
                      <div className="text-[10px] text-slate-500">Tuesday, May 5</div>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-slate-500 text-sm">more_horiz</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Active Conversation Flow */
        <div className="flex flex-col flex-1 max-w-4xl mx-auto w-full p-4 md:p-6 pb-32 z-10">
          <div className="flex flex-col gap-6 flex-1 pt-8">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'planner' && (
                  <div className="w-9 h-9 rounded-full bg-slate-900 border border-indigo-500/30 flex items-center justify-center shrink-0 overflow-hidden shadow">
                    <img src="/logo.png" alt="Logo" className="w-6 h-6 object-contain" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl p-5 ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/10'
                      : 'bg-slate-900/90 backdrop-blur-md border border-slate-800/80 text-white shadow-lg'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">
                    {msg.content}
                  </p>

                  {/* Plan CTA Card */}
                  {(msg.planData || activePlan) && (
                    <div className="mt-4 pt-4 border-t border-slate-800/40 flex justify-between items-center gap-4">
                      <div>
                        <span className="text-[10px] font-bold uppercase text-indigo-400 tracking-wider">Plan Generated</span>
                        <h4 className="text-sm font-semibold text-slate-200">
                          {(msg.planData || activePlan)?.workflow_spec || 'Execution Plan'}
                        </h4>
                      </div>
                      <button
                        onClick={() => navigate('/plan')}
                        className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow cursor-pointer shrink-0"
                      >
                        <span className="material-symbols-outlined text-sm">visibility</span>
                        Review Plan
                      </button>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-9 h-9 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0 shadow">
                    <span className="material-symbols-outlined text-white text-sm">person</span>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-4 items-center">
                <div className="w-9 h-9 rounded-full bg-slate-900 border border-indigo-500/30 flex items-center justify-center shrink-0 shadow">
                  <img src="/logo.png" alt="Logo" className="w-6 h-6 object-contain animate-pulse" />
                </div>
                <div className="bg-slate-900/90 border border-slate-800/80 px-4 py-3 rounded-2xl flex items-center gap-2 shadow">
                  <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" />
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 rounded-full bg-indigo-300 animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Sticky Bottom Input for Active Chat */}
          <div className="fixed bottom-6 left-0 md:left-64 right-0 px-6 z-30">
            <div className="max-w-4xl mx-auto bg-slate-900/95 backdrop-blur-2xl border border-slate-800/80 rounded-[28px] p-3 flex items-center gap-3 shadow-2xl shadow-black/80">
              <input
                className="bg-transparent border-none text-white w-full focus:outline-none px-4 text-sm md:text-base placeholder:text-slate-500"
                placeholder="Ask AetherPhoenix a follow-up or command..."
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button
                onClick={() => handleSend()}
                disabled={!inputVal.trim() || loading}
                className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center disabled:opacity-40 hover:bg-indigo-500 transition-all cursor-pointer shadow"
              >
                <span className="material-symbols-outlined text-[18px]">arrow_upward</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

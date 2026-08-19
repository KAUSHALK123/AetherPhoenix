import React, { useState } from 'react';
import { Send, Shield, Sparkles } from 'lucide-react';
import { Button } from '../common/Button';

export interface ChatInputProps {
  onSend: (text: string) => void;
  isLoading?: boolean;
  isClarifying?: boolean;
  executionMode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS';
  onModeChange?: (mode: 'SAFE' | 'ASSISTED' | 'AUTONOMOUS') => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  isLoading = false,
  isClarifying = false,
  executionMode,
  onModeChange,
}) => {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSend(text.trim());
    setText('');
  };

  const modeColors = {
    SAFE: 'text-emerald-400 border-emerald-500/40 bg-emerald-950/30',
    ASSISTED: 'text-sky-400 border-sky-500/40 bg-sky-950/30',
    AUTONOMOUS: 'text-purple-400 border-purple-500/40 bg-purple-950/30',
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Mode Selector & Quick Prompts */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 flex items-center gap-1 font-mono">
            <Shield className="w-3.5 h-3.5 text-slate-500" />
            Execution Mode:
          </span>
          <div className="flex rounded-lg border border-slate-800 bg-slate-950/70 p-0.5">
            {(['SAFE', 'ASSISTED', 'AUTONOMOUS'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => onModeChange && onModeChange(mode)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-medium transition-all ${
                  executionMode === mode
                    ? modeColors[mode]
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="text-slate-500 font-mono text-[11px] hidden sm:block">
          Press Shift + Enter for new line
        </div>
      </div>

      {/* Input Field Container */}
      <div className="relative glass-panel rounded-2xl p-2 focus-within:border-sky-500/60 focus-within:ring-1 focus-within:ring-sky-500/30 transition-all duration-200">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder={
            isClarifying
              ? 'Answer planner clarification questions...'
              : "Describe your goal (e.g., 'Research competitors, extract key metrics and generate an executive summary slide deck')..."
          }
          rows={2}
          disabled={isLoading}
          className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm px-3 py-2 resize-none focus:outline-none"
        />

        <div className="flex items-center justify-between pt-2 px-2 border-t border-slate-800/60">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span>Autonomous Execution Engine</span>
          </div>

          <Button
            type="submit"
            variant="planner"
            size="sm"
            isLoading={isLoading}
            disabled={!text.trim() || isLoading}
          >
            <Send className="w-4 h-4 mr-1" />
            {isClarifying ? 'Answer' : 'Generate Plan'}
          </Button>
        </div>
      </div>
    </form>
  );
};

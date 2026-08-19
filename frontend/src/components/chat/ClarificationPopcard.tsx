import React, { useState } from 'react';

export interface ClarificationPopcardProps {
  question: string;
  options?: string[];
  onSubmit: (answer: string) => void;
  isLoading?: boolean;
}

export const ClarificationPopcard: React.FC<ClarificationPopcardProps> = ({
  question,
  options = [
    'Create PowerPoint with 5 slides',
    'Include comprehensive technical citations',
    'Generate concise executive summary',
  ],
  onSubmit,
  isLoading = false,
}) => {
  const [customText, setCustomText] = useState('');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  const handleOptionClick = (opt: string) => {
    setSelectedOption(opt);
    setCustomText(opt);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const answer = customText.trim() || selectedOption;
    if (answer) {
      onSubmit(answer);
    }
  };

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-indigo-500/40 rounded-2xl p-5 shadow-2xl shadow-black/60 space-y-4 max-w-xl w-full">
      <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800/80 text-indigo-400 font-semibold text-sm">
        <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
          <span className="material-symbols-outlined text-base">help</span>
        </div>
        <div>
          <span className="text-white font-bold text-sm">Planner Clarification</span>
          <p className="text-[11px] text-slate-400 font-normal">Choose an option or type a response</p>
        </div>
      </div>

      <p className="text-slate-200 text-sm font-medium whitespace-pre-wrap leading-relaxed">
        {question}
      </p>

      {/* Suggested option chips */}
      {options && options.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">
            Structured Choices
          </div>
          <div className="flex flex-col gap-2">
            {options.map((opt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleOptionClick(opt)}
                className={`text-xs px-3.5 py-2.5 rounded-xl border transition-all text-left flex items-center justify-between cursor-pointer ${
                  selectedOption === opt
                    ? 'bg-indigo-600/30 border-indigo-400 text-indigo-200 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-indigo-500/40 hover:text-white'
                }`}
              >
                <span>{opt}</span>
                <span className="material-symbols-outlined text-sm text-slate-500">
                  {selectedOption === opt ? 'radio_button_checked' : 'radio_button_unchecked'}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Custom input submission */}
      <form onSubmit={handleSubmit} className="flex gap-2 pt-1">
        <input
          type="text"
          value={customText}
          onChange={(e) => {
            setCustomText(e.target.value);
            setSelectedOption(null);
          }}
          placeholder="Or type custom specification..."
          className="flex-1 bg-slate-950/90 border border-slate-800 focus:border-indigo-500 text-xs px-3.5 py-2.5 rounded-xl text-white placeholder-slate-500 focus:outline-none"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={(!customText.trim() && !selectedOption) || isLoading}
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all disabled:opacity-40 flex items-center gap-1.5 cursor-pointer shadow active:scale-95"
        >
          <span className="material-symbols-outlined text-sm">send</span>
          Submit
        </button>
      </form>
    </div>
  );
};

import React, { useState } from 'react';
import { HelpCircle, Send } from 'lucide-react';
import { Button } from '../common/Button';

export interface ClarificationCardProps {
  question: string;
  options?: string[];
  onSubmit: (answer: string) => void;
  isLoading?: boolean;
}

export const ClarificationCard: React.FC<ClarificationCardProps> = ({
  question,
  options = ['Yes, proceed with default settings', 'Include detailed research & citations', 'Generate high-level overview only'],
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
    <div className="bg-amber-950/30 border border-amber-500/40 rounded-xl p-5 shadow-lg shadow-amber-950/20 backdrop-blur-md">
      <div className="flex items-center gap-2.5 mb-3 text-amber-400 font-semibold text-sm">
        <HelpCircle className="w-5 h-5" />
        <span>Clarification Required</span>
      </div>

      <p className="text-slate-100 text-sm font-medium mb-4 whitespace-pre-wrap leading-relaxed">
        {question}
      </p>

      {/* Suggested option chips */}
      <div className="space-y-2 mb-4">
        <div className="text-xs uppercase tracking-wider text-amber-400/80 font-mono font-medium">
          Suggested Responses
        </div>
        <div className="flex flex-wrap gap-2">
          {options.map((opt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleOptionClick(opt)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all text-left ${
                selectedOption === opt
                  ? 'bg-amber-500/20 border-amber-400 text-amber-200 shadow-sm'
                  : 'bg-slate-900/60 border-slate-700/80 text-slate-300 hover:border-amber-500/40 hover:text-amber-300'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Custom input submission */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={customText}
          onChange={(e) => {
            setCustomText(e.target.value);
            setSelectedOption(null);
          }}
          placeholder="Type your clarification answer..."
          className="flex-1 glass-input text-sm px-3.5 py-2 rounded-lg"
          disabled={isLoading}
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          isLoading={isLoading}
          disabled={!customText.trim() && !selectedOption}
        >
          <Send className="w-4 h-4 mr-1" />
          Submit
        </Button>
      </form>
    </div>
  );
};

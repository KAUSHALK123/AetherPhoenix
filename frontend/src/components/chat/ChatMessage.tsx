import React from 'react';
import { User, Bot, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { Message } from '../../types/planner';
import { ClarificationCard } from './ClarificationCard';
import { PlanViewer } from './PlanViewer';

export interface ChatMessageProps {
  message: Message;
  onSubmitClarification?: (answer: string) => void;
  onApprovePlan?: () => void;
  onModifyTask?: (taskId: string, instruction: string) => void;
  onCancelPlan?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onSubmitClarification,
  onApprovePlan,
  onModifyTask,
  onCancelPlan,
}) => {
  const isUser = message.role === 'user';
  const isClarifying = message.status === 'clarifying';
  const isPlanReady = message.status === 'ready' && message.planData;
  const isError = message.status === 'error';

  return (
    <div className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'} w-full`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-sky-950/80 border border-sky-500/40 text-sky-400 flex items-center justify-center shrink-0 shadow-lg shadow-sky-950/40 mt-1">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={`max-w-[90%] md:max-w-[80%] space-y-3`}>
        {/* User Message Bubble */}
        {isUser && (
          <div className="bg-indigo-600/90 text-slate-100 px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-md border border-indigo-500/40 text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        )}

        {/* Clarification Message */}
        {!isUser && isClarifying && (
          <ClarificationCard
            question={message.content}
            onSubmit={(ans) => onSubmitClarification && onSubmitClarification(ans)}
          />
        )}

        {/* Visual Plan Viewer */}
        {!isUser && isPlanReady && (
          <PlanViewer
            plan={message.planData!}
            rawJsonString={message.content}
            onApprove={onApprovePlan}
            onModifyTask={onModifyTask}
            onCancel={onCancelPlan}
          />
        )}

        {/* Error Notice */}
        {!isUser && isError && (
          <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-4 text-rose-300 text-sm flex items-start gap-3 shadow-lg">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-semibold text-rose-200">Planner Error</div>
              <p className="text-xs text-rose-300/90 whitespace-pre-wrap">
                {message.content}
              </p>
            </div>
          </div>
        )}

        {/* Standard Planner Text Response */}
        {!isUser && !isClarifying && !isPlanReady && !isError && (
          <div className="glass-card text-slate-200 px-5 py-4 rounded-2xl rounded-tl-sm text-sm leading-relaxed whitespace-pre-wrap border border-slate-700/80 shadow-md">
            <div className="flex items-center gap-1.5 text-xs text-sky-400 font-mono font-medium mb-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Planner Agent Response
            </div>
            {message.content}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-indigo-950/80 border border-indigo-500/40 text-indigo-300 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-950/40 mt-1">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};

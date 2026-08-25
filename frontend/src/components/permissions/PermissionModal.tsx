import React, { useState } from 'react';
import { ShieldAlert, Check, X, Terminal } from 'lucide-react';
import type { PermissionRequest } from '../../types/permission';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';

export interface PermissionModalProps {
  request: PermissionRequest | null;
  onApprove: (requestId: string, message?: string) => Promise<void>;
  onReject: (requestId: string, message?: string) => Promise<void>;
  onDismiss?: () => void;
}

export const PermissionModal: React.FC<PermissionModalProps> = ({
  request,
  onApprove,
  onReject,
  onDismiss,
}) => {
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);

  if (!request) return null;

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await onApprove(request.request_id);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await onReject(request.request_id, rejectReason || undefined);
    } finally {
      setIsSubmitting(false);
      setShowRejectInput(false);
      setRejectReason('');
    }
  };

  const getRiskBadge = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return <Badge variant="danger">{risk} RISK</Badge>;
      case 'MEDIUM':
        return <Badge variant="warning">{risk} RISK</Badge>;
      default:
        return <Badge variant="success">{risk} RISK</Badge>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-lg glass-panel rounded-2xl border border-amber-500/40 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="bg-amber-950/40 px-6 py-4 border-b border-amber-500/30 flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-amber-300 font-bold">
            <ShieldAlert className="w-5 h-5 text-amber-400 animate-pulse" />
            <span>Security Permission Required</span>
          </div>
          {getRiskBadge(request.risk_level)}
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 text-sm">
          <p className="text-slate-300 leading-relaxed">
            An automated worker task is requesting elevated authorization to execute a protected capability:
          </p>

          <div className="bg-slate-950/80 rounded-xl p-4 border border-slate-800 space-y-3 font-mono text-xs">
            <div>
              <div className="text-slate-500 uppercase tracking-wider text-[11px] mb-0.5">
                Capability / Permission Type
              </div>
              <div className="text-sky-300 font-bold flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-sky-400" />
                {request.permission_type}
              </div>
            </div>

            <div>
              <div className="text-slate-500 uppercase tracking-wider text-[11px] mb-0.5">
                Reason & Context
              </div>
              <div className="text-slate-200 font-sans text-sm font-medium">
                {request.reason}
              </div>
            </div>

            {request.task_id && (
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-slate-500">
                <span>Task ID:</span>
                <span className="text-slate-400">{request.task_id}</span>
              </div>
            )}

            {request.workflow_id && (
              <div className="flex items-center justify-between text-slate-500">
                <span>Workflow:</span>
                <span className="text-slate-400">{request.workflow_id}</span>
              </div>
            )}
          </div>

          {/* Optional rejection reason input */}
          {showRejectInput && (
            <div className="space-y-1.5 pt-2">
              <label className="text-xs font-semibold text-slate-400">
                Reason for Denial (Optional):
              </label>
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g., Unsafe file path or unverified website"
                className="glass-input w-full text-xs px-3 py-2 rounded-lg"
              />
            </div>
          )}
        </div>

        {/* Actions Footer */}
        <div className="px-6 py-4 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between gap-3">
          <button
            onClick={() => onDismiss && onDismiss()}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Review Later
          </button>

          <div className="flex items-center gap-2">
            {!showRejectInput ? (
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowRejectInput(true)}
                disabled={isSubmitting}
              >
                <X className="w-4 h-4 mr-1" />
                Deny
              </Button>
            ) : (
              <Button
                variant="danger"
                size="sm"
                onClick={handleReject}
                isLoading={isSubmitting}
              >
                <X className="w-4 h-4 mr-1" />
                Confirm Deny
              </Button>
            )}

            <Button
              variant="success"
              size="sm"
              onClick={handleApprove}
              isLoading={isSubmitting}
            >
              <Check className="w-4 h-4 mr-1" />
              Allow Action
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

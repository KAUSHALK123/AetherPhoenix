import React from 'react';

export interface BadgeProps {
  variant?: 'primary' | 'planner' | 'worker' | 'supervisor' | 'healing' | 'success' | 'warning' | 'danger' | 'neutral';
  size?: 'sm' | 'md';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  size = 'sm',
  children,
  className = '',
}) => {
  const variantStyles: Record<string, string> = {
    primary: 'bg-indigo-950/70 text-indigo-300 border-indigo-700/60',
    planner: 'bg-sky-950/70 text-sky-300 border-sky-600/50',
    worker: 'bg-orange-950/70 text-orange-300 border-orange-600/50',
    supervisor: 'bg-purple-950/70 text-purple-300 border-purple-600/50',
    healing: 'bg-rose-950/70 text-rose-300 border-rose-600/50',
    success: 'bg-emerald-950/70 text-emerald-300 border-emerald-600/50',
    warning: 'bg-amber-950/70 text-amber-300 border-amber-600/50',
    danger: 'bg-red-950/70 text-red-300 border-red-600/50',
    neutral: 'bg-slate-800/80 text-slate-300 border-slate-700/80',
  };

  const sizeStyles: Record<string, string> = {
    sm: 'text-xs px-2.5 py-0.5 font-medium rounded-full',
    md: 'text-sm px-3 py-1 font-medium rounded-md',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 border uppercase tracking-wider font-mono ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};

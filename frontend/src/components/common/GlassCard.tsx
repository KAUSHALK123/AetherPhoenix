import React from 'react';

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  glow?: 'planner' | 'worker' | 'supervisor' | 'healing' | 'none';
  className?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  glow = 'none',
  className = '',
  ...props
}) => {
  const glowStyles = {
    planner: 'glow-planner border-sky-500/30',
    worker: 'glow-worker border-orange-500/30',
    supervisor: 'glow-supervisor border-purple-500/30',
    healing: 'glow-healing border-rose-500/30',
    none: '',
  };

  return (
    <div
      className={`glass-card rounded-xl p-5 ${glowStyles[glow]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Bot,
  Workflow,
  Activity,
  ShieldCheck,
  Users,
  HeartPulse,
  FileBox,
  Brain,
  KeyRound,
  Sliders,
  Sparkles,
  ShieldAlert,
} from 'lucide-react';
import { usePermissionStore } from '../store/permissionStore';

export const Sidebar: React.FC = () => {
  const pendingCount = usePermissionStore((state) => state.pendingRequests.length);

  const navigationItems = [
    { name: 'Assistant / Chat', path: '/chat', icon: Bot, badge: null },
    { name: 'Workflow Visualizer', path: '/workflow', icon: Workflow, badge: null },
    { name: 'Runtime Execution', path: '/runtime', icon: Activity, badge: null },
    {
      name: 'Permission Center',
      path: '/permissions',
      icon: ShieldCheck,
      badge: pendingCount > 0 ? `${pendingCount} Pending` : null,
      badgeVariant: 'warning',
    },
    { name: 'Agent Registry', path: '/agents', icon: Users, badge: null },
    { name: 'System Health', path: '/health', icon: HeartPulse, badge: null },
    { name: 'Artifacts Gallery', path: '/artifacts', icon: FileBox, badge: null },
    { name: 'Memory & Context', path: '/memory', icon: Brain, badge: null },
    { name: 'Security Logs', path: '/security-logs', icon: ShieldAlert, badge: null },
    { name: 'API Tokens', path: '/api-tokens', icon: KeyRound, badge: null },
    { name: 'Settings', path: '/settings', icon: Sliders, badge: null },
  ];

  return (
    <aside className="w-64 shrink-0 glass-panel border-r border-slate-800 flex flex-col justify-between h-screen sticky top-0">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-sky-500 to-indigo-400 p-0.5 shadow-lg shadow-indigo-600/30 group-hover:scale-105 transition-transform">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-sky-400" />
              </div>
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-slate-100 group-hover:text-sky-400 transition-colors">
                AETHER PHOENIX
              </div>
              <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                AI Desktop Suite
              </div>
            </div>
          </NavLink>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1 overflow-y-auto max-h-[calc(100vh-140px)]">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-sky-500/10 text-sky-300 border border-sky-500/30 shadow-sm shadow-sky-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold bg-amber-950/80 text-amber-300 border border-amber-500/40 animate-pulse">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / System Status Pill */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 text-xs text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="font-mono text-[11px] text-slate-300">Kernel Online</span>
        </div>
        <span className="font-mono text-[10px] text-slate-600">v0.1.0</span>
      </div>
    </aside>
  );
};

import React from 'react';
import { NavLink, Link } from 'react-router-dom';

export const DesktopNav: React.FC = () => {
  const navItems = [
    { path: '/', icon: 'home', label: 'Dashboard' },
    { path: '/chat', icon: 'chat_bubble', label: 'Mission Control' },
    { path: '/plan', icon: 'account_tree', label: 'Agent Logs' },
    { path: '/execution', icon: 'terminal', label: 'Active Execution' },
    { path: '/permissions', icon: 'verified_user', label: 'Permissions' },
    { path: '/artifacts', icon: 'inventory_2', label: 'Artifacts' },
  ];

  return (
    <nav className="hidden md:flex h-full w-64 fixed left-0 top-0 border-r border-outline-variant/20 flex-col gap-1 py-6 bg-surface-container-low z-40">
      <Link
        to="/"
        className="px-6 pb-6 mb-6 border-b border-outline-variant/20 flex items-center gap-3 hover:opacity-85 transition-opacity cursor-pointer"
      >
        <div className="w-10 h-10 rounded-lg bg-surface-container-highest flex items-center justify-center border border-outline-variant/40 overflow-hidden">
          <img src="/logo.png" alt="Logo" className="w-7 h-7 object-contain" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-primary">AetherPhoenix</h2>
          <p className="text-[10px] text-on-surface-muted uppercase tracking-wider">v1.0.0-Beta</p>
        </div>
      </Link>
      <div className="px-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-4 px-4 py-2 rounded-lg text-on-surface-variant hover:bg-surface-variant/40 transition-colors ${
                isActive ? 'bg-surface-variant/60 text-white font-medium border-l-2 border-primary' : ''
              }`
            }
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="text-sm font-medium">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

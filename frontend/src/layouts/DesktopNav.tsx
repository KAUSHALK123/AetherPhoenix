import React from 'react';
import { NavLink, Link } from 'react-router-dom';

interface DesktopNavProps {
  isChatPage?: boolean;
}

export const DesktopNav: React.FC<DesktopNavProps> = ({ isChatPage = false }) => {
  const [isOpen, setIsOpen] = React.useState(false);

  const navItems = [
    { path: '/', icon: 'home', label: 'Dashboard' },
    { path: '/chat', icon: 'chat_bubble', label: 'Mission Control' },
    { path: '/plan', icon: 'account_tree', label: 'Plan Review' },
    { path: '/execution', icon: 'terminal', label: 'Active Execution' },
    { path: '/permissions', icon: 'verified_user', label: 'Permissions' },
    { path: '/artifacts', icon: 'inventory_2', label: 'Artifacts' },
  ];

  if (isChatPage) {
    return (
      <>
        {/* Sticky Trigger Logo for Fullscreen Chat */}
        <div className="fixed top-4 left-4 z-50">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="w-12 h-12 rounded-2xl bg-white border border-slate-200 p-2 shadow-2xl hover:scale-105 transition-all flex items-center justify-center cursor-pointer group"
            title="Toggle Navigation Menu"
          >
            <img
              src="/logo.png"
              alt="AetherPhoenix Logo"
              className="w-8 h-8 object-contain pointer-events-none drop-shadow"
            />
          </button>
        </div>

        {/* Backdrop for Overlay Drawer (No blur on underlying chat) */}
        {isOpen && (
          <div
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-black/40 z-40 transition-opacity duration-300"
          />
        )}

        {/* Drawer Overlay Menu (Glassmorphic to show ocean background behind it with 50px rounded corners on the pull-out edge) */}
        <div
          className={`fixed left-0 top-0 h-full w-80 bg-slate-950/80 backdrop-blur-2xl border-r border-slate-800/80 rounded-r-[50px] p-6 flex flex-col gap-6 z-50 shadow-2xl transition-transform duration-300 ease-in-out ${
            isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex items-center justify-between pb-5 border-b border-slate-800/80">
            <Link
              to="/"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3.5 group"
            >
              <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 flex items-center justify-center p-1 shadow-lg shadow-black/20 group-hover:scale-105 transition-transform">
                <img src="/logo.png" alt="Logo" className="w-9 h-9 object-contain drop-shadow" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors">AetherPhoenix</h2>
                <p className="text-[10px] font-mono text-indigo-400">Desktop Suite</p>
              </div>
            </Link>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <div className="space-y-1.5 flex-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-inner'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`
                }
              >
                <span className="material-symbols-outlined text-xl">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 font-mono">
            <span>v1.0.0-Beta</span>
          </div>
        </div>
      </>
    );
  }

  return (
    <nav className="hidden md:flex h-full w-64 fixed left-0 top-0 border-r border-outline-variant/20 flex-col gap-1 py-6 bg-surface-container-low z-40">
      <Link
        to="/"
        className="px-6 pb-6 mb-6 border-b border-outline-variant/20 flex items-center gap-3 hover:opacity-85 transition-opacity cursor-pointer"
      >
        <div className="w-14 h-14 rounded-xl bg-surface-container-highest flex items-center justify-center border border-outline-variant/40 overflow-hidden">
          <img src="/logo.png" alt="Logo" className="w-10 h-10 object-contain" />
        </div>
        <div>
          <h2 className="text-xl font-extrabold text-primary">AetherPhoenix</h2>
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

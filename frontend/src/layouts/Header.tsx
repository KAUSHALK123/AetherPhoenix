import React from 'react';
import { Link } from 'react-router-dom';
import { usePermissionStore } from '../store/permissionStore';

export const Header: React.FC = () => {
  const pendingRequests = usePermissionStore((state) => state.pendingRequests);

  return (
    <header className="fixed top-0 w-full z-50 bg-surface-deep/60 backdrop-blur-md border-b border-outline-variant/20 flex justify-between items-center px-6 h-16">
      <Link to="/" className="flex items-center gap-3 active:opacity-70">
        <img src="/logo.png" alt="AetherPhoenix Logo" className="w-8 h-8 object-contain rounded drop-shadow-md" />
        <h1 className="text-xl font-bold text-white tracking-tight">AetherPhoenix</h1>
      </Link>
      <div className="flex items-center gap-4">
        <Link
          to="/permissions"
          className="text-on-surface-variant hover:text-white transition-colors relative flex items-center justify-center p-1"
          title="Permissions Center"
        >
          <span className="material-symbols-outlined text-[22px]">shield_with_heart</span>
          {pendingRequests.length > 0 && (
            <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-accent-electric rounded-full animate-ping" />
          )}
        </Link>
        <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center border border-outline-variant/30">
          <span className="material-symbols-outlined text-white text-[20px]">person</span>
        </div>
      </div>
    </header>
  );
};

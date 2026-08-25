import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { DesktopNav } from './DesktopNav';
import { usePermissionStore } from '../store/permissionStore';

export const AppLayout: React.FC = () => {
  const fetchPending = usePermissionStore((state) => state.fetchPending);
  const location = useLocation();
  const isChatPage = location.pathname === '/chat';

  useEffect(() => {
    fetchPending();
    const interval = setInterval(() => {
      fetchPending();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchPending]);

  return (
    <div className="relative w-screen h-screen overflow-hidden text-white font-body select-none">
      {/* Universal Full Bleed Ocean Wallpaper Background for All Pages */}
      <div 
        className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat transition-all duration-700"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1518837695005-2083093ee35b?q=80&w=2560&auto=format&fit=crop')`,
        }}
      >
        {/* Subtle Dark Ambient Tint to Make Glass Cards Stand Out */}
        <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[2px]" />
      </div>

      {/* Common Glassmorphic Navigation Drawer across all internal pages */}
      <DesktopNav isChatPage={true} />

      {/* Main Content Area */}
      <div className={`relative z-10 w-full h-full ${isChatPage ? 'overflow-hidden' : 'overflow-y-auto pt-16 md:pt-12 px-4 md:px-8 pb-12'}`}>
        <Outlet />
      </div>
    </div>
  );
};

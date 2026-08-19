import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { DesktopNav } from './DesktopNav';
import { BottomNav } from './BottomNav';
import { WebGLBackground } from '../components/common/WebGLBackground';
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
    <div className={`text-on-surface font-body overflow-x-hidden ${isChatPage ? 'h-screen w-screen overflow-hidden' : 'bg-background min-h-screen flex flex-col'}`}>
      {!isChatPage && <WebGLBackground />}
      {!isChatPage && <Header />}
      <DesktopNav isChatPage={isChatPage} />
      <div className={`flex flex-col ${isChatPage ? 'h-full w-full p-0 m-0 overflow-hidden' : 'flex-1 pt-16 md:pl-64 pb-20 md:pb-0'}`}>
        <Outlet />
      </div>
      {!isChatPage && <BottomNav />}
    </div>
  );
};

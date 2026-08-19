import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { DesktopNav } from './DesktopNav';
import { BottomNav } from './BottomNav';
import { WebGLBackground } from '../components/common/WebGLBackground';
import { usePermissionStore } from '../store/permissionStore';

export const AppLayout: React.FC = () => {
  const fetchPending = usePermissionStore((state) => state.fetchPending);

  useEffect(() => {
    fetchPending();
    const interval = setInterval(() => {
      fetchPending();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchPending]);

  return (
    <div className="bg-background text-on-surface font-body overflow-x-hidden min-h-screen flex flex-col">
      <WebGLBackground />
      <Header />
      <DesktopNav />
      <div className="flex-1 flex flex-col pt-16 md:pl-64 pb-20 md:pb-0">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  );
};

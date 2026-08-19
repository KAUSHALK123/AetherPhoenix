import React from 'react';
import { NavLink } from 'react-router-dom';

export const BottomNav: React.FC = () => {
  const navItems = [
    { path: '/chat', icon: 'chat_bubble_outline', label: 'Chat' },
    { path: '/plan', icon: 'event_note', label: 'Plan' },
    { path: '/execution', icon: 'play_circle', label: 'Execution' },
    { path: '/artifacts', icon: 'inventory_2', label: 'Artifacts' },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-around items-center px-4 pb-4 h-16 bg-surface-container-lowest/80 backdrop-blur-lg border-t border-outline-variant/20 z-50">
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center pt-2 transition-all active:scale-95 ${
              isActive ? 'text-primary border-t-2 border-primary' : 'text-on-surface-variant'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <span className={`material-symbols-outlined mb-1 ${isActive ? 'icon-fill' : ''}`}>
                {item.icon}
              </span>
              <span className="text-[10px] font-semibold">{item.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
};

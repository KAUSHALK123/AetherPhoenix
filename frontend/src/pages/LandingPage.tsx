import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const [dragOffsetY, setDragOffsetY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const startYRef = useRef<number>(0);
  const hasDraggedRef = useRef<boolean>(false);

  const handleLaunch = useCallback(() => {
    navigate('/chat');
  }, [navigate]);

  const handleTouchStart = (e: React.TouchEvent) => {
    startYRef.current = e.touches[0].clientY;
    setIsDragging(true);
    hasDraggedRef.current = false;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    const currentY = e.touches[0].clientY;
    const diffY = currentY - startYRef.current;
    if (Math.abs(diffY) > 5) {
      hasDraggedRef.current = true;
    }
    // Only allow pulling upwards (diffY < 0) or slightly downwards with resistance
    setDragOffsetY(diffY < 0 ? diffY : diffY * 0.2);
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
    // If pulled upwards more than 70px, trigger launch transition
    if (dragOffsetY < -70) {
      handleLaunch();
    } else {
      // Snap back
      setDragOffsetY(0);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    startYRef.current = e.clientY;
    setIsDragging(true);
    hasDraggedRef.current = false;
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const diffY = e.clientY - startYRef.current;
      if (Math.abs(diffY) > 5) {
        hasDraggedRef.current = true;
      }
      setDragOffsetY(diffY < 0 ? diffY : diffY * 0.2);
    };

    const handleMouseUp = () => {
      if (!isDragging) return;
      setIsDragging(false);
      if (dragOffsetY < -70) {
        handleLaunch();
      } else {
        setDragOffsetY(0);
      }
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffsetY, handleLaunch]);

  const handleClick = () => {
    if (!hasDraggedRef.current) {
      handleLaunch();
    }
  };

  return (
    <div className="bg-background text-on-surface font-body min-h-screen flex flex-col pb-20 md:pb-0 pt-16">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-surface-deep/80 backdrop-blur-md border-b border-outline-variant/30 flex justify-between items-center px-6 md:px-10 h-16 mx-auto">
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-3 cursor-pointer active:opacity-70"
        >
          <img
            alt="AetherPhoenix Logo"
            className="w-8 h-8 object-contain rounded drop-shadow"
            src="/logo.png"
          />
          <h1 className="text-xl font-bold text-white tracking-tight">AetherPhoenix</h1>
        </div>
        <div
          onClick={() => navigate('/chat')}
          className="flex items-center cursor-pointer active:opacity-70 hover:bg-surface-container-low transition-colors rounded-full p-1"
        >
          <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center border border-outline-variant overflow-hidden">
            <span className="material-symbols-outlined text-on-surface-variant text-[20px]">person</span>
          </div>
        </div>
      </header>

      {/* Main Layout Grid */}
      <div className="flex flex-1 w-full max-w-6xl mx-auto px-4 md:px-8 py-8 gap-8 flex-col">
        {/* Hero Section */}
        <section className="flex flex-col items-center text-center gap-6 py-16 border-b border-outline-variant/30 mb-8 w-full relative bg-cover bg-center rounded-3xl bg-surface-container/20 overflow-hidden">
          <div className="flex flex-col items-center gap-4 max-w-[800px] mx-auto relative z-20 px-4">
            <span className="text-xs uppercase tracking-widest font-extrabold text-accent-electric px-3 py-1 bg-primary/10 rounded-full border border-primary/20">
              Open Source • Runs on your machine
            </span>
            <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-white leading-tight font-serif italic">
              The AI that <span className="text-primary italic font-serif">really</span>{' '}
              <span className="block not-italic font-sans font-extrabold tracking-normal">does things.</span>
            </h1>
            <p className="text-lg md:text-xl text-on-surface-variant max-w-[600px] font-medium leading-relaxed">
              Organizes your inbox, sends emails, manages your calendar, checks you in for flights. All from WhatsApp, Telegram, or any chat app you already use.
            </p>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              <button
                onClick={() => navigate('/chat')}
                className="px-8 py-3 bg-primary text-white rounded-xl font-bold hover:bg-accent-electric transition-all active:scale-95 shadow-[0_0_20px_rgba(168,85,247,0.4)] flex items-center gap-2"
              >
                Get started
                <span className="material-symbols-outlined text-lg">arrow_forward</span>
              </button>
              <button
                onClick={() => navigate('/plan')}
                className="px-8 py-3 border border-outline-variant text-white rounded-xl font-semibold hover:bg-surface-container-low transition-all active:scale-95"
              >
                Read the docs
              </button>
            </div>
          </div>
        </section>

        {/* Content Section */}
        <div className="flex flex-1 gap-8 w-full flex-col xl:flex-row">
          <main className="flex-1 min-w-0 flex flex-col gap-10">
            {/* System Capabilities */}
            <section className="flex flex-col gap-3">
              <h2 className="text-xs text-on-surface-muted uppercase tracking-widest font-bold mb-1">
                System Capabilities
              </h2>
              <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2">
                {[
                  { icon: 'language', label: 'Browser Automation' },
                  { icon: 'desktop_windows', label: 'Desktop Control' },
                  { icon: 'terminal', label: 'CLI Executor' },
                  { icon: 'public', label: 'Web Research' },
                ].map((cap, i) => (
                  <button
                    key={i}
                    onClick={() => navigate('/chat')}
                    className="flex items-center gap-2.5 px-4 py-2.5 bg-surface-container-low border border-outline-variant/40 rounded-full hover:border-primary hover:shadow-[0_4px_16px_rgba(168,85,247,0.15)] transition-all whitespace-nowrap text-white text-sm cursor-pointer group"
                  >
                    <span className="material-symbols-outlined text-primary text-[18px] group-hover:scale-110 transition-transform">
                      {cap.icon}
                    </span>
                    {cap.label}
                  </button>
                ))}
              </div>
            </section>

            {/* Generated Artifacts */}
            <section className="flex flex-col gap-4">
              <div className="flex justify-between items-center mb-1">
                <h2 className="text-2xl font-bold text-white tracking-tight">Generated Artifacts</h2>
                <div className="flex gap-1">
                  <button className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors">
                    <span className="material-symbols-outlined text-[20px]">filter_list</span>
                  </button>
                  <button className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors">
                    <span className="material-symbols-outlined text-[20px]">grid_view</span>
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Artifact Card 1: PPTX */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-surface-container-low border border-outline-variant/40 rounded-2xl overflow-hidden flex flex-col hover:border-primary transition-all cursor-pointer shadow-sm hover:shadow-[0_4px_20px_rgba(168,85,247,0.2)]"
                >
                  <div className="h-32 bg-surface-container relative overflow-hidden border-b border-outline-variant/30 flex items-center justify-center">
                    <span className="material-symbols-outlined text-[48px] text-accent-electric opacity-40 group-hover:scale-110 transition-transform duration-500">
                      co_present
                    </span>
                    <div className="absolute top-3 right-3 bg-surface-deep/90 rounded-md px-2 py-0.5 flex items-center gap-1 shadow-sm border border-outline-variant/50">
                      <span className="material-symbols-outlined text-[14px] text-primary">co_present</span>
                      <span className="text-xs font-bold text-primary">PPTX</span>
                    </div>
                  </div>
                  <div className="p-4 flex flex-col gap-2 flex-1">
                    <h3 className="text-base font-bold text-white line-clamp-1">Q3 AI Strategy Overview</h3>
                    <p className="text-xs text-on-surface-muted line-clamp-2">
                      Comprehensive breakdown of Q3 generative AI integration plans across core product lines.
                    </p>
                    <div className="mt-auto pt-2 flex justify-between items-center text-on-surface-muted text-xs">
                      <span>Today, 10:42 AM</span>
                      <span className="material-symbols-outlined text-[16px] hover:text-primary transition-colors">
                        more_horiz
                      </span>
                    </div>
                  </div>
                </div>

                {/* Artifact Card 2: PDF */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-surface-container-low border border-outline-variant/40 rounded-2xl overflow-hidden flex flex-col hover:border-primary transition-all cursor-pointer shadow-sm hover:shadow-[0_4px_20px_rgba(168,85,247,0.2)]"
                >
                  <div className="h-32 bg-surface-container relative overflow-hidden border-b border-outline-variant/30 flex items-center justify-center">
                    <span className="material-symbols-outlined text-[48px] text-primary opacity-40 group-hover:scale-110 transition-transform duration-500">
                      picture_as_pdf
                    </span>
                    <div className="absolute top-3 right-3 bg-surface-deep/90 rounded-md px-2 py-0.5 flex items-center gap-1 shadow-sm border border-outline-variant/50">
                      <span className="material-symbols-outlined text-[14px] text-primary">picture_as_pdf</span>
                      <span className="text-xs font-bold text-primary">PDF</span>
                    </div>
                  </div>
                  <div className="p-4 flex flex-col gap-2 flex-1">
                    <h3 className="text-base font-bold text-white line-clamp-1">Market Analysis Report</h3>
                    <p className="text-xs text-on-surface-muted line-clamp-2">
                      Detailed synthetic research combining 15 distinct competitor web scraping runs.
                    </p>
                    <div className="mt-auto pt-2 flex justify-between items-center text-on-surface-muted text-xs">
                      <span>Yesterday</span>
                      <span className="material-symbols-outlined text-[16px] hover:text-primary transition-colors">
                        more_horiz
                      </span>
                    </div>
                  </div>
                </div>

                {/* Artifact Card 3: CSV */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-surface-container-low border border-outline-variant/40 rounded-2xl overflow-hidden flex flex-col hover:border-primary transition-all cursor-pointer shadow-sm hover:shadow-[0_4px_20px_rgba(168,85,247,0.2)]"
                >
                  <div className="h-32 bg-surface-container relative overflow-hidden border-b border-outline-variant/30 flex items-center justify-center">
                    <span className="material-symbols-outlined text-[48px] text-accent-electric opacity-40 group-hover:scale-110 transition-transform duration-500">
                      table_chart
                    </span>
                    <div className="absolute top-3 right-3 bg-surface-deep/90 rounded-md px-2 py-0.5 flex items-center gap-1 shadow-sm border border-outline-variant/50">
                      <span className="material-symbols-outlined text-[14px] text-primary">table_chart</span>
                      <span className="text-xs font-bold text-primary">CSV</span>
                    </div>
                  </div>
                  <div className="p-4 flex flex-col gap-2 flex-1">
                    <h3 className="text-base font-bold text-white line-clamp-1">User Engagement Metrics</h3>
                    <p className="text-xs text-on-surface-muted line-clamp-2">
                      Cleaned and formatted extract of telemetry data for the past 30 days.
                    </p>
                    <div className="mt-auto pt-2 flex justify-between items-center text-on-surface-muted text-xs">
                      <span>Oct 12, 2023</span>
                      <span className="material-symbols-outlined text-[16px] hover:text-primary transition-colors">
                        more_horiz
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </main>

          {/* Context Memory Aside */}
          <aside className="xl:flex flex-col w-full xl:w-[320px] bg-surface-container-low border border-outline-variant/40 rounded-2xl p-6 shadow-sm h-fit sticky top-[88px]">
            <div className="flex items-center gap-2 mb-6 border-b border-outline-variant/30 pb-4">
              <span className="material-symbols-outlined text-primary text-[20px]">history</span>
              <h3 className="text-lg font-bold text-white">Context Memory</h3>
            </div>
            <div className="flex flex-col gap-6 relative before:absolute before:inset-y-0 before:left-[11px] before:w-px before:bg-outline-variant/40">
              <div className="flex gap-4 relative">
                <div className="w-6 h-6 rounded-full bg-surface-deep border-2 border-primary flex items-center justify-center z-10 shrink-0 mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-primary" />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold text-on-surface-muted">Just Now</span>
                  <p className="text-sm text-white">
                    Generated <span className="text-primary font-semibold">Q3 AI Strategy</span> presentation.
                  </p>
                </div>
              </div>
              <div className="flex gap-4 relative">
                <div className="w-6 h-6 rounded-full bg-surface-deep border-2 border-outline-variant flex items-center justify-center z-10 shrink-0 mt-0.5" />
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold text-on-surface-muted">2 hours ago</span>
                  <p className="text-sm text-white">
                    Extracted key metrics into <span className="text-primary font-semibold">CSV</span>.
                  </p>
                </div>
              </div>
            </div>
            <button
              onClick={() => navigate('/artifacts')}
              className="mt-6 pt-4 border-t border-outline-variant/30 text-center w-full text-xs font-bold text-on-surface-muted hover:text-primary transition-colors cursor-pointer"
            >
              View Full Logs
            </button>
          </aside>
        </div>

      </div>

      {/* Full-Width Sticky Pull-Up Drawer */}
      <div
        className="w-full mt-auto sticky bottom-0 left-0 right-0 z-40 select-none transition-transform duration-300 ease-out"
        style={{
          transform: `translateY(${Math.min(0, dragOffsetY)}px)`,
        }}
      >
        <div
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onClick={handleClick}
          className={`w-full py-8 px-6 flex flex-col items-center justify-center text-center relative border-t border-outline-variant/40 rounded-t-[50px] bg-gradient-to-b from-[#1c1a24] via-[#14121b] to-[#0D0B14] shadow-[0_-10px_40px_rgba(0,0,0,0.6)] cursor-grab active:cursor-grabbing hover:border-primary/50 transition-colors ${
            isDragging ? 'cursor-grabbing' : ''
          }`}
        >
          {/* Subtle Pull-Up Indicator Bar */}
          <div className="w-12 h-1.5 bg-outline-variant/60 hover:bg-primary/80 rounded-full mb-4 transition-colors animate-pulse" />

          <div className="group flex flex-col items-center gap-3 transition-transform duration-300 hover:scale-105 active:scale-95">
            <div className="w-20 h-20 rounded-full bg-surface-deep border-2 border-primary/40 flex items-center justify-center shadow-[0_0_30px_rgba(168,85,247,0.3)] group-hover:border-primary group-hover:shadow-[0_0_45px_rgba(168,85,247,0.7)] transition-all">
              <img
                src="/logo.png"
                alt="AetherPhoenix"
                className="w-14 h-14 object-contain pointer-events-none drop-shadow"
              />
            </div>
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-primary group-hover:text-accent-electric transition-colors">
              <span className="material-symbols-outlined text-sm animate-bounce">keyboard_arrow_up</span>
              <span>LAUNCH AGENT ASSISTANT</span>
              <span className="material-symbols-outlined text-sm animate-bounce">keyboard_arrow_up</span>
            </div>
            <span className="text-[10px] text-on-surface-muted">Pull up or click to launch</span>
          </div>
        </div>
      </div>
    </div>
  );
};

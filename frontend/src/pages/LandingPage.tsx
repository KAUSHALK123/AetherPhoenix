import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const [dragOffsetY, setDragOffsetY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [showDrawer, setShowDrawer] = useState(false);
  const [ringAngle, setRingAngle] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);
  
  const [activeNav, setActiveNav] = useState('home');
  
  const startYRef = useRef<number>(0);
  const hasDraggedRef = useRef<boolean>(false);
  const targetAngleRef = useRef<number>(0);
  const currentAngleRef = useRef<number>(0);
  const lastScrollYRef = useRef<number>(0);

  const handleLaunch = useCallback(() => {
    navigate('/chat');
  }, [navigate]);

  const handleNavChange = (option: string, pathOrUrl: string, isExternal: boolean = false) => {
    setActiveNav(option);
    if (isExternal) {
      setTimeout(() => {
        window.open(pathOrUrl, '_blank');
        setActiveNav('home');
      }, 250);
    } else {
      setTimeout(() => {
        navigate(pathOrUrl);
      }, 250);
    }
  };

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

  // Concentric Rings Scroll-driven rotation with smooth Lerp interpolation
  useEffect(() => {
    let animFrameId: number;
    const ROTATION_SPEED = 0.35;

    const onScroll = () => {
      const currentScroll = window.scrollY;
      const delta = currentScroll - lastScrollYRef.current;
      lastScrollYRef.current = currentScroll;
      targetAngleRef.current += delta * ROTATION_SPEED;

      // Calculate scroll progress (0 to 1 over first 250px of scroll)
      const progress = Math.min(1, Math.max(0, currentScroll / 250));
      setScrollProgress(progress);

      // Also trigger drawer visibility check
      const isAtBottom =
        window.innerHeight + window.scrollY >=
        document.documentElement.scrollHeight - 40;
      setShowDrawer(isAtBottom);
    };

    window.addEventListener('scroll', onScroll, { passive: true });

    const renderRings = () => {
      currentAngleRef.current += (targetAngleRef.current - currentAngleRef.current) * 0.08;
      setRingAngle(currentAngleRef.current);
      animFrameId = requestAnimationFrame(renderRings);
    };

    animFrameId = requestAnimationFrame(renderRings);

    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(animFrameId);
    };
  }, []);

  const handleClick = () => {
    if (!hasDraggedRef.current) {
      handleLaunch();
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 font-sans antialiased min-h-screen flex flex-col selection:bg-indigo-500 selection:text-white pb-24">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/95 border-b border-slate-200/80 px-6 h-20 flex items-center justify-between shadow-sm shadow-slate-100/10">
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-3 cursor-pointer group flex-1"
        >
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 p-[1.5px] shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center overflow-hidden">
              <img
                src="/logo.png"
                alt="AetherPhoenix Logo"
                className="w-10 h-10 object-contain pointer-events-none drop-shadow"
              />
            </div>
          </div>
          <span className="font-black text-xl tracking-tight bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
            AetherPhoenix
          </span>
        </div>

        {/* Center Navigation Links (Styled Sliding Radio Group - Dead Center Centered) */}
        <div className="hidden md:flex nav-radio-group">
          <div className="nav-slider" />
          
          <div className="nav-radio-option">
            <input
              type="radio"
              id="nav-home"
              name="nav-group"
              checked={activeNav === 'home'}
              onChange={() => handleNavChange('home', '/')}
            />
            <label htmlFor="nav-home" className="nav-radio-label">
              Home
            </label>
          </div>

          <div className="nav-radio-option">
            <input
              type="radio"
              id="nav-architecture"
              name="nav-group"
              checked={activeNav === 'architecture'}
              onChange={() => handleNavChange('architecture', 'https://github.com/KAUSHALK123/AetherPhoenix/tree/develop/PRD/03_SYSTEM_ARCHITECTURE', true)}
            />
            <label htmlFor="nav-architecture" className="nav-radio-label">
              Architecture
            </label>
          </div>

          <div className="nav-radio-option">
            <input
              type="radio"
              id="nav-docs"
              name="nav-group"
              checked={activeNav === 'docs'}
              onChange={() => handleNavChange('docs', '/plan')}
            />
            <label htmlFor="nav-docs" className="nav-radio-label">
              Docs
            </label>
          </div>

          <div className="nav-radio-option">
            <input
              type="radio"
              id="nav-github"
              name="nav-group"
              checked={activeNav === 'github'}
              onChange={() => handleNavChange('github', 'https://github.com/KAUSHALK123/AetherPhoenix', true)}
            />
            <label htmlFor="nav-github" className="nav-radio-label">
              GitHub
            </label>
          </div>
        </div>

        {/* Right Profile Section */}
        <div className="flex items-center justify-end gap-3 flex-1">
          <button
            onClick={() => navigate('/settings')}
            className="w-9 h-9 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center hover:border-slate-300 hover:bg-slate-100 transition-colors"
          >
            <span className="material-symbols-outlined text-slate-600 text-xl">person</span>
          </button>
        </div>
      </header>

      {/* Hero Banner with Concentric Rotating Rings & Mandala Emblem */}
      <section className="relative overflow-hidden border-b border-slate-200 bg-white py-12 md:py-16 px-6">
        <div className="max-w-5xl mx-auto text-center relative z-10 space-y-6 flex flex-col items-center">
          
          {/* Concentric Rotating Rings Assembly (Expanded Giant Scale) */}
          <div className="relative w-[380px] h-[380px] md:w-[480px] md:h-[480px] flex items-center justify-center mx-auto my-0 select-none pointer-events-none">
            {/* Center Static Emblem / Logo (Enlarged to 300px) */}
            <div className="absolute w-52 h-52 md:w-76 md:h-76 z-20 rounded-full bg-white border-2 border-slate-200/90 flex items-center justify-center p-4 shadow-2xl shadow-black/25 pointer-events-auto">
              <img
                src="/logo.png"
                alt="AetherPhoenix Logo"
                className="w-40 h-40 md:w-60 md:h-60 object-contain drop-shadow-md"
              />
            </div>

            {/* Inner Rotating Ring SVG (Enlarged to 800px) */}
            <div
              className="absolute w-[560px] h-[560px] md:w-[800px] md:h-[800px] z-10 pointer-events-none transition-transform duration-75 ease-out"
              style={{
                transform: `rotate(${ringAngle}deg)`,
              }}
            >
              <svg viewBox="0 0 300 300" className="w-full h-full drop-shadow-md">
                <circle cx="150" cy="150" r="140" fill="none" stroke="#2e303d" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.6"/>
                <circle cx="150" cy="150" r="80" fill="none" stroke="#2e303d" strokeWidth="1.5" opacity="0.5"/>
                <g>
                  {Array.from({ length: 12 }).map((_, i) => {
                    const angle = (360 / 12) * i;
                    const chevronWidth = (140 - 80) * 0.35;
                    return (
                      <g key={i} transform={`rotate(${angle} 150 150)`}>
                        <path
                          d={`M 150 ${150 - 140} L ${150 + chevronWidth} ${150 - 80} L 150 ${150 - 80 + chevronWidth * 0.7} L ${150 - chevronWidth} ${150 - 80} Z`}
                          fill="#16171d"
                          stroke="#050507"
                          strokeWidth="1.5"
                        />
                      </g>
                    );
                  })}
                </g>
              </svg>
            </div>

            {/* Outer Counter-Rotating Ring SVG (Enlarged to 1150px) */}
            <div
              className="absolute w-[760px] h-[760px] md:w-[1150px] md:h-[1150px] z-0 pointer-events-none transition-transform duration-75 ease-out"
              style={{
                transform: `rotate(${-ringAngle * 0.75}deg)`,
              }}
            >
              <svg viewBox="0 0 460 460" className="w-full h-full drop-shadow-2xl">
                <circle cx="230" cy="230" r="220" fill="none" stroke="#2e303d" strokeWidth="1.5" opacity="0.6"/>
                <circle cx="230" cy="230" r="158" fill="none" stroke="#2e303d" strokeWidth="1.5" strokeDasharray="5 5" opacity="0.5"/>
                <g>
                  {Array.from({ length: 18 }).map((_, i) => {
                    const angle = (360 / 18) * i;
                    const chevronWidth = (220 - 158) * 0.35;
                    return (
                      <g key={i} transform={`rotate(${angle} 230 230)`}>
                        <path
                          d={`M 230 ${230 - 220} L ${230 + chevronWidth} ${230 - 158} L 230 ${230 - 158 + chevronWidth * 0.7} L ${230 - chevronWidth} ${230 - 158} Z`}
                          fill="#101116"
                          stroke="#050507"
                          strokeWidth="1.5"
                        />
                      </g>
                    );
                  })}
                </g>
              </svg>
            </div>
          </div>
          {/* Hero Text with dynamic dark gradient overlay on scroll */}
          <div className="relative z-30 max-w-3xl mx-auto px-6 py-6 rounded-3xl transition-all duration-300 space-y-6">
            {/* Dynamic Dark Gradient Backdrop (Fades in opacity on scroll to make text pop) */}
            <div
              className="absolute inset-0 rounded-3xl pointer-events-none transition-opacity duration-200"
              style={{
                background: 'radial-gradient(ellipse at center, rgba(15, 23, 42, 0.88) 0%, rgba(2, 6, 23, 0.7) 60%, transparent 100%)',
                backdropFilter: scrollProgress > 0.1 ? `blur(${scrollProgress * 12}px)` : 'none',
                opacity: Math.min(1, scrollProgress * 1.3),
              }}
            />

            <div className="relative z-10 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100/90 border border-slate-200 text-slate-700 text-xs font-semibold backdrop-blur-md shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span>
                Open Source • Runs on your machine
              </div>

              <h1
                className={`text-5xl sm:text-7xl font-extrabold tracking-tight leading-tight transition-colors duration-200 drop-shadow-sm ${
                  scrollProgress > 0.2 ? 'text-white' : 'text-slate-900'
                }`}
              >
                The AI that{' '}
                <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-indigo-300 bg-clip-text text-transparent italic drop-shadow">
                  really
                </span>{' '}
                does things.
              </h1>

              <p
                className={`text-base sm:text-lg max-w-2xl mx-auto font-medium leading-relaxed transition-colors duration-200 ${
                  scrollProgress > 0.2 ? 'text-slate-200 drop-shadow' : 'text-slate-600'
                }`}
              >
                Organizes your inbox, sends emails, manages your calendar, checks you in for flights. All from WhatsApp, Telegram, or any chat app you already use.
              </p>

              <div className="flex items-center justify-center gap-3 pt-2">
                <button
                  onClick={() => navigate('/chat')}
                  className="px-6 py-2.5 bg-[#2f70d9] hover:bg-blue-600 text-white rounded-xl font-semibold text-sm transition-all shadow-lg shadow-blue-500/25 active:scale-95 cursor-pointer"
                >
                  Get started
                </button>
                <button
                  onClick={() => navigate('/plan')}
                  className="px-6 py-2.5 bg-white/10 hover:bg-white/20 text-blue-600 hover:text-blue-500 border border-blue-200/80 rounded-xl font-semibold text-sm transition-all active:scale-95 cursor-pointer backdrop-blur-md"
                >
                  Read the docs
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Layout (Full Width Grid without Context Memory) */}
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 w-full flex-1">
        <div className="space-y-12">
          {/* Main Feed */}
          <main className="space-y-12">
            {/* System Capabilities Chips */}
            <section className="space-y-3">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                System Capabilities
              </h2>
              <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group cursor-pointer"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    language
                  </span>{' '}
                  Browser Automation
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group cursor-pointer"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    desktop_windows
                  </span>{' '}
                  Desktop Control
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group cursor-pointer"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    terminal
                  </span>{' '}
                  CLI Executor
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group cursor-pointer"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    travel_explore
                  </span>{' '}
                  Web Research
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group cursor-pointer"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    co_present
                  </span>{' '}
                  PowerPoint Generator
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group cursor-pointer"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    picture_as_pdf
                  </span>{' '}
                  PDF Generator
                </button>
              </div>
            </section>

            {/* PINWHEEL FEATURE GRID SECTION (Full Cover Bright Images) */}
            <section className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">Project Capabilities & Features</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Core system architecture and operational highlights</p>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono">3x3 Feature Mosaic</span>
              </div>

              {/* Pinwheel Layout Container */}
              <div className="grid grid-cols-1 md:grid-cols-3 md:grid-rows-3 gap-5 auto-rows-[230px] w-full">
                
                {/* Item 1: Left Vertical Card (Planner Engine) */}
                <div 
                  onClick={() => navigate('/chat')}
                  className="md:row-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-indigo-500/60 hover:shadow-2xl hover:shadow-indigo-500/20 cursor-pointer"
                >
                  {/* Full Cover Bright Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop" alt="Planner Architecture" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/20"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-indigo-500/30 border border-indigo-500/40 text-indigo-200 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">PLANNER ENGINE</span>
                    <span className="material-symbols-outlined text-slate-300 group-hover:text-indigo-400 group-hover:scale-110 transition-all">account_tree</span>
                  </div>

                  <div className="relative z-10 space-y-1.5">
                    <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors">Hierarchical Goal Planner</h3>
                    <p className="text-xs text-slate-200 leading-relaxed font-medium">Decomposes user prompts into structured execution plans with dependencies, execution contracts, and permissions.</p>
                  </div>
                </div>

                {/* Item 2: Top Horizontal Card (Worker Execution Engine) */}
                <div 
                  onClick={() => navigate('/execution')}
                  className="md:col-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-cyan-500/60 hover:shadow-2xl hover:shadow-cyan-500/20 cursor-pointer"
                >
                  {/* Full Cover Bright Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=800&auto=format&fit=crop" alt="Worker Telemetry" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/20"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-cyan-500/30 border border-cyan-500/40 text-cyan-200 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">WORKER EXECUTION ENGINE</span>
                    <span className="material-symbols-outlined text-slate-300 group-hover:text-cyan-400 group-hover:scale-110 transition-all">terminal</span>
                  </div>

                  <div className="relative z-10 space-y-1.5 max-w-lg">
                    <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">Multi-Tool Execution System</h3>
                    <p className="text-xs text-slate-200 leading-relaxed font-medium">Performs real task execution across browser automation, desktop control, web research, PDF parsing, and custom PPTX slides generation.</p>
                  </div>
                </div>

                {/* Item 3: Center Accent Card (RAG Semantic Agent) */}
                <div 
                  onClick={() => navigate('/plan')}
                  className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-5 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:scale-[1.02] hover:border-rose-500/60 hover:shadow-2xl hover:shadow-rose-500/20 cursor-pointer"
                >
                  {/* Full Cover Bright Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=800&auto=format&fit=crop" alt="RAG Memory" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/20"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded bg-rose-500/30 border border-rose-500/40 text-rose-200 text-[9px] font-semibold font-mono backdrop-blur-md">PERSISTENT MEMORY</span>
                    <span className="material-symbols-outlined text-slate-300 group-hover:text-rose-400 group-hover:scale-110 transition-all">neurology</span>
                  </div>

                  <div className="relative z-10 space-y-1">
                    <h3 className="text-sm font-bold text-white group-hover:text-rose-300 transition-colors">RAG Semantic Agent</h3>
                    <p className="text-[11px] text-slate-200 font-mono">Vector Search + LLM</p>
                  </div>
                </div>

                {/* Item 4: Right Vertical Card (Supervisor Monitor) */}
                <div 
                  onClick={() => navigate('/execution')}
                  className="md:row-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-purple-500/60 hover:shadow-2xl hover:shadow-purple-500/20 cursor-pointer"
                >
                  {/* Full Cover Bright Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=800&auto=format&fit=crop" alt="Supervisor View" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/20"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-purple-500/30 border border-purple-500/40 text-purple-200 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">SUPERVISOR ENGINE</span>
                    <span className="material-symbols-outlined text-slate-300 group-hover:text-purple-400 group-hover:scale-110 transition-all">visibility</span>
                  </div>

                  <div className="relative z-10 space-y-1.5">
                    <h3 className="text-lg font-bold text-white group-hover:text-purple-300 transition-colors">Real-time Pipeline Supervisor</h3>
                    <p className="text-xs text-slate-200 leading-relaxed font-medium">Monitors the running state, tracks task progress, validates results, and dispatches state updates across the EventBus.</p>
                  </div>
                </div>

                {/* Item 5: Bottom Horizontal Card (Healing Controller) */}
                <div 
                  onClick={() => navigate('/plan')}
                  className="md:col-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-emerald-500/60 hover:shadow-2xl hover:shadow-emerald-500/20 cursor-pointer"
                >
                  {/* Full Cover Bright Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=800&auto=format&fit=crop" alt="Self-Healing Architecture" className="w-full h-full object-cover opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/20"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-emerald-500/30 border border-emerald-500/40 text-emerald-200 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">HEALING CONTROLLER</span>
                    <span className="material-symbols-outlined text-slate-300 group-hover:text-emerald-400 group-hover:scale-110 transition-all">healing</span>
                  </div>

                  <div className="relative z-10 space-y-1.5 max-w-lg">
                    <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors">Resilient Self-Healing Engine</h3>
                    <p className="text-xs text-slate-200 leading-relaxed font-medium">Synthesizes root-cause analyses for runtime failures and executes autonomous healing strategies to repair broken tasks without user intervention.</p>
                  </div>
                </div>

              </div>
            </section>

            {/* Artifacts Grid */}
            <section className="space-y-4 pt-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white tracking-tight">Generated Artifacts</h2>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => navigate('/artifacts')}
                    className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900 transition-colors cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-xl">filter_list</span>
                  </button>
                  <button
                    onClick={() => navigate('/artifacts')}
                    className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900 transition-colors cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-xl">grid_view</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Card 1 */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-5 transition-all duration-300 cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-semibold tracking-wide uppercase font-mono">
                        PPTX
                      </span>
                      <span className="material-symbols-outlined text-slate-500 group-hover:text-slate-300 text-lg transition-colors">
                        more_horiz
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                        EV_Comprehensive_Presentation.pptx
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        Comprehensive 5-slide breakdown of Electric Vehicles market dynamics and battery tech.
                      </p>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium pt-2 border-t border-slate-800/60 font-mono">
                    5 slides • 41 KB • Updated today
                  </div>
                </div>

                {/* Card 2 */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-5 transition-all duration-300 cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-semibold tracking-wide uppercase font-mono">
                        PDF
                      </span>
                      <span className="material-symbols-outlined text-slate-500 group-hover:text-slate-300 text-lg transition-colors">
                        more_horiz
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                        Market_Analysis_Report.pdf
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        Detailed research document combining 15 distinct competitor web scraping runs.
                      </p>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium pt-2 border-t border-slate-800/60 font-mono">
                    8 pages • 240 KB • Updated yesterday
                  </div>
                </div>

                {/* Card 3 */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-5 transition-all duration-300 cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-semibold tracking-wide uppercase font-mono">
                        CSV
                      </span>
                      <span className="material-symbols-outlined text-slate-500 group-hover:text-slate-300 text-lg transition-colors">
                        more_horiz
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                        Telemetry_Extraction_Log.csv
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        Cleaned and formatted extract of telemetry data for the past 30 days.
                      </p>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium pt-2 border-t border-slate-800/60 font-mono">
                    142 rows • 38 KB • Updated Oct 12
                  </div>
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>

      {/* Full-Width Sticky Pull-Up Drawer - Only shown when scrolled to bottom */}
      <div
        className={`w-full fixed bottom-0 left-0 right-0 z-40 select-none transition-transform duration-500 ease-in-out ${
          showDrawer ? 'translate-y-0 opacity-100' : 'translate-y-[80%] opacity-0 pointer-events-none'
        }`}
        style={{
          transform: showDrawer ? `translateY(${Math.min(0, dragOffsetY)}px)` : 'translateY(100%)',
        }}
      >
        <div
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onClick={handleClick}
          className={`w-full py-5 px-6 flex flex-col items-center justify-center text-center relative border-t border-slate-800/80 rounded-t-[40px] bg-gradient-to-b from-slate-900 to-slate-950 shadow-[0_-10px_40px_rgba(0,0,0,0.6)] cursor-grab active:cursor-grabbing hover:border-indigo-500/50 transition-colors ${
            isDragging ? 'cursor-grabbing' : ''
          }`}
        >
          {/* Subtle Pull-Up Indicator Bar */}
          <div className="w-10 h-1 bg-slate-700/60 hover:bg-indigo-500/80 rounded-full mb-3 transition-colors animate-pulse" />

          <div className="group flex flex-col items-center gap-2 transition-transform duration-300 hover:scale-105 active:scale-95">
            <div className="w-14 h-14 rounded-full bg-slate-950 border-2 border-indigo-500/40 flex items-center justify-center shadow-[0_0_25px_rgba(168,85,247,0.3)] group-hover:border-indigo-500 group-hover:shadow-[0_0_35px_rgba(168,85,247,0.7)] transition-all">
              <img
                src="/logo.png"
                alt="AetherPhoenix Logo"
                className="w-10 h-10 object-contain pointer-events-none drop-shadow"
              />
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-widest text-indigo-400 group-hover:text-indigo-300 transition-colors">
              <span className="material-symbols-outlined text-xs animate-bounce">keyboard_arrow_up</span>
              <span>LAUNCH AGENT ASSISTANT</span>
              <span className="material-symbols-outlined text-xs animate-bounce">keyboard_arrow_up</span>
            </div>
            <span className="text-[9px] text-slate-500">Pull up or click to launch</span>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Bar */}
      <nav className="md:hidden sticky bottom-0 w-full backdrop-blur-xl bg-slate-950/90 border-t border-slate-800 px-6 py-2 flex justify-around items-center z-50">
        <a
          onClick={() => navigate('/chat')}
          className="flex flex-col items-center gap-1 text-slate-500 hover:text-slate-200 cursor-pointer"
        >
          <span className="material-symbols-outlined text-xl">chat_bubble</span>
          <span className="text-[10px] font-medium">Chat</span>
        </a>
        <a
          onClick={() => navigate('/plan')}
          className="flex flex-col items-center gap-1 text-slate-500 hover:text-slate-200 cursor-pointer"
        >
          <span className="material-symbols-outlined text-xl">event_note</span>
          <span className="text-[10px] font-medium">Plan</span>
        </a>
        <a
          onClick={() => navigate('/execution')}
          className="flex flex-col items-center gap-1 text-slate-500 hover:text-slate-200 cursor-pointer"
        >
          <span className="material-symbols-outlined text-xl">terminal</span>
          <span className="text-[10px] font-medium">Execution</span>
        </a>
        <a
          onClick={() => navigate('/artifacts')}
          className="flex flex-col items-center gap-1 text-indigo-400 cursor-pointer"
        >
          <span className="material-symbols-outlined text-xl">inventory_2</span>
          <span className="text-[10px] font-medium">Artifacts</span>
        </a>
      </nav>
    </div>
  );
};

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const [dragOffsetY, setDragOffsetY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [showDrawer, setShowDrawer] = useState(false);
  
  const [activeNav, setActiveNav] = useState('home');
  
  const startYRef = useRef<number>(0);
  const hasDraggedRef = useRef<boolean>(false);

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

  // Scroll to bottom listener to show/hide the pull-up drawer
  useEffect(() => {
    const handleScroll = () => {
      const isAtBottom =
        window.innerHeight + window.scrollY >=
        document.documentElement.scrollHeight - 120;
      setShowDrawer(isAtBottom);
    };

    window.addEventListener('scroll', handleScroll);
    // Verify initially if document height is smaller than screen
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleClick = () => {
    if (!hasDraggedRef.current) {
      handleLaunch();
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 font-sans antialiased min-h-screen flex flex-col selection:bg-indigo-500 selection:text-white pb-24">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/95 border-b border-slate-200/80 px-6 h-16 flex items-center justify-between shadow-sm shadow-slate-100/10">
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-3 cursor-pointer group flex-1"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 p-[1px] shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <div className="w-full h-full bg-white rounded-[11px] flex items-center justify-center overflow-hidden">
              <img
                src="/logo.png"
                alt="AetherPhoenix Logo"
                className="w-6 h-6 object-contain pointer-events-none drop-shadow"
              />
            </div>
          </div>
          <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
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

      {/* Hero Banner (White Theme with Mandala Watermark and Masked Loader Text) */}
      <section className="relative overflow-hidden border-b border-slate-200 bg-white py-24 md:py-32 px-6">
        {/* Background Snowflake Mandala Graphic (As per user uploads) */}
        <div className="absolute inset-0 z-0 flex items-center justify-center overflow-hidden opacity-[0.9] pointer-events-none">
          <img
            src="/snowflake.png"
            alt="Snowflake Mandala"
            className="w-[450px] h-[450px] md:w-[600px] md:h-[600px] object-contain"
          />
        </div>

        {/* Loader Text Animation behind Main Text */}
        <div className="absolute top-[40%] left-[50%] -translate-x-[50%] -translate-y-[50%] z-0 pointer-events-none opacity-[0.15]">
          <div className="loader-wrapper">
            <div className="loader"></div>
            {"AUTOMATION".split("").map((letter, index) => (
              <span key={index} className="loader-letter">{letter}</span>
            ))}
          </div>
        </div>

        <div className="max-w-5xl mx-auto text-center relative z-10 space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold backdrop-blur-md">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span>
            Open Source • Runs on your machine
          </div>

          <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-slate-900 leading-tight">
            The AI that{' '}
            <span className="bg-gradient-to-r from-indigo-600 via-violet-500 to-indigo-600 bg-clip-text text-transparent italic">
              really
            </span>{' '}
            does things.
          </h1>

          <p className="text-slate-600 text-base sm:text-lg max-w-2xl mx-auto font-medium leading-relaxed">
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
              className="px-6 py-2.5 bg-transparent hover:bg-slate-50 text-[#2f70d9] border border-blue-200 rounded-xl font-semibold text-sm transition-all active:scale-95 cursor-pointer"
            >
              Read the docs
            </button>
          </div>
        </div>
      </section>

      {/* Main Content Layout (Increased Sizing to 2xl & Padding) */}
      <div className="max-w-screen-2xl mx-auto px-6 md:px-10 py-16 w-full flex-1">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Main Feed */}
          <main className="lg:col-span-3 space-y-10">
            {/* System Capabilities Chips */}
            <section className="space-y-3">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                System Capabilities
              </h2>
              <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    language
                  </span>{' '}
                  Browser Automation
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    desktop_windows
                  </span>{' '}
                  Desktop Control
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    terminal
                  </span>{' '}
                  CLI Executor
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-medium text-slate-300 transition-all whitespace-nowrap group"
                >
                  <span className="material-symbols-outlined text-indigo-400 text-lg group-hover:scale-110 transition-transform">
                    travel_explore
                  </span>{' '}
                  Web Research
                </button>
              </div>
            </section>

            {/* PINWHEEL FEATURE GRID SECTION (Full Cover Images with Smooth Scale & Hover Lift) */}
            <section className="space-y-4 pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">Project Capabilities & Features</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Core system architecture and operational highlights</p>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono">3x3 Feature Mosaic</span>
              </div>

              {/* Pinwheel Layout Container */}
              <div className="grid grid-cols-1 md:grid-cols-3 md:grid-rows-3 gap-4 auto-rows-[220px]">
                
                {/* Item 1: Left Vertical Card (Planner Engine) */}
                <div 
                  onClick={() => navigate('/chat')}
                  className="md:row-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-indigo-500/60 hover:shadow-2xl hover:shadow-indigo-500/20 cursor-pointer"
                >
                  {/* Full Cover Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop" alt="Planner Architecture" className="w-full h-full object-cover opacity-40 group-hover:opacity-75 group-hover:scale-110 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-slate-950/30"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">PLANNER ENGINE</span>
                    <span className="material-symbols-outlined text-slate-400 group-hover:text-indigo-400 group-hover:scale-110 transition-all">account_tree</span>
                  </div>

                  <div className="relative z-10 space-y-1.5">
                    <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors">Hierarchical Goal Planner</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">Decomposes user prompts into structured execution plans with dependencies, execution contracts, and permissions.</p>
                  </div>
                </div>

                {/* Item 2: Top Horizontal Card (Worker Execution Engine) */}
                <div 
                  onClick={() => navigate('/execution')}
                  className="md:col-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-cyan-500/60 hover:shadow-2xl hover:shadow-cyan-500/20 cursor-pointer"
                >
                  {/* Full Cover Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=800&auto=format&fit=crop" alt="Worker Telemetry" className="w-full h-full object-cover opacity-40 group-hover:opacity-75 group-hover:scale-110 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-slate-950/30"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">WORKER EXECUTION ENGINE</span>
                    <span className="material-symbols-outlined text-slate-400 group-hover:text-cyan-400 group-hover:scale-110 transition-all">terminal</span>
                  </div>

                  <div className="relative z-10 space-y-1.5 max-w-lg">
                    <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">Multi-Tool Execution System</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">Performs real task execution across browser automation, desktop control, web research, PDF parsing, and custom PPTX slides generation.</p>
                  </div>
                </div>

                {/* Item 3: Center Accent Card (RAG Semantic Agent) */}
                <div 
                  onClick={() => navigate('/plan')}
                  className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-5 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:scale-[1.02] hover:border-rose-500/60 hover:shadow-2xl hover:shadow-rose-500/20 cursor-pointer"
                >
                  {/* Full Cover Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=800&auto=format&fit=crop" alt="RAG Memory" className="w-full h-full object-cover opacity-40 group-hover:opacity-75 group-hover:scale-110 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-slate-950/20"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 text-[9px] font-semibold font-mono backdrop-blur-md">PERSISTENT MEMORY</span>
                    <span className="material-symbols-outlined text-slate-400 group-hover:text-rose-400 group-hover:scale-110 transition-all">neurology</span>
                  </div>

                  <div className="relative z-10 space-y-1">
                    <h3 className="text-sm font-bold text-white group-hover:text-rose-300 transition-colors">RAG Semantic Agent</h3>
                    <p className="text-[11px] text-slate-300 font-mono">Vector Search + LLM</p>
                  </div>
                </div>

                {/* Item 4: Right Vertical Card (Supervisor Monitor) */}
                <div 
                  onClick={() => navigate('/execution')}
                  className="md:row-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-purple-500/60 hover:shadow-2xl hover:shadow-purple-500/20 cursor-pointer"
                >
                  {/* Full Cover Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=800&auto=format&fit=crop" alt="Supervisor View" className="w-full h-full object-cover opacity-40 group-hover:opacity-75 group-hover:scale-110 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-slate-950/30"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-purple-500/20 border border-purple-500/30 text-purple-300 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">SUPERVISOR ENGINE</span>
                    <span className="material-symbols-outlined text-slate-400 group-hover:text-purple-400 group-hover:scale-110 transition-all">visibility</span>
                  </div>

                  <div className="relative z-10 space-y-1.5">
                    <h3 className="text-lg font-bold text-white group-hover:text-purple-300 transition-colors">Real-time Pipeline Supervisor</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">Monitors the running state, tracks task progress, validates results, and dispatches state updates across the EventBus.</p>
                  </div>
                </div>

                {/* Item 5: Bottom Horizontal Card (Healing Controller) */}
                <div 
                  onClick={() => navigate('/plan')}
                  className="md:col-span-2 group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 flex flex-col justify-between transition-all duration-300 hover:-translate-y-2 hover:border-emerald-500/60 hover:shadow-2xl hover:shadow-emerald-500/20 cursor-pointer"
                >
                  {/* Full Cover Image Background */}
                  <div className="absolute inset-0 z-0 overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=800&auto=format&fit=crop" alt="Self-Healing Architecture" className="w-full h-full object-cover opacity-40 group-hover:opacity-75 group-hover:scale-110 transition-all duration-500 ease-out" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-slate-950/30"></div>
                  </div>

                  {/* Card Content Overlay */}
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-[10px] font-semibold font-mono tracking-wide backdrop-blur-md">HEALING CONTROLLER</span>
                    <span className="material-symbols-outlined text-slate-400 group-hover:text-emerald-400 group-hover:scale-110 transition-all">healing</span>
                  </div>

                  <div className="relative z-10 space-y-1.5 max-w-lg">
                    <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors">Resilient Self-Healing Engine</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">Synthesizes root-cause analyses for runtime failures and executes autonomous healing strategies to repair broken tasks without user intervention.</p>
                  </div>
                </div>

              </div>
            </section>

            {/* Artifacts Grid */}
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white tracking-tight">Generated Artifacts</h2>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => navigate('/artifacts')}
                    className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900 transition-colors"
                  >
                    <span className="material-symbols-outlined text-xl">filter_list</span>
                  </button>
                  <button
                    onClick={() => navigate('/artifacts')}
                    className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900 transition-colors"
                  >
                    <span className="material-symbols-outlined text-xl">grid_view</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Card 1 */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-4 transition-all duration-300 cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-semibold tracking-wide uppercase">
                        PPTX
                      </span>
                      <span className="material-symbols-outlined text-slate-500 group-hover:text-slate-300 text-lg transition-colors">
                        more_horiz
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                        Q3 AI Strategy Overview
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        Comprehensive breakdown of Q3 generative AI integration plans across core product lines.
                      </p>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium pt-2 border-t border-slate-800/60">
                    Updated today, 10:42 AM
                  </div>
                </div>

                {/* Card 2 */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-4 transition-all duration-300 cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-semibold tracking-wide uppercase">
                        PDF
                      </span>
                      <span className="material-symbols-outlined text-slate-500 group-hover:text-slate-300 text-lg transition-colors">
                        more_horiz
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                        Market Analysis Report
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        Detailed research document combining 15 distinct competitor web scraping runs.
                      </p>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium pt-2 border-t border-slate-800/60">
                    Updated yesterday
                  </div>
                </div>

                {/* Card 3 */}
                <div
                  onClick={() => navigate('/artifacts')}
                  className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-4 transition-all duration-300 cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-semibold tracking-wide uppercase">
                        CSV
                      </span>
                      <span className="material-symbols-outlined text-slate-500 group-hover:text-slate-300 text-lg transition-colors">
                        more_horiz
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                        User Engagement Metrics
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        Cleaned and formatted extract of telemetry data for the past 30 days.
                      </p>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium pt-2 border-t border-slate-800/60">
                    Updated Oct 12
                  </div>
                </div>
              </div>
            </section>
          </main>

          {/* Sidebar */}
          <aside className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 h-fit space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
              <span className="material-symbols-outlined text-indigo-400 text-xl">history</span>
              <h3 className="font-semibold text-sm text-slate-200">Context Memory</h3>
            </div>

            <div className="space-y-4 relative before:absolute before:inset-y-0 before:left-2.5 before:w-px before:bg-slate-800">
              <div className="flex gap-3 relative pl-1">
                <div className="w-3 h-3 rounded-full bg-indigo-500 ring-4 ring-slate-950 shrink-0 mt-1"></div>
                <div className="text-xs space-y-0.5">
                  <span className="text-slate-500 font-medium text-[10px]">Just Now</span>
                  <p className="text-slate-300 leading-relaxed">
                    Generated <strong className="text-white font-medium">Q3 AI Strategy</strong> presentation.
                  </p>
                </div>
              </div>

              <div className="flex gap-3 relative pl-1">
                <div className="w-3 h-3 rounded-full bg-slate-700 ring-4 ring-slate-950 shrink-0 mt-1"></div>
                <div className="text-xs space-y-0.5">
                  <span className="text-slate-500 font-medium text-[10px]">2 hours ago</span>
                  <p className="text-slate-300 leading-relaxed">
                    Extracted key metrics into <strong className="text-white font-medium">CSV</strong>.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={() => navigate('/execution')}
              className="w-full pt-3 border-t border-slate-800 text-center text-xs text-slate-400 hover:text-indigo-400 transition-colors font-medium cursor-pointer"
            >
              View Full Execution Logs &rarr;
            </button>
          </aside>
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
          className={`w-full py-8 px-6 flex flex-col items-center justify-center text-center relative border-t border-slate-800/80 rounded-t-[50px] bg-gradient-to-b from-slate-900 to-slate-950 shadow-[0_-10px_40px_rgba(0,0,0,0.6)] cursor-grab active:cursor-grabbing hover:border-indigo-500/50 transition-colors ${
            isDragging ? 'cursor-grabbing' : ''
          }`}
        >
          {/* Subtle Pull-Up Indicator Bar */}
          <div className="w-12 h-1.5 bg-slate-700/60 hover:bg-indigo-500/80 rounded-full mb-4 transition-colors animate-pulse" />

          <div className="group flex flex-col items-center gap-3 transition-transform duration-300 hover:scale-105 active:scale-95">
            <div className="w-20 h-20 rounded-full bg-slate-950 border-2 border-indigo-500/40 flex items-center justify-center shadow-[0_0_30px_rgba(168,85,247,0.3)] group-hover:border-indigo-500 group-hover:shadow-[0_0_45px_rgba(168,85,247,0.7)] transition-all">
              <img
                src="/logo.png"
                alt="AetherPhoenix Logo"
                className="w-14 h-14 object-contain pointer-events-none drop-shadow"
              />
            </div>
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-indigo-400 group-hover:text-indigo-300 transition-colors">
              <span className="material-symbols-outlined text-sm animate-bounce">keyboard_arrow_up</span>
              <span>LAUNCH AGENT ASSISTANT</span>
              <span className="material-symbols-outlined text-sm animate-bounce">keyboard_arrow_up</span>
            </div>
            <span className="text-[10px] text-slate-500">Pull up or click to launch</span>
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

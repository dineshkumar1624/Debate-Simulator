import React from 'react';

export const BackgroundGlow: React.FC = () => {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none">
      {/* 1. Subtle light architectural grid */}
      <div className="absolute inset-0 bg-grid-pattern opacity-80" />

      {/* 2. Soft radial spotlight behind hero center */}
      <div 
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[1100px] h-[750px] pointer-events-none opacity-80 dark:opacity-100"
        style={{
          background: 'radial-gradient(circle at 50% 20%, rgba(99, 102, 241, 0.12), transparent 58%)',
        }}
      />

      {/* 3. Center subtle light lift glow (hidden/softened in dark mode) */}
      <div className="absolute top-[8%] left-1/2 -translate-x-1/2 w-[700px] h-[500px] bg-white/50 dark:bg-indigo-900/10 rounded-full blur-[100px] pointer-events-none" />

      {/* 4. Left side: Soft blue ambient glow */}
      <div className="absolute top-[10%] -left-[10%] w-[680px] h-[680px] bg-sky-400/[0.13] dark:bg-sky-500/[0.16] rounded-full blur-[140px] pointer-events-none" />

      {/* 5. Right side: Soft purple / lavender ambient glow */}
      <div className="absolute top-[20%] -right-[10%] w-[680px] h-[680px] bg-purple-400/[0.12] dark:bg-purple-500/[0.16] rounded-full blur-[140px] pointer-events-none" />

      {/* 6. Mid-page ambient balancing glows for lower sections */}
      <div className="absolute top-[48%] -left-[5%] w-[550px] h-[550px] bg-indigo-400/[0.07] dark:bg-indigo-500/[0.12] rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute top-[65%] -right-[5%] w-[550px] h-[550px] bg-sky-400/[0.08] dark:bg-sky-500/[0.12] rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[5%] left-1/3 -translate-x-1/2 w-[600px] h-[450px] bg-purple-400/[0.07] dark:bg-purple-500/[0.12] rounded-full blur-[140px] pointer-events-none" />

      {/* 7. Subtle horizontal architectural guidelines */}
      <div className="absolute top-[280px] left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-indigo-500/[0.07] dark:via-indigo-500/[0.18] to-transparent" />
      <div className="absolute top-[720px] left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-purple-500/[0.07] dark:via-purple-500/[0.18] to-transparent" />

      {/* 8. Minimal subtle AI Network Pattern & ambient nodes */}
      <svg className="absolute inset-0 w-full h-full opacity-25 dark:opacity-40 pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        {/* Subtle Network Lines behind hero */}
        <line x1="12%" y1="18%" x2="28%" y2="28%" stroke="#6366f1" strokeWidth="0.75" strokeDasharray="3 3" opacity="0.4" />
        <line x1="28%" y1="28%" x2="22%" y2="42%" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 3" opacity="0.3" />
        <line x1="75%" y1="22%" x2="88%" y2="35%" stroke="#a855f7" strokeWidth="0.75" strokeDasharray="3 3" opacity="0.4" />
        <line x1="88%" y1="35%" x2="82%" y2="52%" stroke="#6366f1" strokeWidth="0.75" strokeDasharray="3 3" opacity="0.3" />

        {/* Small blue/purple AI nodes */}
        <circle cx="12%" cy="18%" r="2" fill="#38bdf8" />
        <circle cx="28%" cy="28%" r="1.5" fill="#6366f1" />
        <circle cx="22%" cy="42%" r="2" fill="#818cf8" />
        <circle cx="75%" cy="22%" r="2" fill="#a855f7" />
        <circle cx="88%" cy="35%" r="1.5" fill="#c084fc" />
        <circle cx="82%" cy="52%" r="2" fill="#ec4899" />
        <circle cx="48%" cy="14%" r="1.5" fill="#38bdf8" />
        <circle cx="52%" cy="78%" r="1.8" fill="#a855f7" />
        <circle cx="14%" cy="82%" r="1.5" fill="#6366f1" />
        <circle cx="86%" cy="86%" r="1.5" fill="#38bdf8" />
      </svg>
    </div>
  );
};

export default BackgroundGlow;

import React from 'react';

export interface SynthesisNucleusProps {
  visible: boolean;
  isFormed?: boolean;
}

/**
 * Floating Synthesis Nucleus
 * Emerges directly from within the Independent AI Judge core as the calculated,
 * evaluated, and synthesized distillation of the entire debate.
 * Purely floating and self-stabilizing (NO hands, NO mechanical arms, NO manipulators).
 */
export const SynthesisNucleus: React.FC<SynthesisNucleusProps> = ({
  visible,
  isFormed = true,
}) => {
  if (!visible) return null;

  return (
    <div className="relative flex items-center justify-center select-none pointer-events-none transition-all duration-1000 animate-fadeIn">
      {/* 1. Neutral Radiant Atmospheric Blooms (Neutral White, Indigo, Subtle Gold) */}
      <div
        className="absolute w-56 h-56 rounded-full bg-gradient-to-r from-amber-200/30 via-white/70 to-indigo-400/30 blur-2xl transition-all duration-1000 animate-pulse"
      />
      <div className="absolute w-36 h-36 rounded-full bg-white/80 blur-xl animate-ping opacity-50 pointer-events-none" />

      {/* 2. Floating 3D Crystalline Synthesis Core Shell */}
      <div
        className={`relative w-28 h-28 sm:w-32 sm:h-32 rounded-full bg-gradient-to-tr from-indigo-950/90 via-slate-900/90 to-amber-950/70 p-1.5 shadow-[0_0_40px_rgba(255,255,255,0.7),0_0_70px_rgba(251,191,36,0.4)] border border-white/80 flex items-center justify-center transition-all duration-700 ${
          isFormed ? 'scale-100 opacity-100' : 'scale-90 opacity-80'
        }`}
      >
        <svg
          viewBox="0 0 120 120"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full overflow-visible"
        >
          <defs>
            <radialGradient id="nucleus-gem-grad" cx="60" cy="60" r="50" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="35%" stopColor="#fef08a" />
              <stop offset="70%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#1e1b4b" />
            </radialGradient>
            <linearGradient id="nucleus-ring-gold" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="50%" stopColor="#fbbf24" />
              <stop offset="100%" stopColor="#818cf8" />
            </linearGradient>
          </defs>

          {/* Crystalline Core Dark Body */}
          <circle cx="60" cy="60" r="48" fill="rgba(15, 23, 42, 0.65)" stroke="#ffffff" strokeWidth="1.2" />

          {/* Internal Rotating Neural Filaments */}
          <g className="animate-[spin_20s_linear_infinite]" style={{ transformOrigin: '60px 60px' }}>
            <ellipse cx="60" cy="60" rx="40" ry="17" stroke="url(#nucleus-ring-gold)" strokeWidth="1.4" />
            <ellipse
              cx="60"
              cy="60"
              rx="36"
              ry="15"
              stroke="#ffffff"
              strokeWidth="1.1"
              transform="rotate(60 60 60)"
              strokeDasharray="4 2"
            />
            <ellipse
              cx="60"
              cy="60"
              rx="34"
              ry="13"
              stroke="#fbbf24"
              strokeWidth="1.1"
              transform="rotate(-60 60 60)"
              strokeDasharray="3 3"
            />
          </g>

          {/* Multi-facet Synthesis Core Diamond Pattern */}
          <path
            d="M 60 22 L 88 45 L 82 82 L 60 98 L 38 82 L 32 45 Z"
            fill="url(#nucleus-gem-grad)"
            stroke="#ffffff"
            strokeWidth="1.6"
            opacity="0.85"
          />

          {/* Internal Diamond Facet Filaments */}
          <line x1="60" y1="22" x2="60" y2="98" stroke="#ffffff" strokeWidth="1" opacity="0.9" />
          <line x1="32" y1="45" x2="88" y2="45" stroke="#ffffff" strokeWidth="1" opacity="0.9" />
          <line x1="38" y1="82" x2="82" y2="82" stroke="#ffffff" strokeWidth="1" opacity="0.9" />

          {/* Center Quantum Spark */}
          <circle cx="60" cy="60" r="8" fill="#ffffff" className="animate-pulse" />
          <circle cx="60" cy="60" r="3.5" fill="#fbbf24" />
        </svg>

        {/* Orbiting Stardust Particles */}
        <div className="absolute inset-0 rounded-full border border-amber-300/40 animate-[spin_12s_linear_infinite] pointer-events-none" />
      </div>

      {/* Floating Stabilization Aura */}
      <div className="absolute -inset-3 rounded-full border border-white/20 animate-pulse pointer-events-none" />
    </div>
  );
};

export default SynthesisNucleus;

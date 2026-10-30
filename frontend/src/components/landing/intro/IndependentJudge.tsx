import React, { useState, useEffect } from 'react';

export interface IndependentJudgeProps {
  visible: boolean;
  isAnalyzing: boolean;
  isSynthesized: boolean;
  hasNucleus?: boolean;
  isDormant?: boolean;
}

const ANALYSIS_CRITERIA = ['EVIDENCE', 'REASONING', 'COUNTERARGUMENTS', 'CONSISTENCY', 'BALANCE'];

export const IndependentJudge: React.FC<IndependentJudgeProps> = ({
  visible,
  isAnalyzing,
  isSynthesized,
  hasNucleus = false,
  isDormant = false,
}) => {
  const [activeCriterionIdx, setActiveCriterionIdx] = useState(0);

  useEffect(() => {
    if (!isAnalyzing) return;
    const interval = setInterval(() => {
      setActiveCriterionIdx((prev) => (prev + 1) % ANALYSIS_CRITERIA.length);
    }, 400);
    return () => clearInterval(interval);
  }, [isAnalyzing]);

  if (!visible) return null;

  return (
    <div
      className={`relative flex flex-col items-center justify-center select-none pointer-events-none transition-all duration-1000 ${
        isDormant ? 'opacity-25 scale-90 blur-[0.5px]' : 'opacity-100 scale-100 blur-0'
      }`}
      style={{
        filter: isDormant
          ? 'none'
          : 'drop-shadow(0 0 40px rgba(99, 102, 241, 0.45))',
      }}
    >
      {/* 1. Neutral Radiant Atmosphere (Indigo, Soft Gold, Pure White) */}
      {!isDormant && (
        <div className="absolute -inset-24 rounded-full bg-gradient-to-r from-indigo-500/15 via-amber-300/10 to-indigo-500/15 blur-3xl animate-pulse pointer-events-none" />
      )}

      {/* 2. Abstract 3D Celestial Evaluation Entity with Gyroscopic Gimbal Rings */}
      <div className="relative w-56 h-56 sm:w-72 sm:h-72 flex items-center justify-center">
        <svg
          viewBox="0 0 320 320"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full overflow-visible"
        >
          <defs>
            <linearGradient id="judge-gold-indigo" x1="40" y1="40" x2="280" y2="280" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.9" />
              <stop offset="35%" stopColor="#ffffff" stopOpacity="0.95" />
              <stop offset="70%" stopColor="#818cf8" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#fbbf24" stopOpacity="0.8" />
            </linearGradient>
            <radialGradient id="judge-core-orb" cx="160" cy="160" r="45" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="40%" stopColor="#fef08a" />
              <stop offset="75%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#1e1b4b" />
            </radialGradient>
          </defs>

          {/* Outer Constellation Orbit with Gold & Indigo Star Nodes */}
          <circle
            cx="160"
            cy="160"
            r="140"
            stroke="rgba(99, 102, 241, 0.35)"
            strokeWidth="1.2"
            strokeDasharray="4 4"
            className="animate-[spin_90s_linear_infinite]"
          />
          {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((deg) => {
            const rad = (deg * Math.PI) / 180;
            const x = 160 + Math.cos(rad) * 140;
            const y = 160 + Math.sin(rad) * 140;
            const isGold = deg % 60 === 0;
            return (
              <g key={deg}>
                <circle cx={x} cy={y} r={isGold ? 3 : 1.5} fill={isGold ? '#fbbf24' : '#c7d2fe'} />
                {isGold && <circle cx={x} cy={y} r={6} stroke="#fbbf24" strokeWidth="0.8" opacity="0.4" />}
              </g>
            );
          })}

          {/* 3D Gyroscopic Gimbal Rings (Neutral Gold & Indigo) */}
          {/* Ring 1 (Tilted -28 deg) */}
          <ellipse
            cx="160"
            cy="160"
            rx="115"
            ry="60"
            fill="none"
            stroke="url(#judge-gold-indigo)"
            strokeWidth="2"
            transform="rotate(-28 160 160)"
            className={isDormant ? '' : 'animate-[spin_45s_linear_infinite]'}
          />

          {/* Ring 2 (Tilted 38 deg) */}
          <ellipse
            cx="160"
            cy="160"
            rx="100"
            ry="48"
            fill="none"
            stroke="#fbbf24"
            strokeWidth="1.4"
            strokeDasharray="6 3"
            transform="rotate(38 160 160)"
            className={isDormant ? 'opacity-40' : 'animate-[spin_35s_linear_infinite_reverse] opacity-85'}
          />

          {/* Ring 3 (Tilted 8 deg, White) */}
          <ellipse
            cx="160"
            cy="160"
            rx="85"
            ry="30"
            fill="none"
            stroke="#ffffff"
            strokeWidth="1.6"
            transform="rotate(8 160 160)"
            className={isDormant ? 'opacity-40' : 'opacity-90'}
          />

          {/* Central 3D Evaluation Core Orb or Open Aperture for Nucleus */}
          {!hasNucleus ? (
            <>
              <circle cx="160" cy="160" r="32" fill="url(#judge-core-orb)" stroke="#ffffff" strokeWidth="2" />
              <circle cx="160" cy="160" r="14" fill="#0f172a" />
              {!isDormant && <circle cx="160" cy="160" r="6" fill="#fbbf24" className="animate-ping" opacity="0.8" />}
            </>
          ) : (
            <circle cx="160" cy="160" r="48" fill="none" stroke="url(#judge-gold-indigo)" strokeWidth="1.8" strokeDasharray="4 2" className="animate-pulse" />
          )}
        </svg>

        {/* Counter-orbital Accent Ring */}
        {!isDormant && (
          <div className="absolute inset-4 border border-amber-300/30 rounded-full animate-[spin_50s_linear_infinite] pointer-events-none" />
        )}
      </div>

      {/* 3. Judge Identification Header & Subtitle */}
      <div className={`absolute -top-12 text-center transition-opacity duration-700 ${isDormant ? 'opacity-50' : 'opacity-100'}`}>
        <span className="text-xs sm:text-sm font-mono font-extrabold tracking-widest uppercase text-white drop-shadow-[0_0_15px_rgba(251,191,36,0.8)]">
          INDEPENDENT AI JUDGE
        </span>
        <div className="text-[10px] font-mono text-indigo-300/90 mt-0.5 tracking-wider">
          {isDormant
            ? 'STANDBY • AWAITING SYNTHESIS STREAM'
            : isSynthesized
            ? 'DIALECTIC EQUILIBRIUM REACHED'
            : 'OBJECTIVE DIALECTIC ARBITRATION'}
        </div>
      </div>

      {/* 4. Active Analysis Micro-Criteria Indicators */}
      {isAnalyzing && (
        <div className="absolute -bottom-10 flex items-center justify-center gap-1.5 animate-fadeIn">
          {ANALYSIS_CRITERIA.map((criterion, idx) => {
            const isActive = idx === activeCriterionIdx;
            return (
              <span
                key={criterion}
                className={`px-2 py-0.5 rounded-full text-[9px] font-mono transition-all duration-300 ${
                  isActive
                    ? 'bg-amber-400/25 border border-amber-300 text-amber-200 scale-105 shadow-[0_0_10px_rgba(251,191,36,0.5)] font-bold'
                    : 'bg-indigo-950/40 border border-white/10 text-indigo-300/60 scale-95'
                }`}
              >
                {criterion}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default IndependentJudge;

import React from 'react';

export interface NeuralCoreViewProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  state?: 'idle' | 'thinking' | 'debating' | 'analyzing' | 'synthesizing' | 'pulse';
  stageIndex?: number; // 0 to 5 for How It Works stages (ASK -> SYNTHESIZE)
  glowColor?: 'indigo' | 'cyan' | 'purple' | 'amber' | 'neutral';
  className?: string;
  showLabel?: boolean;
  label?: string;
}

export const NeuralCoreView: React.FC<NeuralCoreViewProps> = ({
  size = 'md',
  state = 'idle',
  stageIndex,
  glowColor = 'indigo',
  className = '',
  showLabel = false,
  label,
}) => {
  // Size dimensions in px
  const dimensions = {
    xs: { dim: 48, stroke: 1, nodeR: 1.8 },
    sm: { dim: 80, stroke: 1.2, nodeR: 2.2 },
    md: { dim: 140, stroke: 1.4, nodeR: 3 },
    lg: { dim: 220, stroke: 1.6, nodeR: 3.5 },
    xl: { dim: 300, stroke: 2, nodeR: 4 },
  }[size];

  // Colors & Glow gradients
  const glowMap = {
    indigo: {
      ambient: 'rgba(99, 102, 241, 0.25)',
      primary: '#6366f1',
      secondary: '#818cf8',
      core: '#4f46e5',
    },
    cyan: {
      ambient: 'rgba(56, 189, 248, 0.25)',
      primary: '#38bdf8',
      secondary: '#7dd3fc',
      core: '#0284c7',
    },
    purple: {
      ambient: 'rgba(192, 132, 252, 0.25)',
      primary: '#c084fc',
      secondary: '#e879f9',
      core: '#9333ea',
    },
    amber: {
      ambient: 'rgba(251, 191, 36, 0.3)',
      primary: '#fbbf24',
      secondary: '#fef08a',
      core: '#d97706',
    },
    neutral: {
      ambient: 'rgba(255, 255, 255, 0.2)',
      primary: '#f8fafc',
      secondary: '#cbd5e1',
      core: '#64748b',
    },
  }[glowColor];

  // Dynamic rotation speeds & animation modifiers
  const isAnalyzing = state === 'analyzing';
  const isDebating = state === 'debating';
  const isSynthesizing = state === 'synthesizing';

  const ring1Speed = isAnalyzing ? '10s' : isDebating ? '18s' : '35s';
  const ring2Speed = isAnalyzing ? '14s' : isDebating ? '22s' : '45s';
  const ring3Speed = isSynthesizing ? '8s' : '55s';

  // SVG Unique identifier for gradients
  const idPrefix = React.useId().replace(/:/g, '');

  return (
    <div
      className={`relative inline-flex flex-col items-center justify-center select-none ${className}`}
      style={{
        filter: `drop-shadow(0 0 ${size === 'lg' || size === 'xl' ? '35px' : '18px'} ${glowMap.ambient})`,
      }}
    >
      {/* Volumetric background glow aura */}
      <div
        className="absolute inset-0 rounded-full blur-2xl pointer-events-none opacity-60 animate-pulse"
        style={{
          background: `radial-gradient(circle, ${glowMap.ambient} 0%, transparent 70%)`,
        }}
      />

      {/* SVG Neural Structure */}
      <div
        className="relative flex items-center justify-center"
        style={{ width: dimensions.dim, height: dimensions.dim }}
      >
        <svg
          viewBox="0 0 200 200"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full overflow-visible"
        >
          <defs>
            <linearGradient id={`${idPrefix}-grad`} x1="0" y1="0" x2="200" y2="200" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor={glowMap.secondary} stopOpacity="0.85" />
              <stop offset="50%" stopColor={glowMap.primary} stopOpacity="0.95" />
              <stop offset="100%" stopColor={glowMap.core} stopOpacity="0.75" />
            </linearGradient>
            <radialGradient id={`${idPrefix}-orb`} cx="100" cy="100" r="35" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="40%" stopColor={glowMap.secondary} />
              <stop offset="80%" stopColor={glowMap.primary} />
              <stop offset="100%" stopColor="#050711" />
            </radialGradient>
          </defs>

          {/* Gyroscopic Orbital Rings */}
          <g style={{ animation: `spin ${ring1Speed} linear infinite`, transformOrigin: 'center' }}>
            <ellipse
              cx="100"
              cy="100"
              rx="88"
              ry="36"
              stroke={`url(#${idPrefix}-grad)`}
              strokeWidth={dimensions.stroke}
              strokeDasharray="4 4"
              transform="rotate(25 100 100)"
              className="opacity-70"
            />
          </g>

          <g style={{ animation: `spin ${ring2Speed} linear infinite reverse`, transformOrigin: 'center' }}>
            <ellipse
              cx="100"
              cy="100"
              rx="78"
              ry="30"
              stroke={glowMap.secondary}
              strokeWidth={dimensions.stroke}
              strokeDasharray="6 3"
              transform="rotate(-45 100 100)"
              className="opacity-60"
            />
          </g>

          <g style={{ animation: `spin ${ring3Speed} linear infinite`, transformOrigin: 'center' }}>
            <ellipse
              cx="100"
              cy="100"
              rx="68"
              ry="24"
              stroke="#ffffff"
              strokeWidth={dimensions.stroke * 0.9}
              strokeDasharray="3 3"
              transform="rotate(70 100 100)"
              className="opacity-45"
            />
          </g>

          {/* Interconnected Filaments / Synaptic Mesh */}
          <g stroke={`url(#${idPrefix}-grad)`} strokeWidth={dimensions.stroke * 0.8} opacity="0.75">
            <line x1="100" y1="100" x2="50" y2="60" />
            <line x1="100" y1="100" x2="150" y2="60" />
            <line x1="100" y1="100" x2="40" y2="130" />
            <line x1="100" y1="100" x2="160" y2="130" />
            <line x1="100" y1="100" x2="100" y2="30" />
            <line x1="100" y1="100" x2="100" y2="170" />

            {/* Stage-evolving secondary filaments */}
            {(stageIndex === undefined || stageIndex >= 1) && (
              <>
                <line x1="50" y1="60" x2="100" y2="30" strokeDasharray="3 3" />
                <line x1="150" y1="60" x2="100" y2="30" strokeDasharray="3 3" />
              </>
            )}
            {(stageIndex === undefined || stageIndex >= 2) && (
              <>
                <line x1="50" y1="60" x2="40" y2="130" strokeDasharray="2 2" />
                <line x1="150" y1="60" x2="160" y2="130" strokeDasharray="2 2" />
              </>
            )}
            {(stageIndex === undefined || stageIndex >= 3) && (
              <>
                <line x1="40" y1="130" x2="100" y2="170" strokeDasharray="3 3" />
                <line x1="160" y1="130" x2="100" y2="170" strokeDasharray="3 3" />
              </>
            )}
          </g>

          {/* Neural Nodes */}
          {[
            { cx: 50, cy: 60, color: '#38bdf8' },
            { cx: 150, cy: 60, color: '#c084fc' },
            { cx: 40, cy: 130, color: '#0284c7' },
            { cx: 160, cy: 130, color: '#9333ea' },
            { cx: 100, cy: 30, color: '#ffffff' },
            { cx: 100, cy: 170, color: '#818cf8' },
            { cx: 75, cy: 80, color: '#e0e7ff' },
            { cx: 125, cy: 80, color: '#e0e7ff' },
          ].map((n, idx) => (
            <g key={idx}>
              <circle cx={n.cx} cy={n.cy} r={dimensions.nodeR * 1.8} fill={n.color} opacity="0.3" />
              <circle cx={n.cx} cy={n.cy} r={dimensions.nodeR} fill={n.color} />
              <circle cx={n.cx - 0.7} cy={n.cy - 0.7} r={dimensions.nodeR * 0.4} fill="#ffffff" />
            </g>
          ))}

          {/* Core Singularity Nucleus */}
          <circle
            cx="100"
            cy="100"
            r={size === 'xs' ? 10 : size === 'sm' ? 15 : size === 'md' ? 22 : 30}
            fill={`url(#${idPrefix}-orb)`}
            stroke="#ffffff"
            strokeWidth={dimensions.stroke * 1.2}
          />
          <circle
            cx="100"
            cy="100"
            r={size === 'xs' ? 5 : size === 'sm' ? 8 : size === 'md' ? 11 : 16}
            fill="#050711"
          />
          <circle
            cx="100"
            cy="100"
            r={size === 'xs' ? 2 : size === 'sm' ? 3.5 : size === 'md' ? 5 : 7}
            fill="#ffffff"
            className={isAnalyzing || isSynthesizing ? 'animate-ping' : ''}
            opacity="0.9"
          />
        </svg>
      </div>

      {showLabel && (
        <span className="mt-2 text-[10px] font-mono tracking-widest uppercase text-slate-400 font-semibold">
          {label || 'NEURAL CORE'}
        </span>
      )}
    </div>
  );
};

export default NeuralCoreView;

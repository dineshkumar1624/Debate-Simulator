import React from 'react';

export interface AINeuralBrainProps {
  type: 'PRO' | 'CON';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  state?: 'idle' | 'thinking' | 'arguing' | 'reacting' | 'converging';
  intensity?: number;
  className?: string;
  showLabel?: boolean;
  subLabel?: string;
}

export const AINeuralBrain: React.FC<AINeuralBrainProps> = ({
  type,
  size = 'md',
  state = 'idle',
  className = '',
  showLabel = true,
  subLabel,
}) => {
  const isPro = type === 'PRO';

  // Palette from Section 19:
  // PRO: #22D3EE, #38BDF8, #60A5FA, white highlights
  // CON: #A78BFA, #8B5CF6, #D946EF, white highlights
  const colors = isPro
    ? {
        primary: '#38BDF8',
        secondary: '#22D3EE',
        deep: '#0284C7',
        highlight: '#FFFFFF',
        accent: '#60A5FA',
        glow: 'rgba(56, 189, 248, 0.45)',
        aura: 'rgba(34, 211, 238, 0.15)',
        label: 'AI PRO',
        sub: subLabel || 'AFFIRMATIVE INTELLIGENCE',
      }
    : {
        primary: '#8B5CF6',
        secondary: '#D946EF',
        deep: '#7C3AED',
        highlight: '#FFFFFF',
        accent: '#A78BFA',
        glow: 'rgba(139, 92, 246, 0.45)',
        aura: 'rgba(217, 70, 239, 0.15)',
        label: 'AI CON',
        sub: subLabel || 'NEGATIVE SCRUTINY',
      };

  const dimensions = {
    sm: { width: 120, height: 100 },
    md: { width: 180, height: 150 },
    lg: { width: 260, height: 215 },
    xl: { width: 340, height: 280 },
  }[size];

  const isThinking = state === 'thinking';
  const isArguing = state === 'arguing';
  const isReacting = state === 'reacting';
  const isConverging = state === 'converging';

  const uid = React.useId().replace(/:/g, '');

  return (
    <div
      className={`relative inline-flex flex-col items-center select-none transition-all duration-700 ${className}`}
      style={{
        filter: `drop-shadow(0 0 ${isArguing || isThinking ? '30px' : '18px'} ${colors.glow})`,
      }}
    >
      {/* 1. Volumetric Neural Aura (Layered Deep Field) */}
      <div
        className={`absolute inset-0 rounded-full blur-2xl pointer-events-none transition-opacity duration-500 ${
          isArguing || isThinking ? 'opacity-80 scale-110' : 'opacity-40 scale-100'
        }`}
        style={{
          background: `radial-gradient(circle, ${colors.aura} 0%, transparent 70%)`,
        }}
      />

      {/* 2. Abstract 3D Artificial Neural Brain SVG Silhouette */}
      <div
        className="relative flex items-center justify-center"
        style={{ width: dimensions.width, height: dimensions.height }}
      >
        <svg
          viewBox="0 0 280 230"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`w-full h-full overflow-visible transition-transform duration-500 ${
            isThinking ? 'scale-105' : 'scale-100'
          }`}
          style={{
            transform: isPro ? 'scaleX(1)' : 'scaleX(-1)', // Orient frontal lobe toward center
          }}
        >
          <defs>
            <linearGradient id={`${uid}-brain-grad`} x1="20" y1="20" x2="260" y2="210" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor={colors.highlight} stopOpacity="0.9" />
              <stop offset="40%" stopColor={colors.secondary} stopOpacity="0.75" />
              <stop offset="80%" stopColor={colors.primary} stopOpacity="0.4" />
              <stop offset="100%" stopColor={colors.deep} stopOpacity="0.1" />
            </linearGradient>

            <linearGradient id={`${uid}-filament-grad`} x1="0" y1="0" x2="280" y2="230" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor={colors.secondary} />
              <stop offset="50%" stopColor={colors.primary} />
              <stop offset="100%" stopColor={colors.deep} />
            </linearGradient>

            <radialGradient id={`${uid}-core-burst`} cx="140" cy="115" r="70" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor={colors.highlight} stopOpacity="0.8" />
              <stop offset="50%" stopColor={colors.secondary} stopOpacity="0.4" />
              <stop offset="100%" stopColor="transparent" />
            </radialGradient>
          </defs>

          {/* BACKGROUND LAYER: Translucent Cortical Geometry & Outer Shell */}
          {/* Main Anatomical Silhouette of Artificial Brain (Lateral Perspective): Frontal, Parietal, Occipital, Temporal, Cerebellar Lobes */}
          <path
            d="M 120 28 
               C 160 22, 210 32, 245 65 
               C 272 90, 275 130, 255 160 
               C 240 182, 215 195, 185 192 
               C 170 190, 155 208, 135 210 
               C 118 212, 105 198, 95 185 
               C 65 188, 38 170, 28 142 
               C 18 115, 26 82, 48 58 
               C 68 36, 92 28, 120 28 Z"
            fill={`url(#${uid}-brain-grad)`}
            stroke={colors.primary}
            strokeWidth="1.6"
            className="opacity-25"
          />

          {/* Secondary Gyral & Sulcal Curvatures (Artificial Cortical Fissures) */}
          <path
            d="M 60 70 Q 110 50 160 75 T 235 95"
            stroke={colors.secondary}
            strokeWidth="1.2"
            strokeDasharray="4 3"
            opacity="0.6"
          />
          <path
            d="M 45 110 Q 95 95 155 115 T 240 140"
            stroke={colors.primary}
            strokeWidth="1.2"
            opacity="0.5"
          />
          <path
            d="M 75 150 Q 120 140 170 160 T 215 175"
            stroke={colors.accent}
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity="0.4"
          />
          <path
            d="M 140 32 C 145 70, 138 110, 142 165 C 145 190, 135 208, 130 210"
            stroke={colors.secondary}
            strokeWidth="1.4"
            opacity="0.5"
          />

          {/* INTERCONNECTING SYNAPTIC FILAMENTS (Neural Mesh Network) */}
          <g stroke={`url(#${uid}-filament-grad)`} strokeWidth="1.1" opacity="0.75">
            {/* Frontal to Central Mesh */}
            <line x1="210" y1="55" x2="165" y2="75" />
            <line x1="245" y1="90" x2="200" y2="105" />
            <line x1="245" y1="90" x2="210" y2="55" />
            <line x1="200" y1="105" x2="165" y2="75" />

            {/* Central to Parietal Mesh */}
            <line x1="165" y1="75" x2="120" y2="50" />
            <line x1="165" y1="75" x2="145" y2="115" />
            <line x1="200" y1="105" x2="185" y2="150" />
            <line x1="145" y1="115" x2="185" y2="150" />

            {/* Occipital & Temporal Mesh */}
            <line x1="120" y1="50" x2="70" y2="60" />
            <line x1="70" y1="60" x2="40" y2="95" />
            <line x1="120" y1="50" x2="100" y2="100" />
            <line x1="100" y1="100" x2="40" y2="95" />
            <line x1="100" y1="100" x2="145" y2="115" />

            {/* Temporal & Cerebellar Bottom Mesh */}
            <line x1="40" y1="95" x2="45" y2="140" />
            <line x1="45" y1="140" x2="90" y2="155" />
            <line x1="100" y1="100" x2="90" y2="155" />
            <line x1="90" y1="155" x2="140" y2="165" />
            <line x1="145" y1="115" x2="140" y2="165" />
            <line x1="140" y1="165" x2="185" y2="150" />
            <line x1="90" y1="155" x2="115" y2="195" />
            <line x1="140" y1="165" x2="115" y2="195" />
            <line x1="185" y1="150" x2="225" y2="165" />
            <line x1="200" y1="105" x2="245" y2="135" />
            <line x1="245" y1="135" x2="225" y2="165" />

            {/* Cross-mesh subtle diagonal links */}
            <line x1="70" y1="60" x2="100" y2="100" strokeDasharray="3 3" opacity="0.6" />
            <line x1="165" y1="75" x2="100" y2="100" strokeDasharray="2 2" opacity="0.5" />
            <line x1="200" y1="105" x2="140" y2="165" strokeDasharray="3 3" opacity="0.5" />
            <line x1="45" y1="140" x2="115" y2="195" strokeDasharray="2 2" opacity="0.4" />
          </g>

          {/* DENSE NEURAL NODES & ACTIVE SYNAPSES */}
          {[
            // Frontal Thought Hub (Front of brain)
            { cx: 245, cy: 90, r: 4.2, isEmmiter: true, pulse: true },
            { cx: 210, cy: 55, r: 3.8, isEmmiter: true, pulse: false },
            { cx: 200, cy: 105, r: 4.5, isEmmiter: true, pulse: true },
            { cx: 245, cy: 135, r: 3.5, isEmmiter: true, pulse: false },
            { cx: 225, cy: 165, r: 3.8, isEmmiter: false, pulse: false },

            // Superior Parietal Cortex (Top of brain)
            { cx: 165, cy: 75, r: 4.2, isEmmiter: false, pulse: true },
            { cx: 120, cy: 50, r: 3.8, isEmmiter: false, pulse: false },
            { cx: 70, cy: 60, r: 3.5, isEmmiter: false, pulse: false },

            // Central Core Singularity & Limbic Nodes (Middle depth)
            { cx: 145, cy: 115, r: 5.2, isEmmiter: false, pulse: true },
            { cx: 100, cy: 100, r: 4.0, isEmmiter: false, pulse: false },
            { cx: 185, cy: 150, r: 4.2, isEmmiter: false, pulse: true },

            // Occipital Cortex (Back of brain)
            { cx: 40, cy: 95, r: 3.6, isEmmiter: false, pulse: false },
            { cx: 45, cy: 140, r: 3.8, isEmmiter: false, pulse: false },

            // Temporal & Cerebellar Lobes (Bottom of brain)
            { cx: 90, cy: 155, r: 3.8, isEmmiter: false, pulse: false },
            { cx: 140, cy: 165, r: 4.0, isEmmiter: false, pulse: true },
            { cx: 115, cy: 195, r: 3.4, isEmmiter: false, pulse: false },

            // Intermediate Computational Synaptic Clusters
            { cx: 175, cy: 45, r: 2.4, isEmmiter: false, pulse: false },
            { cx: 225, cy: 80, r: 2.6, isEmmiter: true, pulse: true },
            { cx: 175, cy: 125, r: 2.8, isEmmiter: false, pulse: false },
            { cx: 125, cy: 85, r: 2.5, isEmmiter: false, pulse: false },
            { cx: 70, cy: 125, r: 2.6, isEmmiter: false, pulse: false },
            { cx: 165, cy: 175, r: 2.5, isEmmiter: false, pulse: false },
          ].map((node, i) => {
            const shouldGlow = (isThinking || isArguing || isReacting) && (node.pulse || node.isEmmiter);

            return (
              <g key={i}>
                {/* Node Outer Energy Corona */}
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={node.r * 2.2}
                  fill={colors.secondary}
                  opacity={shouldGlow ? '0.45' : '0.15'}
                  className={shouldGlow ? 'animate-pulse' : ''}
                />
                {/* Node Core Body */}
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={node.r}
                  fill={shouldGlow ? colors.highlight : colors.primary}
                  stroke={colors.highlight}
                  strokeWidth={node.r > 4 ? '1' : '0.6'}
                />
                {/* Node Highlight Glint */}
                <circle
                  cx={node.cx - node.r * 0.3}
                  cy={node.cy - node.r * 0.3}
                  r={node.r * 0.35}
                  fill="#FFFFFF"
                />
              </g>
            );
          })}

          {/* ACTIVE SYNAPTIC FIRING (When thinking or arguing) */}
          {(isThinking || isArguing || isReacting) && (
            <g>
              {/* Internal synaptic firing sparks */}
              <circle cx="145" cy="115" r="8" fill={`url(#${uid}-core-burst)`} className="animate-ping" opacity="0.6" />
              <line
                x1="145"
                y1="115"
                x2="200"
                y2="105"
                stroke={colors.highlight}
                strokeWidth="2"
                strokeLinecap="round"
                className="animate-pulse"
              />
              <line
                x1="200"
                y1="105"
                x2="245"
                y2="90"
                stroke={colors.secondary}
                strokeWidth="2"
                strokeLinecap="round"
                className="animate-pulse"
              />
            </g>
          )}

          {/* EMITTING PARTICLES HINT AT FRONTAL TIP (When arguing) */}
          {(isArguing || isThinking) && (
            <g className="animate-pulse">
              <circle cx="260" cy="90" r="2.5" fill={colors.highlight} opacity="0.9" />
              <circle cx="270" cy="100" r="2.0" fill={colors.secondary} opacity="0.8" />
              <circle cx="265" cy="80" r="1.8" fill={colors.primary} opacity="0.7" />
            </g>
          )}
        </svg>
      </div>

      {/* 3. Subtle Clean Typography Label */}
      {showLabel && (
        <div className="mt-2.5 flex flex-col items-center text-center">
          <div
            className={`px-3 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-widest font-black transition-all ${
              isArguing || isThinking
                ? isPro
                  ? 'bg-sky-500 text-white shadow-[0_0_15px_rgba(56,189,248,0.6)]'
                  : 'bg-purple-600 text-white shadow-[0_0_15px_rgba(168,85,247,0.6)]'
                : 'bg-slate-100/90 dark:bg-slate-900/80 text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-white/10'
            }`}
          >
            <span>{colors.label}</span>
          </div>
          <span
            className={`text-[9px] font-mono mt-0.5 font-semibold tracking-wider uppercase ${
              isPro ? 'text-sky-600 dark:text-sky-400' : 'text-purple-600 dark:text-purple-400'
            }`}
          >
            {isThinking
              ? isPro
                ? 'GENERATING ARGUMENT'
                : 'SYNTHESIZING COUNTERARGUMENT'
              : isArguing
              ? 'TRANSMITTING THOUGHT PARTICLES'
              : isConverging
              ? 'REASONING CONVERGED'
              : colors.sub}
          </span>
        </div>
      )}
    </div>
  );
};

export default AINeuralBrain;

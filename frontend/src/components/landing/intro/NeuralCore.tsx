import React from 'react';

interface NeuralCoreProps {
  phase: string;
  isExpanded?: boolean;
}

export const NeuralCore: React.FC<NeuralCoreProps> = ({ phase, isExpanded = false }) => {
  // Abstract 3D Neural Intelligence Structure
  // Multiple depth layers: background nodes, central singularity, foreground orbital filaments
  return (
    <div
      className={`relative flex flex-col items-center justify-center transition-all duration-1000 ${
        isExpanded ? 'scale-125' : 'scale-100'
      }`}
      style={{
        filter: 'drop-shadow(0 0 45px rgba(99, 102, 241, 0.45))',
      }}
    >
      {/* 1. Deep Volumetric Ambient Atmosphere */}
      <div className="absolute -inset-20 rounded-full bg-gradient-to-r from-sky-500/10 via-indigo-500/15 to-purple-500/10 blur-3xl animate-pulse pointer-events-none" />

      {/* 2. Abstract 3D Neural Network Nodes & Interconnected Filaments */}
      <div className="relative w-44 h-44 sm:w-56 sm:h-56 flex items-center justify-center">
        <svg
          viewBox="0 0 240 240"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full animate-[spin_60s_linear_infinite]"
        >
          <defs>
            <linearGradient id="core-neural-grad-1" x1="20" y1="20" x2="220" y2="220" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#818cf8" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#c084fc" stopOpacity="0.8" />
            </linearGradient>
            <radialGradient id="core-orb-grad" cx="120" cy="120" r="40" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="35%" stopColor="#a5b4fc" />
              <stop offset="70%" stopColor="#4f46e5" />
              <stop offset="100%" stopColor="#0f172a" />
            </radialGradient>
            <linearGradient id="core-ring-grad" x1="0" y1="0" x2="240" y2="240" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#c084fc" stopOpacity="0.6" />
            </linearGradient>
          </defs>

          {/* Background Layer: Orbital Elliptical Rings */}
          <ellipse
            cx="120"
            cy="120"
            rx="105"
            ry="45"
            stroke="url(#core-ring-grad)"
            strokeWidth="1.2"
            strokeDasharray="4 4"
            transform="rotate(25 120 120)"
            className="opacity-60"
          />
          <ellipse
            cx="120"
            cy="120"
            rx="95"
            ry="40"
            stroke="#818cf8"
            strokeWidth="1.2"
            strokeDasharray="6 3"
            transform="rotate(-40 120 120)"
            className="opacity-50"
          />
          <ellipse
            cx="120"
            cy="120"
            rx="85"
            ry="30"
            stroke="#ffffff"
            strokeWidth="1.5"
            transform="rotate(75 120 120)"
            className="opacity-40"
          />

          {/* Mid Layer: Organic Computational Filaments (Neural Network Mesh) */}
          <g stroke="url(#core-neural-grad-1)" strokeWidth="1.2" opacity="0.75">
            <line x1="120" y1="120" x2="60" y2="70" />
            <line x1="120" y1="120" x2="180" y2="70" />
            <line x1="120" y1="120" x2="50" y2="150" />
            <line x1="120" y1="120" x2="190" y2="150" />
            <line x1="120" y1="120" x2="120" y2="35" />
            <line x1="120" y1="120" x2="120" y2="205" />

            {/* Cross-mesh interconnects */}
            <line x1="60" y1="70" x2="120" y2="35" strokeDasharray="3 3" />
            <line x1="180" y1="70" x2="120" y2="35" strokeDasharray="3 3" />
            <line x1="60" y1="70" x2="50" y2="150" strokeDasharray="2 2" />
            <line x1="180" y1="70" x2="190" y2="150" strokeDasharray="2 2" />
            <line x1="50" y1="150" x2="120" y2="205" strokeDasharray="3 3" />
            <line x1="190" y1="150" x2="120" y2="205" strokeDasharray="3 3" />
          </g>

          {/* 3D Neural Node Clusters (Layered Spheres) */}
          {[
            { cx: 60, cy: 70, r: 3.5, color: '#38bdf8' },
            { cx: 180, cy: 70, r: 3.5, color: '#c084fc' },
            { cx: 50, cy: 150, r: 4, color: '#0ea5e9' },
            { cx: 190, cy: 150, r: 4, color: '#a855f7' },
            { cx: 120, cy: 35, r: 3, color: '#ffffff' },
            { cx: 120, cy: 205, r: 3.5, color: '#818cf8' },
            { cx: 90, cy: 95, r: 2.5, color: '#e0e7ff' },
            { cx: 150, cy: 95, r: 2.5, color: '#e0e7ff' },
            { cx: 85, cy: 145, r: 2.5, color: '#38bdf8' },
            { cx: 155, cy: 145, r: 2.5, color: '#c084fc' },
          ].map((node, i) => (
            <g key={i}>
              <circle cx={node.cx} cy={node.cy} r={node.r * 1.8} fill={node.color} opacity="0.25" />
              <circle cx={node.cx} cy={node.cy} r={node.r} fill={node.color} />
              <circle cx={node.cx - 1} cy={node.cy - 1} r={node.r * 0.4} fill="#ffffff" />
            </g>
          ))}

          {/* Foreground Layer: Central Neural Singularity Nucleus */}
          <circle cx="120" cy="120" r="28" fill="url(#core-orb-grad)" stroke="#ffffff" strokeWidth="1.8" />
          <circle cx="120" cy="120" r="14" fill="#0f172a" />
          <circle cx="120" cy="120" r="6" fill="#ffffff" className="animate-ping" opacity="0.75" />
        </svg>

        {/* Counter-rotating Gyroscopic Halo */}
        <div className="absolute inset-2 border border-indigo-400/30 rounded-full animate-[spin_40s_linear_infinite_reverse] pointer-events-none" />
        <div className="absolute inset-6 border border-sky-400/20 rounded-full animate-pulse pointer-events-none" />
      </div>

      {/* Subtle Initialization Status Badge */}
      {phase === 'INITIAL_CORE' && (
        <div className="mt-4 text-center animate-fadeIn">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-black/60 border border-white/10 backdrop-blur-md text-[10px] font-mono text-indigo-300 uppercase tracking-widest">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping" />
            <span>AI NEURAL ENGINE INITIALIZING</span>
          </div>
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { HelpCircle } from 'lucide-react';

interface QuestionHologramProps {
  visible: boolean;
  question?: string;
}

export const QuestionHologram: React.FC<QuestionHologramProps> = ({
  visible,
  question = 'Should artificial intelligence make critical autonomous decisions for human society?',
}) => {
  if (!visible) return null;

  return (
    <div
      className="absolute top-[28%] sm:top-[26%] left-1/2 -translate-x-1/2 -translate-y-1/2 z-30 pointer-events-none transition-all duration-700 ease-out flex flex-col items-center max-w-lg px-4 text-center animate-fadeIn"
    >
      {/* Holographic Badge */}
      <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-indigo-950/70 border border-indigo-400/40 text-[10px] font-mono text-indigo-300 uppercase tracking-widest mb-2 shadow-[0_0_15px_rgba(99,102,241,0.3)]">
        <HelpCircle className="w-3 h-3 text-sky-400" />
        <span>DIALECTIC INQUIRY</span>
      </div>

      {/* Holographic Query Text with soft neon scanline illumination */}
      <div className="relative px-5 py-3 rounded-2xl bg-black/60 backdrop-blur-xl border border-white/15 shadow-[0_0_35px_rgba(0,0,0,0.8),0_0_25px_rgba(99,102,241,0.25)]">
        {/* Subtle scanline overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-sky-400/[0.04] to-transparent pointer-events-none rounded-2xl animate-pulse" />
        
        <p className="text-xs sm:text-sm font-sans font-medium text-slate-100 tracking-wide leading-relaxed drop-shadow-[0_0_10px_rgba(255,255,255,0.4)]">
          "{question}"
        </p>
      </div>

      <div className="mt-1 text-[9px] font-mono text-slate-400 tracking-wider uppercase opacity-75">
        ILLUSTRATIVE SYNTHESIS TOPIC
      </div>
    </div>
  );
};

import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Scale, Sparkles, RefreshCw, Cpu } from 'lucide-react';
import { Button } from '../ui/Button';

export const CompactWhyDebate: React.FC = () => {
  return (
    <section className="py-12 relative overflow-hidden">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-panel rounded-3xl p-8 sm:p-12 border border-slate-200/80 dark:border-white/10 shadow-xl bg-white/90 dark:bg-[#070a16]/85 text-center relative overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 dark:bg-indigo-500/15 rounded-full blur-3xl -z-10 pointer-events-none" />

          {/* Tag */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider mb-4 shadow-sm">
            <span>CORE PHILOSOPHY</span>
          </div>

          {/* Heading and Core Proposition */}
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-black text-[#0F172A] dark:text-white tracking-tight mb-3">
            One AI gives you an answer.
          </h2>
          <p className="text-lg sm:text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 dark:from-sky-400 dark:via-indigo-300 dark:to-purple-400 mb-8">
            Opposing perspectives make you question it.
          </p>

          {/* Concise Visual Diagram: DOCUMENT -> EXTRACT -> AI PRO ↔ AI CON -> AI JUDGE -> SYNTHESIS */}
          <div className="max-w-xl mx-auto my-6 p-6 rounded-2xl bg-slate-50/80 dark:bg-[#050814]/80 border border-slate-200/80 dark:border-white/10 shadow-inner">
            {/* Step 0: Uploaded Document */}
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-white/10 flex items-center justify-between max-w-sm mx-auto shadow-sm mb-2.5">
              <div className="flex items-center gap-2">
                <span className="text-base">📄</span>
                <span className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200">
                  DOCUMENT (PDF / DOCX)
                </span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold">
                PAGE CITATIONS
              </span>
            </div>

            {/* Down arrow */}
            <div className="flex justify-center my-1.5">
              <span className="text-[11px] font-mono text-slate-400">↓ evidence extraction</span>
            </div>

            {/* Step 1: AI PRO ↔ AI CON */}
            <div className="flex items-center justify-center gap-3 sm:gap-6">
              <div className="flex-1 p-3 rounded-xl bg-sky-50 dark:bg-sky-950/50 border border-sky-300 dark:border-sky-500/40 flex items-center justify-center gap-2 shadow-sm">
                <Cpu className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                <div className="text-left">
                  <div className="text-xs font-mono font-bold text-sky-800 dark:text-sky-300">AI PRO</div>
                  <div className="text-[9px] font-mono text-sky-600 dark:text-sky-400">Supports Claims</div>
                </div>
              </div>

              <div className="w-8 h-8 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 flex items-center justify-center shadow-sm text-indigo-600 dark:text-indigo-400">
                <RefreshCw className="w-3.5 h-3.5" />
              </div>

              <div className="flex-1 p-3 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-300 dark:border-purple-500/40 flex items-center justify-center gap-2 shadow-sm">
                <Cpu className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <div className="text-left">
                  <div className="text-xs font-mono font-bold text-purple-800 dark:text-purple-300">AI CON</div>
                  <div className="text-[9px] font-mono text-purple-600 dark:text-purple-400">Challenges Flaws</div>
                </div>
              </div>
            </div>

            {/* Down arrow */}
            <div className="flex justify-center my-2">
              <span className="text-[11px] font-mono text-slate-400">↓ objective arbitration</span>
            </div>

            {/* Step 2: AI JUDGE */}
            <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-500/40 flex items-center justify-center gap-2 max-w-sm mx-auto shadow-sm">
              <Scale className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-mono font-bold text-indigo-900 dark:text-indigo-200">
                INDEPENDENT AI JUDGE
              </span>
            </div>

            {/* Down arrow */}
            <div className="flex justify-center my-2">
              <span className="text-[11px] font-mono text-slate-400">↓ grounded convergence</span>
            </div>

            {/* Step 3: SYNTHESIS */}
            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-500/50 flex items-center justify-center gap-2 max-w-sm mx-auto shadow-sm">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-mono font-bold text-amber-900 dark:text-amber-200">
                EVIDENCE-GROUNDED SYNTHESIS
              </span>
            </div>
          </div>

          {/* Action button navigating to /how-it-works */}
          <div className="pt-2">
            <Link to="/how-it-works">
              <Button
                variant="secondary"
                size="md"
                className="gap-2 font-mono text-xs font-bold shadow-sm uppercase tracking-wider"
              >
                <span>EXPLORE HOW IT WORKS</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CompactWhyDebate;

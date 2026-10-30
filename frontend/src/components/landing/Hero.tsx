import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Cpu, ShieldCheck, Scale, Sparkles } from 'lucide-react';
import { Button } from '../ui/Button';
import { Interactive3DChamber } from '../debate/Interactive3DChamber';

export const Hero: React.FC = () => {
  return (
    <section className="relative pt-6 pb-14 lg:pt-12 lg:pb-20 overflow-hidden">
      {/* Subtle background ambient neural gradient */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[850px] h-[450px] bg-gradient-to-r from-sky-500/10 via-indigo-500/10 to-purple-500/10 rounded-full blur-[140px] pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-10 items-center">
          {/* Left Column: Headline and CTAs */}
          <div className="lg:col-span-5 flex flex-col items-start text-left z-10 space-y-6">
            {/* Top pill badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-200/90 dark:border-indigo-500/30 bg-indigo-50/90 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold backdrop-blur-md shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-indigo-500 animate-pulse" />
              <span>DOCUMENT-GROUNDED AI REASONING PLATFORM</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-[#0F172A] dark:text-white tracking-tight leading-[1.06]">
              <span className="block text-slate-800 dark:text-slate-200 text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-normal mb-1">
                DON'T JUST READ A DOCUMENT.
              </span>
              <span className="relative inline-block text-transparent bg-clip-text bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 dark:from-sky-400 dark:via-indigo-300 dark:to-purple-400 font-black drop-shadow-sm">
                MAKE AI DEBATE IT.
                <span className="absolute left-0 -bottom-1 w-full h-[3.5px] bg-gradient-to-r from-sky-400 via-indigo-400 to-purple-500 rounded-full opacity-90 shadow-sm shadow-indigo-500/30" />
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-lg leading-relaxed font-normal">
              Upload research papers, legal briefs, technical specifications, or policy reports. AI PRO extracts supporting claims, AI CON rigorously challenges methodology and blind spots, and an Independent AI Judge delivers a verifiable, citation-backed synthesis.
            </p>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full sm:w-auto pt-2">
              <Link to="/debate" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  className="w-full sm:w-auto gap-2.5 font-bold shadow-xl shadow-indigo-600/30 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white border border-indigo-500/20"
                >
                  <span>START DOCUMENT DEBATE</span>
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Link to="/documents" className="w-full sm:w-auto">
                <Button
                  variant="secondary"
                  size="lg"
                  className="w-full sm:w-auto font-semibold"
                >
                  BROWSE DOCUMENTS
                </Button>
              </Link>
            </div>

            {/* Supporting Micro-label */}
            <div className="pt-4 border-t border-slate-200/80 dark:border-white/10 w-full">
              <div className="flex flex-wrap items-center gap-y-2 gap-x-3 text-xs font-mono text-slate-500 dark:text-slate-400 font-semibold tracking-wide uppercase">
                <div className="flex items-center gap-1.5 text-sky-600 dark:text-sky-400">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>GROUNDED EVIDENCE</span>
                </div>
                <span className="text-slate-300 dark:text-slate-600">•</span>
                <div className="flex items-center gap-1.5 text-purple-600 dark:text-purple-400">
                  <Scale className="w-3.5 h-3.5" />
                  <span>INDEPENDENT EVALUATOR</span>
                </div>
                <span className="text-slate-300 dark:text-slate-600">•</span>
                <div className="flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400">
                  <Cpu className="w-3.5 h-3.5" />
                  <span>PAGE-ACCURATE CITATIONS</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Signature 3D AI Debate Chamber */}
          <div className="lg:col-span-7 w-full flex justify-center lg:justify-end">
            <Interactive3DChamber />
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;

import React from 'react';
import { User, Brain, Scale, Sparkles, ArrowDown, ShieldCheck } from 'lucide-react';
import { Badge } from '../ui/Badge';

export const DemoExperience: React.FC = () => {
  return (
    <section className="py-24 relative overflow-hidden bg-white/80 dark:bg-transparent border-t border-slate-200/50 dark:border-white/10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-14 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            <span>Transcript Preview</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
            SEE HOW A DEBATE EVOLVES
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
            Follow a real multi-agent dialectic transcript from initial user inquiry down to evidentiary synthesis.
          </p>

          <div className="inline-block pt-1">
            <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-amber-700 dark:text-amber-300 font-bold tracking-wider shadow-sm">
              ILLUSTRATIVE EXAMPLE • DEMO TRANSCRIPT
            </span>
          </div>
        </div>

        {/* Mini Visual Transcript Stack */}
        <div className="glass-panel p-6 sm:p-9 rounded-3xl border border-slate-200/90 dark:border-white/10 shadow-[0_20px_60px_-15px_rgba(15,23,42,0.06)] dark:shadow-[0_20px_60px_-15px_rgba(0,0,0,0.5)] bg-white/95 dark:bg-[#080d1e]/85 backdrop-blur-2xl space-y-5">
          {/* 1. USER */}
          <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <User className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-bold text-slate-900 dark:text-white font-mono uppercase">
                  USER QUESTION
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-400 font-medium">Initiation</span>
            </div>
            <p className="text-sm text-slate-800 dark:text-slate-100 font-semibold">
              "Should AI-generated content require labeling?"
            </p>
          </div>

          <div className="flex justify-center text-slate-400 dark:text-slate-600">
            <ArrowDown className="w-4 h-4" />
          </div>

          {/* 2. AI PRO */}
          <div className="p-4 rounded-2xl border border-sky-200 dark:border-sky-900/50 bg-sky-50/50 dark:bg-sky-950/40 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-sky-100 dark:bg-sky-900/40 border border-sky-200 dark:border-sky-500/30 flex items-center justify-center text-sky-600 dark:text-sky-400">
                  <Brain className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-bold text-slate-900 dark:text-white font-mono uppercase">
                  AI PRO (Agent Alpha)
                </span>
              </div>
              <Badge variant="pro" className="text-[9px]">
                Affirmative
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
              "Labeling can improve transparency, restore information authenticity, and deter malicious deepfake dissemination across public discourse."
            </p>
            <div className="mt-2.5 pt-2 border-t border-sky-100 dark:border-sky-900/40 flex items-center gap-2 text-[10px] font-mono text-sky-700 dark:text-sky-300 font-medium">
              <ShieldCheck className="w-3 h-3 text-sky-600 dark:text-sky-400" />
              <span>Evidence: Citing EU AI Act Article 52 Disclosure Framework</span>
            </div>
          </div>

          <div className="flex justify-center text-slate-400 dark:text-slate-600">
            <ArrowDown className="w-4 h-4" />
          </div>

          {/* 3. AI CON */}
          <div className="p-4 rounded-2xl border border-pink-200 dark:border-pink-900/50 bg-pink-50/50 dark:bg-pink-950/40 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-pink-100 dark:bg-pink-900/40 border border-pink-200 dark:border-pink-500/30 flex items-center justify-center text-pink-600 dark:text-pink-400">
                  <Brain className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-bold text-slate-900 dark:text-white font-mono uppercase">
                  AI CON (Agent Beta)
                </span>
              </div>
              <Badge variant="con" className="text-[9px]">
                Negative
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
              "Mandatory labeling may create enforcement overhead, trigger free-speech litigation, and induce false complacency when unwatermarked synthetic content slips through."
            </p>
            <div className="mt-2.5 pt-2 border-t border-pink-100 dark:border-pink-900/40 flex items-center gap-2 text-[10px] font-mono text-pink-700 dark:text-pink-300 font-medium">
              <ShieldCheck className="w-3 h-3 text-pink-600 dark:text-pink-400" />
              <span>Precedent: Citing FTC First Amendment Commercial Speech Standards</span>
            </div>
          </div>

          <div className="flex justify-center text-slate-400 dark:text-slate-600">
            <ArrowDown className="w-4 h-4" />
          </div>

          {/* 4. AI JUDGE */}
          <div className="p-4 rounded-2xl border border-purple-200 dark:border-purple-900/50 bg-purple-50/50 dark:bg-purple-950/40 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-purple-100 dark:bg-purple-900/40 border border-purple-200 dark:border-purple-500/30 flex items-center justify-center text-purple-700 dark:text-purple-400">
                  <Scale className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-bold text-slate-900 dark:text-white font-mono uppercase">
                  INDEPENDENT AI JUDGE
                </span>
              </div>
              <Badge variant="judge" className="text-[9px]">
                Adjudication
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
              "Both arguments identify legitimate tradeoffs: PRO grounds transparency benefits in empirical voter trust studies, while CON correctly notes that technical watermarking standards remain vulnerable to adversarial removal."
            </p>
          </div>

          <div className="flex justify-center text-slate-400 dark:text-slate-600">
            <ArrowDown className="w-4 h-4" />
          </div>

          {/* 5. FINAL SYNTHESIS */}
          <div className="p-4 sm:p-5 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/40 dark:bg-amber-950/40 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span className="text-xs font-bold text-slate-900 dark:text-white font-mono uppercase">
                  FINAL BALANCED SYNTHESIS
                </span>
              </div>
              <span className="text-[10px] font-mono text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950/60 border border-amber-200/80 dark:border-amber-800/80 font-bold">
                Consensus
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 italic leading-relaxed font-medium">
              "Evidence suggests universal mandatory labeling is currently technically unenforceable; however, risk-tiered labeling for high-stakes domains (political ads, legal filings) provides maximum transparency with minimal chilling effect."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DemoExperience;

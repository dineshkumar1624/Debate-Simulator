import React from 'react';
import { ArrowDown, AlertTriangle, CheckCircle2, ShieldCheck, Scale, Sparkles, Brain } from 'lucide-react';

export const WhyMultiAgent: React.FC = () => {
  return (
    <section className="py-24 relative overflow-hidden bg-[#F8FAFC]/80 dark:bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-4xl mx-auto mb-16 space-y-5">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-purple-200 dark:border-purple-500/30 bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            Dialectical Epistemology
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight leading-tight">
            One AI gives you an answer.{' '}
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 dark:from-sky-400 dark:via-indigo-300 dark:to-purple-400">
              Multiple perspectives make you question it.
            </span>
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
            AI Debate Simulator uses structured disagreement to expose assumptions, counterarguments, evidence, and uncertainty.
          </p>
        </div>

        {/* Visual Comparison: ONE AI vs MULTI-AGENT DEBATE */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch max-w-5xl mx-auto">
          {/* Card 1: Conventional Monolithic AI (Flawed) */}
          <div className="lg:col-span-5 glass-panel rounded-3xl p-6 sm:p-8 border border-red-200 dark:border-red-900/50 bg-white/90 dark:bg-[#150a0e]/85 flex flex-col justify-between shadow-md">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-mono uppercase tracking-wider text-red-700 dark:text-red-300 font-bold bg-red-50 dark:bg-red-950/40 px-3 py-1 rounded-lg border border-red-200 dark:border-red-900/50">
                  Standard LLM Prompt
                </span>
                <AlertTriangle className="w-5 h-5 text-red-500" />
              </div>

              <div className="space-y-4 my-6">
                {/* Node 1 */}
                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 text-center font-mono text-xs font-bold text-slate-700 dark:text-slate-300 shadow-sm">
                  ONE AI MODEL
                </div>

                <div className="flex justify-center text-slate-400">
                  <ArrowDown className="w-4 h-4" />
                </div>

                {/* Node 2 */}
                <div className="p-3.5 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/40 text-center font-mono text-xs font-bold text-red-700 dark:text-red-300 shadow-sm">
                  SINGLE UNCHECKED ANSWER
                </div>
              </div>

              <div className="border-t border-slate-100 dark:border-white/10 pt-5 space-y-2.5 text-xs text-slate-600 dark:text-slate-300">
                <div className="flex items-start gap-2">
                  <span className="text-red-500 font-bold">✕</span>
                  <span>Prone to sycophancy (agreeing with prompt bias)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-red-500 font-bold">✕</span>
                  <span>Unchallenged premises and unseen blindspots</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-red-500 font-bold">✕</span>
                  <span>Zero independent adversarial fact-checking</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/10 text-center">
              <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 uppercase font-medium">
                Single Point of Cognitive Failure
              </span>
            </div>
          </div>

          {/* Versus Divider for desktop */}
          <div className="lg:col-span-2 flex flex-col items-center justify-center my-2 lg:my-0">
            <div className="w-10 h-10 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-xs font-bold text-indigo-600 dark:text-indigo-400 shadow-md">
              VS
            </div>
          </div>

          {/* Card 2: Multi-Agent AI Debate Simulator (Epistemic Rigor) */}
          <div className="lg:col-span-5 glass-panel rounded-3xl p-6 sm:p-8 border border-indigo-200 dark:border-indigo-500/30 bg-white/95 dark:bg-[#080d1e]/85 flex flex-col justify-between shadow-xl ring-1 ring-indigo-100 dark:ring-0">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-mono uppercase tracking-wider text-indigo-700 dark:text-indigo-300 font-bold bg-indigo-50 dark:bg-indigo-950/40 px-3 py-1 rounded-lg border border-indigo-200 dark:border-indigo-500/30">
                  AI Debate Simulator
                </span>
                <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              </div>

              {/* Visual Pipeline Stack */}
              <div className="space-y-3 my-4">
                <div className="p-3 rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50/70 dark:bg-blue-950/40 text-center font-mono text-xs font-bold text-blue-900 dark:text-blue-200 flex items-center justify-center gap-2 shadow-sm">
                  <Brain className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
                  <span>AI PRO ↔ AI CON</span>
                </div>

                <div className="flex justify-center text-indigo-400">
                  <ArrowDown className="w-3.5 h-3.5" />
                </div>

                <div className="p-3 rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/70 dark:bg-emerald-950/40 text-center font-mono text-xs font-bold text-emerald-900 dark:text-emerald-200 flex items-center justify-center gap-2 shadow-sm">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  <span>CLAIM VERIFICATION & EVIDENCE</span>
                </div>

                <div className="flex justify-center text-indigo-400">
                  <ArrowDown className="w-3.5 h-3.5" />
                </div>

                <div className="p-3 rounded-xl border border-purple-200 dark:border-purple-900/50 bg-purple-50/70 dark:bg-purple-950/40 text-center font-mono text-xs font-bold text-purple-900 dark:text-purple-200 flex items-center justify-center gap-2 shadow-sm">
                  <Scale className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                  <span>INDEPENDENT EVALUATION</span>
                </div>

                <div className="flex justify-center text-indigo-400">
                  <ArrowDown className="w-3.5 h-3.5" />
                </div>

                <div className="p-3 rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/70 dark:bg-amber-950/40 text-center font-mono text-xs font-bold text-amber-900 dark:text-amber-200 flex items-center justify-center gap-2 shadow-sm">
                  <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                  <span>EVIDENCE-GROUNDED SYNTHESIS</span>
                </div>
              </div>

              <div className="border-t border-slate-100 dark:border-white/10 pt-4 space-y-2 text-xs text-slate-700 dark:text-slate-300">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <span>Adversarial dialectic breaks echo chambers</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <span>Every controversial claim verified against citations</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <span>Explicit uncertainty metrics and trade-off mapping</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/10 text-center">
              <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 uppercase font-semibold">
                Multi-Agent Epistemic Verification
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default WhyMultiAgent;

import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Cpu, ShieldCheck, Scale, Sparkles } from 'lucide-react';
import { Button } from '../ui/Button';

export const FeaturesPreview: React.FC = () => {
  const highlights = [
    {
      title: 'Multi-Agent Debate',
      description: 'Structured affirmative and negative perspectives challenge assumptions across dialectical rounds.',
      icon: Cpu,
      badge: 'Bilateral Logic',
      border: 'border-sky-200 dark:border-sky-500/30',
      bg: 'bg-sky-50/50 dark:bg-sky-950/30',
      iconColor: 'text-sky-600 dark:text-sky-400 bg-sky-100 dark:bg-sky-900/40',
    },
    {
      title: 'Evidence Verification',
      description: 'Automated claim extraction cross-verifies factual assertions against retrieved citation sources.',
      icon: ShieldCheck,
      badge: 'Empirical Proof',
      border: 'border-emerald-200 dark:border-emerald-500/30',
      bg: 'bg-emerald-50/50 dark:bg-emerald-950/30',
      iconColor: 'text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/40',
    },
    {
      title: 'Independent Judge',
      description: 'Objective third-party arbitration evaluates fallacies, reasoning coherence, and evidence relevance.',
      icon: Scale,
      badge: 'Zero Bias',
      border: 'border-purple-200 dark:border-purple-500/30',
      bg: 'bg-purple-50/50 dark:bg-purple-950/30',
      iconColor: 'text-purple-700 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/40',
    },
    {
      title: 'Balanced Synthesis',
      description: 'Transparent synthesis detailing genuine consensus, irreducible trade-offs, and epistemic uncertainty.',
      icon: Sparkles,
      badge: 'Nuanced Output',
      border: 'border-amber-200 dark:border-amber-500/30',
      bg: 'bg-amber-50/50 dark:bg-amber-950/30',
      iconColor: 'text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/40',
    },
  ];

  return (
    <section className="py-16 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-3">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            <span>Capabilities Preview</span>
          </div>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
            POWERED BY MULTI-AGENT REASONING
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Moving beyond single-model hallucination into rigorous, verified deliberation.
          </p>
        </div>

        {/* 4 Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          {highlights.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className={`rounded-2xl p-6 border ${item.border} ${item.bg} bg-white/90 dark:bg-[#080d1e]/85 shadow-sm hover:shadow-md transition-all flex flex-col justify-between`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${item.iconColor} shadow-sm`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded-full border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300">
                      {item.badge}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* CTA navigating to /how-it-works */}
        <div className="text-center">
          <Link to="/how-it-works">
            <Button
              variant="outline"
              size="md"
              className="gap-2 font-bold border-indigo-200 dark:border-indigo-500/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/50"
            >
              <span>EXPLORE ALL FEATURES</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
};

export default FeaturesPreview;

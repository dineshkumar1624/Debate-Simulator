import React from 'react';
import {
  Users,
  Repeat,
  Cpu,
  Search,
  CheckCircle,
  Scale,
  Crosshair,
  BookOpen,
  HelpCircle,
  History,
  Network,
  MessageSquarePlus,
} from 'lucide-react';

export const FeaturesGrid: React.FC = () => {
  const features = [
    {
      title: 'Multi-Agent Debate',
      description: 'Opposing specialized AI agents formulate thesis and antithesis to explore contentious topics without bias.',
      icon: Users,
      iconColor: 'text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/40 border-sky-200 dark:border-sky-500/30',
      badge: 'Core Engine',
    },
    {
      title: 'Multi-Round Reasoning',
      description: 'Configurable iterative discourse where agents deepen arguments, expose weak points, and cross-rebut.',
      icon: Repeat,
      iconColor: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-500/30',
      badge: 'Iterative',
    },
    {
      title: 'Multiple LLM Providers',
      description: 'Pit disparate models (OpenAI, Anthropic, Google Gemini) against each other to avoid monolithic perspective collapse.',
      icon: Cpu,
      iconColor: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-500/30',
      badge: 'Provider Agnostic',
    },
    {
      title: 'Evidence Retrieval',
      description: 'Semantic vector retrieval across empirical studies, legal case law, and credible data repositories.',
      icon: Search,
      iconColor: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-500/30',
      badge: 'RAG Grounded',
    },
    {
      title: 'Claim Verification',
      description: 'Automated claim decomposition, isolating factual assertions and assigning veracity confidence scores.',
      icon: CheckCircle,
      iconColor: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-500/30',
      badge: 'Anti-Hallucination',
    },
    {
      title: 'Independent AI Judge',
      description: 'An uncommitted arbiter model evaluating adherence to evidence, fallacy detection, and persuasive rigor.',
      icon: Scale,
      iconColor: 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-500/30',
      badge: 'Impartial',
    },
    {
      title: 'Judge Challenger',
      description: 'An adversarial meta-auditor agent testing the judicial decision for latent bias or unstated assumptions.',
      icon: Crosshair,
      iconColor: 'text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-950/40 border-pink-200 dark:border-pink-500/30',
      badge: 'Meta-Audit',
    },
    {
      title: 'Source Citations',
      description: 'Direct verifiable excerpts linked to every empirical premise, allowing humans to audit the primary literature.',
      icon: BookOpen,
      iconColor: 'text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/40 border-cyan-200 dark:border-cyan-500/30',
      badge: 'Traceability',
    },
    {
      title: 'Uncertainty Analysis',
      description: 'Quantified epistemic uncertainty bands indicating where facts end and subjective value judgments begin.',
      icon: HelpCircle,
      iconColor: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-500/30',
      badge: 'Probabilistic',
    },
    {
      title: 'Debate History',
      description: 'Complete session persistence allowing replay, comparative analysis, and tracking argument drift over time.',
      icon: History,
      iconColor: 'text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700',
      badge: 'Audit Trail',
    },
    {
      title: 'Argument Visualization',
      description: 'Interactive dialectical graph mapping supporting premises, attack vectors, and evidentiary grounding.',
      icon: Network,
      iconColor: 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-500/30',
      badge: 'Graph Topology',
    },
    {
      title: 'Human Feedback',
      description: 'Human-in-the-loop steering allowing participants to challenge agents, inject constraints, or arbitrate rounds.',
      icon: MessageSquarePlus,
      iconColor: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-500/30',
      badge: 'Steerable',
    },
  ];

  return (
    <section id="features" className="py-20 relative bg-[#FAFAFC] dark:bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            Capabilities
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
            ENGINEERED FOR DIALECTIC RIGOR
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
            Every module is tailored to dismantle sycophancy, surface overlooked trade-offs, and ground claims in evidence.
          </p>
        </div>

        {/* 12-Card Grid with varied card styling and micro-interactions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {features.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="glass-card rounded-2xl p-5 border border-slate-200/90 dark:border-white/10 hover:border-indigo-300 dark:hover:border-indigo-500/40 transition-all duration-300 group flex flex-col justify-between bg-white/95 dark:bg-[#080d1e]/85 shadow-sm hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${item.iconColor} transition-transform group-hover:scale-110 duration-200 shadow-sm`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-mono uppercase font-semibold px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">
                      {item.badge}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors tracking-tight">
                    {item.title}
                  </h3>

                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                    {item.description}
                  </p>
                </div>

                <div className="pt-4 mt-3 border-t border-slate-100 dark:border-white/10 flex items-center justify-between text-[11px] font-mono text-slate-400 dark:text-slate-500">
                  <span>Mod. 0{idx + 1}</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-bold group-hover:translate-x-1 transition-transform duration-200">→</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default FeaturesGrid;

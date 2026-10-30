import React from 'react';
import { Layout, Cpu, GitBranch, Database, ShieldAlert } from 'lucide-react';

export const TechnologyStack: React.FC = () => {
  const groups = [
    {
      category: 'FRONTEND',
      icon: Layout,
      color: 'text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-500/30 bg-sky-50 dark:bg-sky-950/40',
      items: [
        { name: 'React 18', desc: 'Component hierarchy & functional state' },
        { name: 'TypeScript', desc: 'Strict typing & schema contracts' },
        { name: 'Vite 6', desc: 'Fast HMR & optimized production bundling' },
        { name: 'Tailwind CSS', desc: 'Precision light & dark futuristic design system' },
        { name: 'shadcn/ui', desc: 'Accessible, unstyled modular primitives' },
      ],
    },
    {
      category: 'AI MODELS',
      icon: Cpu,
      color: 'text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40',
      items: [
        { name: 'OpenAI (GPT-4o)', desc: 'Complex reasoning & dialectic thesis' },
        { name: 'Google (Gemini 1.5/2.0)', desc: 'Deep synthesis & large context lookup' },
        { name: 'Anthropic (Claude 3.5)', desc: 'Nuanced counterargument & arbitration' },
      ],
    },
    {
      category: 'ORCHESTRATION',
      icon: GitBranch,
      color: 'text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-500/30 bg-purple-50 dark:bg-purple-950/40',
      items: [
        { name: 'LangGraph', desc: 'Cyclic state graph & multi-agent routing' },
      ],
    },
    {
      category: 'DATA & RETRIEVAL',
      icon: Database,
      color: 'text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40',
      items: [
        { name: 'PostgreSQL', desc: 'Relational storage for debate transcripts' },
        { name: 'pgvector', desc: 'High-dimensional embeddings for citations' },
        { name: 'Redis', desc: 'Real-time pub/sub & session cache' },
      ],
    },
    {
      category: 'EVALUATION & RIGOR',
      icon: ShieldAlert,
      color: 'text-pink-600 dark:text-pink-400 border-pink-200 dark:border-pink-500/30 bg-pink-50 dark:bg-pink-950/40',
      items: [
        { name: 'RAGAS', desc: 'Faithfulness & answer relevancy metrics' },
        { name: 'DeepEval', desc: 'Unit testing agent reasoning & hallucinations' },
      ],
    },
  ];

  return (
    <section id="technology" className="py-24 relative bg-[#F4F8FC] dark:bg-transparent border-y border-sky-100/50 dark:border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            Architecture Blueprint
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
            BUILT FOR MULTI-AGENT AI
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
            Constructed with a decoupled, enterprise-ready technology stack calibrated for multi-agent reasoning, fast asynchronous execution, and rigorous verification.
          </p>

          <div className="inline-block pt-1">
            <span className="text-xs font-mono px-3.5 py-1 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-indigo-700 dark:text-indigo-400 font-bold uppercase tracking-wider shadow-sm">
              PLANNED ARCHITECTURE
            </span>
          </div>
        </div>

        {/* Grouped Technology Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map((group) => {
            const Icon = group.icon;
            return (
              <div
                key={group.category}
                className="glass-card rounded-3xl p-6 border border-slate-200/90 dark:border-white/10 hover:border-indigo-300 dark:hover:border-indigo-500/40 bg-white/95 dark:bg-[#080d1e]/85 shadow-sm hover:shadow-md flex flex-col justify-between transition-all"
              >
                <div>
                  <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-slate-100 dark:border-white/10">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${group.color} shadow-sm`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-mono font-bold tracking-wider text-slate-800 dark:text-slate-200 uppercase">
                      {group.category}
                    </span>
                  </div>

                  <div className="space-y-3.5">
                    {group.items.map((tech) => (
                      <div key={tech.name} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800">
                        <div className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
                          {tech.name}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-normal">
                          {tech.desc}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 dark:border-white/10 text-[10px] font-mono text-slate-400 dark:text-slate-500 uppercase text-right font-medium">
                  Module Planned
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default TechnologyStack;

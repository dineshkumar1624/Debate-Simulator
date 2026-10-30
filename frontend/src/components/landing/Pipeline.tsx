import React from 'react';
import {
  HelpCircle,
  Cpu,
  Repeat,
  FileSearch,
  Database,
  ShieldAlert,
  Scale,
  Crosshair,
  Sparkles,
} from 'lucide-react';

export const Pipeline: React.FC = () => {
  const nodes = [
    {
      label: 'USER QUESTION',
      stage: 'Input',
      description: 'Proposition formulation, contextual constraints, and debate parameters initialization',
      icon: HelpCircle,
      accent: 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800',
      badge: 'User Ingestion',
    },
    {
      label: 'QUERY ANALYZER',
      stage: 'Analysis',
      description: 'Intent decomposition, semantic scoping, and identifying key contentious sub-questions',
      icon: Cpu,
      accent: 'border-sky-200 dark:border-sky-500/30 text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/40',
      badge: 'NLP Parsing',
    },
    {
      label: 'AI PRO  ↔  AI CON',
      stage: 'Debaters',
      description: 'Multi-round dialectic generation, structured thesis formulation, and iterative rebuttal',
      icon: Repeat,
      accent: 'border-blue-200 dark:border-blue-500/30 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40',
      badge: 'Agent Exchange',
    },
    {
      label: 'CLAIM EXTRACTION',
      stage: 'Evidence',
      description: 'Automated claim decomposition extracting verifiable empirical assertions from speech turns',
      icon: FileSearch,
      accent: 'border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40',
      badge: 'Information Extraction',
    },
    {
      label: 'EVIDENCE RETRIEVAL',
      stage: 'Evidence',
      description: 'Hybrid dense-sparse vector search across academic papers, case law, and empirical databases',
      icon: Database,
      accent: 'border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40',
      badge: 'Semantic Vector Retrieval',
    },
    {
      label: 'FACT CHECKER',
      stage: 'Evidence',
      description: 'Cross-verifying extracted claims against retrieved citation excerpts and assigning veracity labels',
      icon: ShieldAlert,
      accent: 'border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40',
      badge: 'NLI Verification',
    },
    {
      label: 'INDEPENDENT JUDGE',
      stage: 'Evaluation',
      description: 'Objective third-party arbitration evaluating argument validity, rhetoric, and empirical grounding',
      icon: Scale,
      accent: 'border-purple-200 dark:border-purple-500/30 text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40',
      badge: 'Judicial Scoring',
    },
    {
      label: 'JUDGE CHALLENGER',
      stage: 'Evaluation',
      description: 'Adversarial auditor model testing the verdict for latent biases, omissions, or reasoning flaws',
      icon: Crosshair,
      accent: 'border-purple-200 dark:border-purple-500/30 text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40',
      badge: 'Meta-Evaluation',
    },
    {
      label: 'FINAL SYNTHESIS',
      stage: 'Output',
      description: 'Balanced, evidence-grounded summary detailing consensus, remaining tensions, and uncertainty levels',
      icon: Sparkles,
      accent: 'border-amber-200 dark:border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40',
      badge: 'Synthesized Report',
    },
  ];

  return (
    <section id="pipeline" className="py-24 relative bg-[#FAF9FE] dark:bg-transparent border-y border-purple-100/50 dark:border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            Architecture Blueprint
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
            THE REASONING PIPELINE
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
            Every query navigates a multi-agent cognitive architecture designed to prevent sycophancy and ground assertions in facts.
          </p>
        </div>

        {/* Vertical Pipeline with Downward Flowing Line and Cards */}
        <div className="max-w-3xl mx-auto space-y-3 relative">
          {nodes.map((node, index) => {
            const Icon = node.icon;
            return (
              <div key={node.label} className="relative group">
                <div className="glass-panel p-4 sm:p-5 rounded-2xl border border-slate-200/90 dark:border-white/10 hover:border-indigo-300 dark:hover:border-indigo-500/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all duration-200 bg-white/95 dark:bg-[#080d1e]/85 shadow-sm hover:shadow-md">
                  <div className="flex items-center gap-4">
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center border ${node.accent} shrink-0 shadow-sm`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="text-sm font-bold text-slate-900 dark:text-white tracking-wider font-mono">
                          {node.label}
                        </span>
                        <span className="text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">
                          {node.badge}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                        {node.description}
                      </p>
                    </div>
                  </div>

                  <div className="self-end sm:self-center shrink-0">
                    <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 font-medium">
                      Step 0{index + 1}
                    </span>
                  </div>
                </div>

                {/* Connecting arrow with downward light flow */}
                {index < nodes.length - 1 && (
                  <div className="flex justify-center my-1.5">
                    <div className="w-[2px] h-4 bg-gradient-to-b from-indigo-400 to-purple-400 opacity-60" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Pipeline;

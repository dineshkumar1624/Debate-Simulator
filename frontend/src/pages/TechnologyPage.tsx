import React from 'react';
import { Link } from 'react-router-dom';
import {
  Layout,
  Cpu,
  GitBranch,
  Database,
  ShieldAlert,
  ArrowRight,
  Info,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Button } from '../components/ui/Button';

export const TechnologyPage: React.FC = () => {
  const categories = [
    {
      name: 'FRONTEND',
      icon: Layout,
      color: 'text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-500/40 bg-sky-50 dark:bg-sky-950/40',
      description: 'Modern, responsive, accessible presentation tier with real-time state visualization.',
      technologies: [
        { name: 'React', desc: 'Component hierarchy, modular UI composition, and declarative render cycles.', status: 'Active' },
        { name: 'TypeScript', desc: 'Strict compile-time type safety and API contract validation.', status: 'Active' },
        { name: 'Vite', desc: 'Next-generation frontend tooling with lightning-fast HMR and optimized builds.', status: 'Active' },
        { name: 'Tailwind CSS', desc: 'Utility-first styling with unified dark and light mode design systems.', status: 'Active' },
        { name: 'shadcn/ui', desc: 'Unstyled, accessible primitives conforming to WAI-ARIA standards.', status: 'Active' },
      ],
    },
    {
      name: 'AI MODELS',
      icon: Cpu,
      color: 'text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/40 bg-indigo-50 dark:bg-indigo-950/40',
      description: 'Multi-provider foundation models selected for complementary reasoning traits.',
      technologies: [
        { name: 'OpenAI (GPT-4o)', desc: 'High dialectical agility, structured thesis formulation, and logical rigor.', status: 'Planned' },
        { name: 'Gemini (1.5/2.0 Pro)', desc: 'Large context retrieval, deep cross-source synthesis, and judicial neutrality.', status: 'Planned' },
        { name: 'Claude (3.5 Sonnet)', desc: 'Nuanced counterargument generation, fallacy detection, and epistemic calibration.', status: 'Planned' },
      ],
    },
    {
      name: 'ORCHESTRATION',
      icon: GitBranch,
      color: 'text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-500/40 bg-purple-50 dark:bg-purple-950/40',
      description: 'Cyclic state graph coordination governing multi-agent conversational turns.',
      technologies: [
        { name: 'LangGraph', desc: 'Cyclic, multi-agent state machines managing adversarial turn-taking, branching paths, and arbitration checkpoints.', status: 'Planned' },
      ],
    },
    {
      name: 'DATA & STORAGE',
      icon: Database,
      color: 'text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/40 bg-emerald-50 dark:bg-emerald-950/40',
      description: 'Hybrid relational and vector persistence for transcripts and citation embeddings.',
      technologies: [
        { name: 'PostgreSQL', desc: 'ACID-compliant relational storage for debate history, transcripts, and judicial scorecards.', status: 'Planned' },
        { name: 'pgvector', desc: 'High-dimensional vector similarity indexing for real-time semantic citation retrieval.', status: 'Planned' },
        { name: 'Redis', desc: 'In-memory pub/sub message broker for live streaming agent reasoning turns to clients.', status: 'Planned' },
      ],
    },
    {
      name: 'EVALUATION & RIGOR',
      icon: ShieldAlert,
      color: 'text-pink-600 dark:text-pink-400 border-pink-200 dark:border-pink-500/40 bg-pink-50 dark:bg-pink-950/40',
      description: 'Automated evaluation pipelines auditing factual grounding and reasoning consistency.',
      technologies: [
        { name: 'RAGAS', desc: 'Evaluation framework benchmarking retrieval context recall, faithfulness, and answer relevancy.', status: 'Planned' },
        { name: 'DeepEval', desc: 'Unit testing suite measuring hallucination rates, bias drift, and judicial consistency across debate runs.', status: 'Planned' },
      ],
    },
  ];

  return (
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-16">
      {/* Breadcrumb back link */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-white/10">
        <Link
          to="/how-it-works#built-with"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 font-semibold"
        >
          <ArrowRight className="w-3.5 h-3.5 rotate-180" />
          <span>← Back to How It Works</span>
        </Link>
        <span className="text-[11px] font-mono text-slate-400">Infrastructure Stack</span>
      </div>

      {/* Page Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <span>Infrastructure Overview</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
          TECHNOLOGY STACK
        </h1>
        <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
          Built for Multi-Agent AI.
        </p>

        {/* Planned Architecture Callout Badge (Requirement 15) */}
        <div className="pt-2">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-700/60 text-amber-800 dark:text-amber-200 text-xs font-mono font-bold uppercase tracking-wider shadow-sm">
            <Info className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span>PLANNED ARCHITECTURE</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 max-w-xl mx-auto">
            The frontend interface and API schemas are implemented. Backend orchestration, databases, and LLM integrations reflect the target production deployment.
          </p>
        </div>
      </div>

      {/* Categorized Technology Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map((category) => {
          const Icon = category.icon;
          return (
            <div
              key={category.name}
              className="glass-card rounded-3xl p-6 sm:p-7 border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#080d1e]/85 shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                {/* Category Header */}
                <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100 dark:border-white/10">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${category.color} shadow-sm`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold font-mono tracking-wider text-slate-900 dark:text-white uppercase">
                        {category.name}
                      </h2>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    {category.technologies.length} components
                  </span>
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-400 mb-5 leading-relaxed">
                  {category.description}
                </p>

                {/* Items */}
                <div className="space-y-3">
                  {category.technologies.map((tech) => (
                    <div
                      key={tech.name}
                      className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 space-y-1 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 dark:text-white">
                          {tech.name}
                        </span>
                        <span
                          className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                            tech.status === 'Active'
                              ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-700/60'
                              : 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-700/60'
                          }`}
                        >
                          {tech.status === 'Active' ? (
                            <CheckCircle className="w-2.5 h-2.5" />
                          ) : (
                            <Clock className="w-2.5 h-2.5" />
                          )}
                          <span>{tech.status}</span>
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-snug">
                        {tech.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer CTA */}
      <div className="text-center pt-6 border-t border-slate-200 dark:border-white/10">
        <Link to="/debate">
          <Button
            size="lg"
            className="gap-2.5 font-bold shadow-lg shadow-indigo-600/25 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white"
          >
            <span>LAUNCH DEBATE SIMULATION</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default TechnologyPage;

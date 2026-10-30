import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Cpu,
  GitBranch,
  Brain,
  FileSearch,
  Database,
  ShieldAlert,
  Scale,
  Crosshair,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Layers,
  Code2,
  ChevronRight,
} from 'lucide-react';
import { Button } from '../components/ui/Button';

interface PipelineComponent {
  id: number;
  name: string;
  category: 'Input' | 'Orchestration' | 'Agents' | 'Evidence' | 'Evaluation' | 'Output';
  summary: string;
  icon: React.ElementType;
  inputs: string[];
  outputs: string[];
  guarantees: string;
  accent: string;
  badgeColor: string;
}

export const PipelinePage: React.FC = () => {
  const [activeId, setActiveId] = useState<number>(1);

  const components: PipelineComponent[] = [
    {
      id: 1,
      name: 'Query Analyzer',
      category: 'Input',
      summary: 'Decomposes raw user propositions into epistemological dimensions, identifies core contentious claims, and bounds the scope of the debate.',
      icon: Cpu,
      inputs: ['Raw proposition string', 'Context constraints', 'Debate rules'],
      outputs: ['Structured debate schema', 'Key sub-questions', 'Semantic intent vectors'],
      guarantees: 'Zero prompt-injection leakage; validates proposition polarity before routing.',
      accent: 'border-sky-300 dark:border-sky-500/50 text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/40',
      badgeColor: 'bg-sky-50 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-500/40',
    },
    {
      id: 2,
      name: 'Debate Orchestrator',
      category: 'Orchestration',
      summary: 'Stateful LangGraph coordinator governing dialectic rounds, speaking order, time quotas, and turn-taking protocol between opposing debaters.',
      icon: GitBranch,
      inputs: ['Debate parameters', 'Round limits', 'Current turn state'],
      outputs: ['Active agent trigger', 'Context window slice', 'State checkpoints'],
      guarantees: 'Deterministic execution ordering with fault-tolerant checkpointing.',
      accent: 'border-indigo-300 dark:border-indigo-500/50 text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40',
      badgeColor: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-500/40',
    },
    {
      id: 3,
      name: 'AI PRO',
      category: 'Agents',
      summary: 'Affirmative debater agent tasked with defending the proposition through empirical evidence, logical deduction, and direct rebuttal of negative challenges.',
      icon: Brain,
      inputs: ['Proposition schema', 'Opponent counterarguments', 'Retrieved citations'],
      outputs: ['Affirmative claims', 'Constructive speeches', 'Rebuttals'],
      guarantees: 'Constrained to affirmative stance without internal vacillation.',
      accent: 'border-blue-300 dark:border-blue-500/50 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40',
      badgeColor: 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-500/40',
    },
    {
      id: 4,
      name: 'AI CON',
      category: 'Agents',
      summary: 'Negative debater agent tasked with identifying systemic vulnerabilities, fallacies, counter-examples, and unstated risks in the affirmative case.',
      icon: Brain,
      inputs: ['Proposition schema', 'Affirmative speech turns', 'Retrieved citations'],
      outputs: ['Negative counterarguments', 'Risk taxonomies', 'Critiques'],
      guarantees: 'Strictly bounded to adversarial negative stance to prevent premature consensus.',
      accent: 'border-pink-300 dark:border-pink-500/50 text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-950/40',
      badgeColor: 'bg-pink-50 text-pink-700 dark:bg-pink-950/60 dark:text-pink-300 border-pink-200 dark:border-pink-500/40',
    },
    {
      id: 5,
      name: 'Claim Extractor',
      category: 'Evidence',
      summary: 'Information extraction model isolating atomic empirical statements from rhetorical narrative for independent verification.',
      icon: FileSearch,
      inputs: ['Raw debate turns', 'Natural language arguments'],
      outputs: ['Atomic claim triplets', 'Entities and predicates', 'Confidence flags'],
      guarantees: 'High precision claim bounding; filters opinions from testable assertions.',
      accent: 'border-emerald-300 dark:border-emerald-500/50 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40',
      badgeColor: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/40',
    },
    {
      id: 6,
      name: 'Evidence Retriever',
      category: 'Evidence',
      summary: 'Dense-sparse hybrid search engine pulling relevant scientific papers, policy reports, and legal precedents from pgvector knowledge bases.',
      icon: Database,
      inputs: ['Atomic claim queries', 'Temporal relevance filters'],
      outputs: ['Top-k passage excerpts', 'DOI citations', 'Vector similarity scores'],
      guarantees: 'Source attribution tracking with verifiable metadata and timestamps.',
      accent: 'border-emerald-300 dark:border-emerald-500/50 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40',
      badgeColor: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/40',
    },
    {
      id: 7,
      name: 'Fact Checker',
      category: 'Evidence',
      summary: 'Natural Language Inference (NLI) model testing entailment, neutrality, or contradiction between extracted claims and retrieved evidence.',
      icon: ShieldAlert,
      inputs: ['Extracted claims', 'Retrieved source passages'],
      outputs: ['Veracity scores (Supported, Refuted, Unverified)', 'Contradiction notes'],
      guarantees: 'Penalizes ungrounded hallucinations before evaluation phase.',
      accent: 'border-teal-300 dark:border-teal-500/50 text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/40',
      badgeColor: 'bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border-teal-200 dark:border-teal-500/40',
    },
    {
      id: 8,
      name: 'Independent Judge',
      category: 'Evaluation',
      summary: 'Impartial judicial agent scoring both debaters on factual grounding, logical consistency, responsiveness to rebuttals, and rhetorical validity.',
      icon: Scale,
      inputs: ['Full debate transcripts', 'Fact-check audit logs', 'Scoring rubric'],
      outputs: ['Point allocations', 'Sub-dimension breakdown', 'Provisional verdict'],
      guarantees: 'Zero bias policy; prompt isolated from debater identities to avoid favoritism.',
      accent: 'border-purple-300 dark:border-purple-500/50 text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40',
      badgeColor: 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-500/40',
    },
    {
      id: 9,
      name: 'Judge Challenger',
      category: 'Evaluation',
      summary: 'Adversarial meta-evaluator stress-testing the Judge’s reasoning for potential confirmation bias, unaddressed nuances, or arbitrary scoring.',
      icon: Crosshair,
      inputs: ['Provisional judicial verdict', 'Transcript audit'],
      outputs: ['Bias critique', 'Challenge flags', 'Confidence rating'],
      guarantees: 'Detects judge blind spots and forces judicial re-examination if necessary.',
      accent: 'border-purple-300 dark:border-purple-500/50 text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40',
      badgeColor: 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-500/40',
    },
    {
      id: 10,
      name: 'Final Synthesizer',
      category: 'Output',
      summary: 'Generates the final comprehensive report integrating verified claims, irreducible policy tensions, consensus points, and epistemic uncertainty metrics.',
      icon: Sparkles,
      inputs: ['Certified transcripts', 'Audited judge verdict', 'Evidence logs'],
      outputs: ['Executive synthesis', 'Confidence intervals', 'Nuance matrix'],
      guarantees: 'Produces balanced, non-polarized conclusions grounded in verified evidence.',
      accent: 'border-amber-300 dark:border-amber-500/50 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40',
      badgeColor: 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-500/40',
    },
  ];

  const activeComponent = components.find((c) => c.id === activeId) || components[0];
  const ActiveIcon = activeComponent.icon;

  return (
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-16">
      {/* Breadcrumb back link */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-white/10">
        <Link
          to="/how-it-works#behind-the-debate"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 font-semibold"
        >
          <ChevronRight className="w-3.5 h-3.5 rotate-180" />
          <span>← Back to How It Works</span>
        </Link>
        <span className="text-[11px] font-mono text-slate-400">Technical Deep Dive</span>
      </div>

      {/* Page Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <span>Technical Architecture</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
          THE REASONING PIPELINE
        </h1>
        <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
          From a user question to an evidence-grounded synthesis.
        </p>
      </div>

      {/* Interactive Pipeline Explorer: 10 Components on Left, Deep Details on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: List of 10 Components */}
        <div className="lg:col-span-5 space-y-2.5">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/10 mb-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Pipeline Stages (Click to Inspect)
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              10 Components
            </span>
          </div>

          <div className="space-y-2">
            {components.map((c) => {
              const Icon = c.icon;
              const isSelected = c.id === activeId;
              return (
                <button
                  key={c.id}
                  onClick={() => setActiveId(c.id)}
                  type="button"
                  className={`w-full text-left p-3.5 rounded-2xl border transition-all duration-200 flex items-center justify-between group ${
                    isSelected
                      ? 'bg-white dark:bg-[#0c1228] border-indigo-400 dark:border-indigo-500 shadow-md ring-2 ring-indigo-500/20'
                      : 'bg-white/80 dark:bg-[#080d1e]/60 border-slate-200/80 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-bold w-6 text-slate-400 dark:text-slate-500">
                      {String(c.id).padStart(2, '0')}
                    </span>
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center border ${c.accent} shadow-sm`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white leading-tight">
                        {c.name}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 leading-none mt-0.5">
                        {c.category}
                      </div>
                    </div>
                  </div>

                  <ChevronRight className={`w-4 h-4 transition-transform ${isSelected ? 'text-indigo-600 dark:text-indigo-400 translate-x-1' : 'text-slate-400 dark:text-slate-600'}`} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Detailed Component Inspector */}
        <div className="lg:col-span-7 lg:sticky lg:top-24 lg:self-start">
          <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#080d1e]/90 shadow-xl space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-slate-200 dark:border-white/10">
              <div className="flex items-center gap-3.5">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${activeComponent.accent} shadow-md`}>
                  <ActiveIcon className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-400">
                      Component {String(activeComponent.id).padStart(2, '0')} of 10
                    </span>
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${activeComponent.badgeColor}`}>
                      {activeComponent.category}
                    </span>
                  </div>
                  <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white mt-0.5">
                    {activeComponent.name}
                  </h2>
                </div>
              </div>
            </div>

            {/* Description */}
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                Operational Role
              </h3>
              <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed font-medium">
                {activeComponent.summary}
              </p>
            </div>

            {/* Inputs & Outputs Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 space-y-2">
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300 flex items-center gap-1.5">
                  <Code2 className="w-3.5 h-3.5" />
                  Inputs Received
                </span>
                <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                  {activeComponent.inputs.map((inItem, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-sky-500 font-bold">•</span>
                      <span>{inItem}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 space-y-2">
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  Outputs Emitted
                </span>
                <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                  {activeComponent.outputs.map((outItem, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{outItem}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Verification Guarantee */}
            <div className="p-4 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200/80 dark:border-indigo-500/30 space-y-1.5">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                Architectural Guarantee
              </span>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
                {activeComponent.guarantees}
              </p>
            </div>

            {/* Navigation / Action */}
            <div className="pt-2 flex items-center justify-between border-t border-slate-200 dark:border-white/10">
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={activeId <= 1}
                  onClick={() => setActiveId((prev) => Math.max(1, prev - 1))}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-mono font-medium disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  ← Prev
                </button>
                <button
                  type="button"
                  disabled={activeId >= 10}
                  onClick={() => setActiveId((prev) => Math.min(10, prev + 1))}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-mono font-medium disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Next →
                </button>
              </div>

              <Link to="/debate">
                <Button size="sm" className="gap-2 font-bold bg-indigo-600 hover:bg-indigo-500 text-white">
                  <span>TEST IN DEBATE</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PipelinePage;

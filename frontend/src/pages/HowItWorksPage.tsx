import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  HelpCircle,
  Cpu,
  Brain,
  ShieldCheck,
  Scale,
  Sparkles,
  ArrowRight,
  GitBranch,
  FileSearch,
  Database,
  ChevronRight,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { NeuralCoreView } from '../components/common/NeuralCoreView';

interface StageData {
  num: string;
  action: string;
  title: string;
  evolution: string;
  desc: string;
  icon: React.ElementType;
  glowColor: 'indigo' | 'cyan' | 'purple' | 'amber' | 'neutral';
}

const STAGES: StageData[] = [
  {
    num: '01',
    action: 'UPLOAD',
    title: 'Document enters the platform.',
    evolution: 'Core ingests document container (PDF, DOCX, TXT).',
    desc: 'You upload a research paper, legal brief, or technical report. The system scans file integrity, page bounds, and structural layout.',
    icon: HelpCircle,
    glowColor: 'cyan',
  },
  {
    num: '02',
    action: 'UNDERSTAND',
    title: 'Text extraction & semantic chunking.',
    evolution: 'Core isolates sections, headings, claims, and data tables.',
    desc: 'The document is indexed into searchable page units. Atomic claims and quantitative benchmarks are tagged with exact line and page numbers.',
    icon: Cpu,
    glowColor: 'indigo',
  },
  {
    num: '03',
    action: 'GROUND',
    title: 'Opposing agents receive identical context.',
    evolution: 'AI PRO and AI CON synchronized to the same document ground truth.',
    desc: 'Both debating neural models are locked to the uploaded document context. Neither agent can fabricate outside facts without citation.',
    icon: ShieldCheck,
    glowColor: 'cyan',
  },
  {
    num: '04',
    action: 'DEBATE',
    title: 'Adversarial clash with page citations.',
    evolution: 'Bilateral harmonic resonance as opposing agents clash.',
    desc: 'AI PRO builds supporting arguments citing specific pages; AI CON attacks methodological flaws and limitations citing contrary passages.',
    icon: Brain,
    glowColor: 'purple',
  },
  {
    num: '05',
    action: 'JUDGE',
    title: 'Independent AI Judge evaluates fidelity.',
    evolution: 'Independent Judge core awakens and scores coherence & citation accuracy.',
    desc: 'An impartial third-party neural arbiter evaluates whether claims match the text, tests for hallucinations, and audits counterargument validity.',
    icon: Scale,
    glowColor: 'indigo',
  },
  {
    num: '06',
    action: 'SYNTHESIZE',
    title: 'Final citation-grounded synthesis.',
    evolution: 'Balanced equilibrium crystallized with exact source references.',
    desc: 'The system generates a balanced conclusion detailing confirmed claims, highlighted limitations, unhedged uncertainties, and page references.',
    icon: Sparkles,
    glowColor: 'amber',
  },
];

interface PipelineNode {
  name: string;
  role: string;
  category: string;
  detail: string;
  icon: React.ElementType;
}

const PIPELINE_NODES: PipelineNode[] = [
  {
    name: 'Query Analyzer',
    role: 'Decomposes proposition',
    category: 'Input Phase',
    detail: 'Isolates core contentious assertions and bounds conversational polarity before routing.',
    icon: Cpu,
  },
  {
    name: 'Debate Orchestrator',
    role: 'Turn-taking state machine',
    category: 'Orchestration',
    detail: 'LangGraph-inspired cyclic coordinator managing speaking orders, speech limits, and turn handoffs.',
    icon: GitBranch,
  },
  {
    name: 'AI PRO',
    role: 'Affirmative Case',
    category: 'Debaters',
    detail: 'Defends the thesis using deductive reasoning, empirical evidence, and constructive arguments.',
    icon: Brain,
  },
  {
    name: 'AI CON',
    role: 'Negative Case',
    category: 'Debaters',
    detail: 'Challenges underlying assumptions, surfaces edge cases, and identifies systemic failure modes.',
    icon: Brain,
  },
  {
    name: 'Claim Extraction',
    role: 'Isolates empirical claims',
    category: 'Evidence',
    detail: 'Transforms rhetorical statements into atomic, testable premise triplets for fact-checking.',
    icon: FileSearch,
  },
  {
    name: 'Evidence Retrieval',
    role: 'Vector knowledge search',
    category: 'Evidence',
    detail: 'Queries semantic embeddings across scientific literature, legal precedents, and empirical datasets.',
    icon: Database,
  },
  {
    name: 'Fact Checking',
    role: 'NLI Entailment verification',
    category: 'Evidence',
    detail: 'Scores claims as Supported, Refuted, or Unverified using natural language inference.',
    icon: ShieldCheck,
  },
  {
    name: 'Independent Judge',
    role: 'Third-party arbitration',
    category: 'Evaluation',
    detail: 'Scores reasoning validity, filters fallacies, and benchmarks dialectical equilibrium.',
    icon: Scale,
  },
  {
    name: 'Final Synthesizer',
    role: 'Balanced conclusion output',
    category: 'Synthesis',
    detail: 'Crystallizes bilateral tensions into transparent agreements, disagreements, and trade-offs.',
    icon: Sparkles,
  },
];

export const HowItWorksPage: React.FC = () => {
  const [activeStageIdx, setActiveStageIdx] = useState<number>(0);
  const [selectedPipelineNode, setSelectedPipelineNode] = useState<number>(0);

  const activeStage = STAGES[activeStageIdx];
  const activeNode = PIPELINE_NODES[selectedPipelineNode];

  return (
    <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-20">
      {/* 1. Page Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <span>COGNITIVE REASONING PROCESS</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-[#0F172A] dark:text-white tracking-tight">
          HOW AI DEBATE WORKS
        </h1>
        <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
          From a single proposition to bilateral debate, empirical verification, and an independent judicial synthesis.
        </p>
      </div>

      {/* 2. THE 6-STAGE EVOLVING NEURAL EXPERIENCE (Section 19) */}
      <div className="space-y-8">
        <div className="flex items-center justify-between border-b border-slate-200/80 dark:border-white/10 pb-4">
          <div>
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              THE SIX DELIBERATION STAGES
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Interactive evolution of the AI Neural Core through the reasoning lifecycle.
            </p>
          </div>
          <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400 font-bold px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-500/30">
            Stage {activeStage.num} of 06
          </span>
        </div>

        {/* Dynamic Interactive Stage Viewer */}
        <div className="glass-panel rounded-3xl p-6 sm:p-10 border border-slate-200/80 dark:border-white/10 bg-white/90 dark:bg-[#070a16]/90 shadow-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left: Evolving 3D AI Neural Core */}
            <div className="lg:col-span-5 flex flex-col items-center justify-center p-6 rounded-2xl bg-slate-50/50 dark:bg-[#040714]/60 border border-slate-200/60 dark:border-white/5 relative overflow-hidden">
              <NeuralCoreView
                size="lg"
                stageIndex={activeStageIdx}
                state={activeStageIdx === 4 ? 'analyzing' : activeStageIdx === 2 ? 'debating' : activeStageIdx === 5 ? 'synthesizing' : 'idle'}
                glowColor={activeStage.glowColor}
              />

              <div className="mt-4 text-center">
                <span className="text-[10px] font-mono font-bold tracking-widest uppercase px-3 py-1 rounded-full bg-slate-200/70 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  {activeStage.num} • {activeStage.action}
                </span>
                <p className="text-[11px] font-mono text-indigo-500 mt-2">
                  {activeStage.evolution}
                </p>
              </div>
            </div>

            {/* Right: Stage Detail & Stage Switcher */}
            <div className="lg:col-span-7 space-y-6">
              <div className="space-y-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  STAGE {activeStage.num} — {activeStage.action}
                </span>
                <h3 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white leading-snug">
                  {activeStage.title}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                  {activeStage.desc}
                </p>
              </div>

              {/* Six Stages Pill Stepper */}
              <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-white/5">
                <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold">
                  Select Stage to Observe Core:
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {STAGES.map((st, idx) => {
                    const isSelected = idx === activeStageIdx;
                    return (
                      <button
                        key={st.num}
                        type="button"
                        onClick={() => setActiveStageIdx(idx)}
                        className={`p-2.5 rounded-xl text-left border text-xs font-mono transition-all ${
                          isSelected
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-600/30'
                            : 'bg-slate-100/70 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 border-slate-200/80 dark:border-slate-800 hover:border-indigo-300'
                        }`}
                      >
                        <div className="font-bold flex items-center justify-between">
                          <span>{st.num} {st.action}</span>
                          {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. BEHIND THE DEBATE — PIPELINE NEURAL FLOW (Section 20) */}
      <div id="behind-the-debate" className="space-y-8 scroll-mt-24">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-500/30 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-bold uppercase">
            <span>Section 20 • Architecture</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-[#0F172A] dark:text-white tracking-tight">
            BEHIND THE DEBATE
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
            Multi-agent orchestrator pipeline tracing data from query intake through arbitration.
          </p>
        </div>

        {/* Interactive Neural Flow Nodes */}
        <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200/80 dark:border-white/10 bg-white/95 dark:bg-[#070a16]/95 shadow-xl space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 gap-2">
            {PIPELINE_NODES.map((node, idx) => {
              const isSelected = idx === selectedPipelineNode;
              const Icon = node.icon;
              return (
                <button
                  key={node.name}
                  type="button"
                  onClick={() => setSelectedPipelineNode(idx)}
                  className={`p-3 rounded-2xl border text-center transition-all flex flex-col items-center justify-between min-h-[110px] ${
                    isSelected
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-500 shadow-md shadow-indigo-500/20 ring-2 ring-indigo-400/30 text-slate-900 dark:text-white'
                      : 'bg-slate-50/70 dark:bg-slate-900/50 border-slate-200/70 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                  }`}
                >
                  <span className="text-[9px] font-mono text-slate-400 font-semibold">0{idx + 1}</span>
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center my-1 ${
                    isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-200/60 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                  }`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[10px] font-mono font-bold leading-tight block">
                    {node.name}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active Node Detail Card */}
          <div className="p-5 rounded-2xl bg-indigo-50/50 dark:bg-[#050814]/70 border border-indigo-200 dark:border-indigo-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold uppercase px-2.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                  {activeNode.category}
                </span>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                  {activeNode.name} — {activeNode.role}
                </h4>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl">
                {activeNode.detail}
              </p>
            </div>

            <Link to="/pipeline" className="shrink-0 text-xs font-mono text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-semibold">
              <span>Full Pipeline View</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>


      {/* 5. Final CTA to Start a Debate */}
      <div className="pt-8 border-t border-slate-200 dark:border-white/10 text-center space-y-4">
        <h3 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white">
          READY TO ENTER THE DEBATE CHAMBER?
        </h3>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 max-w-md mx-auto">
          Test opposing AI perspectives against your toughest questions.
        </p>

        <div>
          <Link to="/debate">
            <Button
              size="lg"
              className="gap-2.5 font-bold shadow-xl shadow-indigo-600/30 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-mono text-xs uppercase tracking-wider px-8"
            >
              <span>START A DEBATE</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default HowItWorksPage;

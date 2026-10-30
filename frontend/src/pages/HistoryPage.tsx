import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  History,
  ArrowRight,
  Sparkles,
  Calendar,
  Layers,
  Scale,
  Brain,
} from 'lucide-react';
import { Button } from '../components/ui/Button';

interface DebateRecord {
  id: string;
  question: string;
  date: string;
  rounds: number;
  proModel: string;
  conModel: string;
  judgeModel: string;
  synthesis: string;
  groundingScore: string;
  isSample: boolean;
  documentSource?: string;
  pageCitations?: string;
}

const SAMPLE_DEBATES: DebateRecord[] = [
  {
    id: 'demo-1',
    question: 'Does the document provide sufficient empirical evidence to justify replacing human judges in liability rulings?',
    date: 'Recent Deliberation',
    rounds: 3,
    proModel: 'GPT-4o',
    conModel: 'Claude 3.5 Sonnet',
    judgeModel: 'Gemini 1.5 Pro',
    synthesis: 'Dual-track synthesis: Probabilistic calculation delegated with formal constraint runtime bounds; ultimate normative and moral accountability preserved for human institutions.',
    groundingScore: '96%',
    isSample: true,
    documentSource: 'AI_in_HighStakes_Law.pdf',
    pageCitations: 'Pages 8, 14, 19, 23',
  },
  {
    id: 'demo-2',
    question: 'Does the 41-minute latency reduction outweigh the risk of atypical patient under-triage?',
    date: 'Archived Inquest',
    rounds: 3,
    proModel: 'Claude 3.5 Sonnet',
    conModel: 'GPT-4o',
    judgeModel: 'Gemini 1.5 Pro',
    synthesis: 'Supervised deployment: Delegate non-comorbid triage routing while requiring mandatory human bedside re-evaluation for geriatric and multi-morbid cases.',
    groundingScore: '94%',
    isSample: true,
    documentSource: 'Autonomous_Clinical_Triage.pdf',
    pageCitations: 'Pages 2, 7, 12',
  },
  {
    id: 'demo-3',
    question: 'Should frontier AI safety regulations mandate formal invariant checks over model release?',
    date: 'Archived Inquest',
    rounds: 3,
    proModel: 'Llama 3.3 70B',
    conModel: 'GPT-4o',
    judgeModel: 'Gemini 1.5 Pro',
    synthesis: 'Tiered transparency protocol: Mandatory open research weights below compute threat thresholds, while safeguarding catastrophic dual-use bio/cyber weights behind multi-institution escrow.',
    groundingScore: '89%',
    isSample: true,
    documentSource: 'AI_in_HighStakes_Law.pdf',
    pageCitations: 'Pages 11, 23',
  },
];

export const HistoryPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'my' | 'sample'>('my');

  return (
    <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <History className="w-3.5 h-3.5" />
          <span>DEBATE MEMORY</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-[#0F172A] dark:text-white tracking-tight">
          DEBATE HISTORY
        </h1>
        <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
          Review previous multi-agent deliberations, dialectical arguments, and judicial syntheses.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex justify-center">
        <div className="p-1 rounded-2xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex gap-1 text-xs font-mono font-bold">
          <button
            type="button"
            onClick={() => setActiveTab('my')}
            className={`px-4 py-2 rounded-xl transition-all ${
              activeTab === 'my'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            My Debates (0)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sample')}
            className={`px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 ${
              activeTab === 'sample'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>Illustrative Archive</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
              DEMO
            </span>
          </button>
        </div>
      </div>

      {/* TAB 1: Empty State (Section 18) */}
      {activeTab === 'my' && (
        <div className="glass-panel rounded-3xl p-8 sm:p-14 border border-slate-200/90 dark:border-white/10 text-center max-w-xl mx-auto shadow-xl bg-white/95 dark:bg-[#080d1e]/85 space-y-5 animate-fadeIn">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 shadow-sm">
            <History className="w-8 h-8" />
          </div>

          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              NO DEBATES YET
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 max-w-sm mx-auto leading-relaxed">
              Start your first AI debate to generate structured deliberations and judicial evaluations.
            </p>
          </div>

          <div className="pt-2">
            <Link to="/debate">
              <Button
                size="lg"
                className="gap-2.5 font-bold px-8 shadow-xl shadow-indigo-600/30 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-mono text-xs uppercase tracking-wider"
              >
                <span>START A DEBATE</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* TAB 2 or Archive Display: Visual Debate Memory Cards (Section 18) */}
      {(activeTab === 'sample' || activeTab === 'my') && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-slate-200 dark:border-white/10">
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                {activeTab === 'sample' ? 'Illustrative Sample Records' : 'Sample Demonstrations for Exploration'}
              </h3>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200/80 dark:border-amber-800/60 font-bold">
                ILLUSTRATIVE
              </span>
            </div>
            <span className="text-xs font-mono text-slate-400">
              3 Illustrated Records
            </span>
          </div>

          <div className="grid grid-cols-1 gap-5">
            {SAMPLE_DEBATES.map((debate) => (
              <div
                key={debate.id}
                className="glass-card rounded-3xl p-6 sm:p-7 border border-slate-200/80 dark:border-white/10 bg-white/95 dark:bg-[#070a16]/90 shadow-lg hover:shadow-xl transition-all duration-300 space-y-4"
              >
                {/* Header Row: Date & Rounds */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
                  <div className="flex items-center gap-2.5">
                    <span className="text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60">
                      ILLUSTRATIVE
                    </span>
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{debate.date}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono text-slate-500 dark:text-slate-400">
                    <div className="flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{debate.rounds} Rounds</span>
                    </div>
                    <span>•</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                      {debate.groundingScore} Grounded
                    </span>
                  </div>
                </div>

                {/* Question */}
                <div>
                  <h4 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white leading-snug">
                    "{debate.question}"
                  </h4>
                  {debate.documentSource && (
                    <div className="flex flex-wrap items-center gap-2 pt-2 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 font-bold">
                        📄 {debate.documentSource}
                      </span>
                      {debate.pageCitations && (
                        <span className="text-slate-500 dark:text-slate-400 font-semibold">
                          Citing: {debate.pageCitations}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Miniature Wave Visualization Bar (Section 18: BLUE PRO ─── JUDGE ─── PURPLE CON) */}
                <div className="p-3.5 rounded-2xl bg-slate-50/80 dark:bg-[#040712] border border-slate-200/60 dark:border-white/5 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono font-semibold">
                    <div className="flex items-center gap-1.5 text-sky-600 dark:text-sky-400">
                      <Brain className="w-3.5 h-3.5" />
                      <span>PRO: {debate.proModel}</span>
                    </div>

                    <div className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400 font-bold">
                      <Scale className="w-3.5 h-3.5" />
                      <span>JUDGE</span>
                    </div>

                    <div className="flex items-center gap-1.5 text-purple-600 dark:text-purple-400">
                      <Brain className="w-3.5 h-3.5" />
                      <span>CON: {debate.conModel}</span>
                    </div>
                  </div>

                  {/* Wave Connection Graphic */}
                  <div className="relative w-full h-3 flex items-center justify-center">
                    <div className="absolute inset-x-0 h-[2px] bg-gradient-to-r from-sky-400 via-indigo-500 to-purple-400 rounded-full opacity-80" />
                    <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 shadow-[0_0_8px_#6366f1] relative z-10" />
                  </div>
                </div>

                {/* Final Synthesis Excerpt */}
                <div className="p-4 rounded-xl bg-amber-50/40 dark:bg-[#150f05]/50 border border-amber-200/80 dark:border-amber-800/40 space-y-1">
                  <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-mono font-bold text-[10px] uppercase">
                    <Sparkles className="w-3 h-3 text-amber-500" />
                    <span>FINAL SYNTHESIS</span>
                  </div>
                  <p className="text-xs text-slate-800 dark:text-slate-200 italic leading-relaxed font-medium">
                    "{debate.synthesis}"
                  </p>
                </div>

                {/* Footer Action: VIEW DEBATE → (Section 18) */}
                <div className="pt-1 flex justify-end">
                  <Link to={`/debate?question=${encodeURIComponent(debate.question)}`}>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 font-mono text-xs font-bold border-indigo-200 dark:border-indigo-500/40 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300"
                    >
                      <span>VIEW DEBATE</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryPage;

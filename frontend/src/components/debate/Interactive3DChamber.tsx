import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Scale, Play, Pause, RotateCcw, FileText } from 'lucide-react';
import { AINeuralBrain } from '../common/AINeuralBrain';
import { ThoughtParticleSystem } from '../common/ThoughtParticleSystem';
import { NeuralCoreView } from '../common/NeuralCoreView';
import { useIntro } from '../../context/IntroContext';
import { useDocument } from '../../context/DocumentContext';

interface ArgumentTurn {
  agent: 'PRO' | 'CON' | 'JUDGE' | 'SYNTHESIS';
  round: string;
  claim: string;
  evidence: string;
  pageCitation?: string;
}

const SAMPLE_TURNS: ArgumentTurn[] = [
  {
    agent: 'PRO',
    round: 'ROUND 01 • PRO (SUPPORTING)',
    claim: 'Empirical benchmark demonstrates a 32% reduction in inter-circuit sentencing variance when applying Bayesian prior adherence.',
    evidence: 'AI_in_HighStakes_Law.pdf — Section 3 (p < 0.001)',
    pageCitation: 'Page 8: Results',
  },
  {
    agent: 'CON',
    round: 'ROUND 01 • CON (CHALLENGING)',
    claim: 'Section 4 documents catastrophic failure on novel fact patterns, producing 91% false confidence on out-of-distribution statutory dilemmas.',
    evidence: 'AI_in_HighStakes_Law.pdf — Section 4 (Black Swan Failures)',
    pageCitation: 'Page 14: Limitations',
  },
  {
    agent: 'PRO',
    round: 'ROUND 02 • PRO RESPONSE',
    claim: 'Runtime SMT invariant verification eliminates statutory floor breaches across the formal Affirmative test corpus.',
    evidence: 'AI_in_HighStakes_Law.pdf — Section 3.2 (Bounded Solvers)',
    pageCitation: 'Page 11: Invariant Verification',
  },
  {
    agent: 'CON',
    round: 'ROUND 02 • CON RESPONSE',
    claim: 'Section 5 proves mathematical consistency cannot satisfy procedural due process or replace non-delegable civic recourse.',
    evidence: 'AI_in_HighStakes_Law.pdf — Section 5 (Constitutional Bounds)',
    pageCitation: 'Page 19: Due Process',
  },
  {
    agent: 'JUDGE',
    round: 'INDEPENDENT JUDGE EVALUATION',
    claim: 'Both agents correctly isolate document bounds: statistical gains on Page 8 are valid, but Page 14 out-of-distribution vulnerabilities prevent full autonomous delegation.',
    evidence: 'Independent Arbiter • 95% Document Grounding Score',
    pageCitation: 'Pages 8, 14, 23',
  },
  {
    agent: 'SYNTHESIS',
    round: 'EVIDENCE-GROUNDED SYNTHESIS',
    claim: 'Adopt dual-track policy from Page 23: delegate bounded calculation checks while reserving normative legal liability for human review.',
    evidence: 'Synthesized from AI_in_HighStakes_Law.pdf',
    pageCitation: 'Page 23: Policy Framework',
  },
];

export const Interactive3DChamber: React.FC = () => {
  const { replayIntro } = useIntro();
  const { activeDocument } = useDocument();
  // Entity hover states for Section 20
  const [hoveredEntity, setHoveredEntity] = useState<'PRO' | 'CON' | 'JUDGE' | null>(null);
  const [activeTurnIndex, setActiveTurnIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);

  // Cycle dialectic steps every 4.2s if playing
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setActiveTurnIndex((prev) => (prev + 1) % SAMPLE_TURNS.length);
    }, 4200);
    return () => clearInterval(interval);
  }, [isPlaying]);

  const currentTurn = SAMPLE_TURNS[activeTurnIndex];

  const isJudgeTurn = currentTurn.agent === 'JUDGE';
  const isSynthesisTurn = currentTurn.agent === 'SYNTHESIS';

  // Derived particle state based on turn or hover (simultaneous transfer by default)
  const particlePhase =
    hoveredEntity === 'PRO'
      ? 'PRO_THINKING'
      : hoveredEntity === 'CON'
      ? 'CON_THINKING'
      : hoveredEntity === 'JUDGE'
      ? 'SYNTHESIS_STREAM'
      : isSynthesisTurn
      ? 'RESULT'
      : isJudgeTurn
      ? 'JUDGE_ANALYSIS'
      : 'TRANSFER';

  const showSynthesisLine =
    hoveredEntity === 'JUDGE' || isJudgeTurn || isSynthesisTurn;

  const proBrainState =
    hoveredEntity === 'PRO' || currentTurn.agent === 'PRO'
      ? 'thinking'
      : currentTurn.agent === 'CON'
      ? 'reacting'
      : 'idle';

  const conBrainState =
    hoveredEntity === 'CON' || currentTurn.agent === 'CON'
      ? 'thinking'
      : currentTurn.agent === 'PRO'
      ? 'reacting'
      : 'idle';

  return (
    <div className="relative w-full rounded-3xl overflow-hidden border border-slate-200/80 dark:border-white/10 bg-gradient-to-b from-white/90 via-slate-50/70 to-white/95 dark:from-[#080d1e]/90 dark:via-[#070a16]/95 dark:to-[#05060a] shadow-[0_25px_70px_-15px_rgba(99,102,241,0.15)] dark:shadow-[0_25px_70px_-15px_rgba(0,0,0,0.7)] backdrop-blur-2xl p-5 sm:p-7 select-none">
      {/* Background Volumetric Glows */}
      <div className="absolute top-0 left-1/4 w-80 h-80 bg-sky-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute top-0 right-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Top Meta Bar */}
      <div className="relative z-20 flex items-center justify-between pb-3 border-b border-slate-200/60 dark:border-white/10 mb-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] font-mono tracking-widest uppercase font-bold text-slate-800 dark:text-slate-200">
            AI BRAIN DEBATE CHAMBER
          </span>
          <span className="hidden sm:inline-block text-[9px] font-mono uppercase px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200/80 dark:border-indigo-500/30 font-semibold">
            THOUGHT PARTICLES
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={replayIntro}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[10px] font-mono border border-indigo-200/80 dark:border-indigo-500/30 bg-indigo-50/80 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 transition-all cursor-pointer shadow-sm active:scale-95"
            title="Replay full AI reasoning intro animation"
          >
            <RotateCcw className="w-3 h-3 text-indigo-500" />
            <span>REPLAY INTRO</span>
          </button>

          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[10px] font-mono border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
            title={isPlaying ? 'Pause simulation loop' : 'Play simulation loop'}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3 h-3 text-indigo-500" />
                <span className="hidden sm:inline">LIVE</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 text-indigo-500" />
                <span className="hidden sm:inline">PAUSED</span>
              </>
            )}
          </button>
          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200/80 dark:border-amber-800/60 font-bold">
            ILLUSTRATIVE
          </span>
        </div>
      </div>

      {/* Proposition & Document Header */}
      <div className="relative z-20 my-2 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100/90 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 text-[10px] font-mono text-slate-700 dark:text-slate-300 mb-1.5 shadow-sm">
          <FileText className="w-3 h-3 text-indigo-500" />
          <span className="font-bold text-slate-900 dark:text-white">{activeDocument.name}</span>
          <span className="text-slate-400">•</span>
          <span className="text-slate-500 dark:text-slate-400">{activeDocument.pageCount} Pages Grounded</span>
        </div>
        <h3 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white max-w-xl mx-auto leading-snug">
          "Does empirical research justify AI legal adjudication under due process?"
        </h3>
      </div>

      {/* 3D Visual Chamber: PRO Brain (Left), Thought Particles & Synthesis Line (Center), CON Brain (Right), Judge (Below) */}
      <div className="relative w-full h-72 sm:h-80 my-2">
        {/* Layer 1: Discrete Thought Particle Transfer System with Downward Synthesis Line (Section 5, 6, 7, 8) */}
        <div className="absolute inset-0 z-10 pointer-events-none">
          <ThoughtParticleSystem
            phase={particlePhase}
            intensity={hoveredEntity ? 1.5 : 1.1}
            showSynthesisLine={showSynthesisLine}
            synthesisLineLength={showSynthesisLine ? 1.0 : 0.0}
          />
        </div>

        {/* Layer 2: Interactive Intelligence Entities */}
        <div className="relative z-20 w-full h-full flex flex-col justify-between">
          {/* Upper Row: AI PRO Brain (Left) ↔ AI CON Brain (Right) */}
          <div className="flex items-start justify-between px-2 sm:px-6 pt-2">
            {/* AI PRO Brain (Section 1 & 2) */}
            <div
              onMouseEnter={() => setHoveredEntity('PRO')}
              onMouseLeave={() => setHoveredEntity(null)}
              className="cursor-pointer transition-transform duration-300 hover:scale-105"
            >
              <AINeuralBrain
                type="PRO"
                size="sm"
                state={proBrainState}
                showLabel={true}
              />
            </div>

            {/* Central Synthesis Point Micro-Indicator */}
            <div className="pt-8 text-center pointer-events-none">
              <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-indigo-400 bg-black/40 px-2 py-0.5 rounded-full border border-white/10 backdrop-blur-md">
                SYNTHESIS POINT
              </span>
            </div>

            {/* AI CON Brain (Section 1 & 3) */}
            <div
              onMouseEnter={() => setHoveredEntity('CON')}
              onMouseLeave={() => setHoveredEntity(null)}
              className="cursor-pointer transition-transform duration-300 hover:scale-105"
            >
              <AINeuralBrain
                type="CON"
                size="sm"
                state={conBrainState}
                showLabel={true}
              />
            </div>
          </div>

          {/* Lower Center: Independent AI Judge (Section 9 & 10) */}
          <div
            onMouseEnter={() => setHoveredEntity('JUDGE')}
            onMouseLeave={() => setHoveredEntity(null)}
            className="flex flex-col items-center justify-center cursor-pointer transition-transform duration-300 hover:scale-105 pb-1"
          >
            <div className="flex flex-col items-center">
              <NeuralCoreView
                size="xs"
                state={
                  hoveredEntity === 'JUDGE' || currentTurn.agent === 'JUDGE'
                    ? 'analyzing'
                    : currentTurn.agent === 'SYNTHESIS'
                    ? 'synthesizing'
                    : 'idle'
                }
                glowColor={currentTurn.agent === 'SYNTHESIS' ? 'amber' : 'indigo'}
              />

              <div
                className={`mt-1 px-2.5 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-wider font-bold transition-all ${
                  hoveredEntity === 'JUDGE' || currentTurn.agent === 'JUDGE'
                    ? 'bg-indigo-600 text-white shadow-[0_0_15px_rgba(99,102,241,0.6)]'
                    : 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30'
                }`}
              >
                <span>INDEPENDENT AI JUDGE</span>
              </div>
              <span className="text-[8px] font-mono text-slate-400 mt-0.5">
                Receives Synthesis Line • Evaluates Reasoning
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Floating Holographic Argument Ribbon (Section 4 & 5) */}
      <div className="relative z-20 mt-3 p-4 rounded-2xl glass-card border border-slate-200/80 dark:border-white/10 bg-white/85 dark:bg-[#0c1228]/85 transition-all duration-500">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full ${
                currentTurn.agent === 'PRO'
                  ? 'bg-sky-100 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-300 dark:border-sky-500/40'
                  : currentTurn.agent === 'CON'
                  ? 'bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-500/40'
                  : currentTurn.agent === 'JUDGE'
                  ? 'bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-500/40'
                  : 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-500/40'
              }`}
            >
              {currentTurn.round}
            </span>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center gap-1.5">
            {SAMPLE_TURNS.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setActiveTurnIndex(idx)}
                className={`w-2 h-2 rounded-full transition-all ${
                  idx === activeTurnIndex
                    ? 'w-5 bg-indigo-600 dark:bg-indigo-400'
                    : 'bg-slate-300 dark:bg-slate-700 hover:bg-slate-400'
                }`}
                aria-label={`Jump to debate step ${idx + 1}`}
              />
            ))}
          </div>
        </div>

        <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
          "{currentTurn.claim}"
        </p>

        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span className="truncate max-w-[280px] sm:max-w-none">{currentTurn.evidence}</span>
          </span>
          {currentTurn.pageCitation && (
            <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-500/30 font-bold shrink-0">
              {currentTurn.pageCitation}
            </span>
          )}
        </div>
      </div>

      {/* Chamber Call to Action */}
      <div className="relative z-20 mt-4 pt-3 border-t border-slate-200/60 dark:border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
          <Scale className="w-4 h-4 text-indigo-500" />
          <span>Enter the live reasoning lab to test custom queries.</span>
        </div>

        <Link to="/debate" className="w-full sm:w-auto">
          <button
            type="button"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 shadow-md shadow-indigo-600/25 transition-all font-mono uppercase tracking-wider"
          >
            <span>ENTER DEBATE CHAMBER</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Link>
      </div>
    </div>
  );
};

export default Interactive3DChamber;

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';
import { AINeuralBrain } from '../../common/AINeuralBrain';
import { ThoughtParticleSystem } from '../../common/ThoughtParticleSystem';
import { IndependentJudge } from './IndependentJudge';
import { SynthesisNucleus } from './SynthesisNucleus';

export interface AIReasoningIntroProps {
  onComplete?: () => void;
  skipEnabled?: boolean;
}

export type IntroPhase =
  | 'PHASE_1_BRAINS_FORM'          // 0.0 - 2.0s: Two AI Brains appear on left & right
  | 'PHASE_2_BRAINS_THINK'         // 2.0 - 4.0s: Both brains activate and think (no external transfer)
  | 'PHASE_3_SIMULTANEOUS_TRANSFER'// 4.0 - 8.0s: Both brains emit digital data dots simultaneously
  | 'PHASE_4_CENTRAL_CONVERGENCE'  // 8.0 - 9.8s: Data dots arrive and orbit at central synthesis point
  | 'PHASE_5_SYNTHESIS_STABILIZE'  // 9.8 - 11.8s: Synthesis node stabilizes (neutral white/indigo/gold core)
  | 'PHASE_6_SYNTHESIS_STREAM'     // 11.8 - 14.5s: Synthesis data stream slowly travels downward to Judge (progress 0 -> 1)
  | 'PHASE_7_JUDGE_EVALUATES'      // 14.5 - 16.8s: Judge receives stream and evaluates 5 criteria
  | 'PHASE_8_RESULT_CRYSTALLIZES'  // 16.8 - 18.5s: Floating synthesis nucleus crystallizes from Judge (NO hands)
  | 'PHASE_9_RESULT_STABILIZES'    // 18.5 - 19.5s: Nucleus stabilizes; FINAL SYNTHESIS text fades in last
  | 'PHASE_10_FADE_TO_HOME';       // 19.5 - 20.3s: Soft dissolve into Home page

export const AIReasoningIntro: React.FC<AIReasoningIntroProps> = ({
  onComplete,
  skipEnabled = true,
}) => {
  const [phase, setPhase] = useState<IntroPhase>('PHASE_1_BRAINS_FORM');
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [synthesisLineProgress, setSynthesisLineProgress] = useState(0);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const judgeRef = useRef<HTMLDivElement | null>(null);
  const [targetJudgeY, setTargetJudgeY] = useState<number | undefined>(undefined);

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const animFrameRef = useRef<number | null>(null);

  // Accessibility check for reduced motion
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const addTimer = (fn: () => void, delayMs: number) => {
    const t = setTimeout(fn, delayMs);
    timersRef.current.push(t);
  };

  const clearAllAnimations = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
  };

  const handleFinish = useCallback(
    (wasSkipped = false) => {
      clearAllAnimations();
      setIsFadingOut(true);

      const fadeDuration = wasSkipped ? 250 : 800;
      setTimeout(() => {
        onComplete?.();
      }, fadeDuration);
    },
    [onComplete]
  );

  const handleSkip = () => {
    handleFinish(true);
  };

  // Measure dynamic Judge coordinate so the synthesis stream reaches the exact Judge core
  useEffect(() => {
    const measureJudgeCoords = () => {
      if (!containerRef.current || !judgeRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const judgeRect = judgeRef.current.getBoundingClientRect();
      const relativeY = judgeRect.top + judgeRect.height / 2 - containerRect.top;
      setTargetJudgeY(relativeY);
    };

    measureJudgeCoords();
    window.addEventListener('resize', measureJudgeCoords);
    return () => window.removeEventListener('resize', measureJudgeCoords);
  }, [phase]);

  // Master Deterministic Timeline (Section 4 & Section 46 Choreography)
  useEffect(() => {
    clearAllAnimations();

    if (prefersReducedMotion) {
      addTimer(() => handleFinish(false), 1400);
      return () => clearAllAnimations();
    }

    const schedule: { phase: IntroPhase; delay: number }[] = [
      { phase: 'PHASE_1_BRAINS_FORM', delay: 0 },
      { phase: 'PHASE_2_BRAINS_THINK', delay: 2000 },
      { phase: 'PHASE_3_SIMULTANEOUS_TRANSFER', delay: 4000 },
      { phase: 'PHASE_4_CENTRAL_CONVERGENCE', delay: 8000 },
      { phase: 'PHASE_5_SYNTHESIS_STABILIZE', delay: 9800 },
      { phase: 'PHASE_6_SYNTHESIS_STREAM', delay: 11800 },
      { phase: 'PHASE_7_JUDGE_EVALUATES', delay: 14500 },
      { phase: 'PHASE_8_RESULT_CRYSTALLIZES', delay: 16800 },
      { phase: 'PHASE_9_RESULT_STABILIZES', delay: 18500 },
      { phase: 'PHASE_10_FADE_TO_HOME', delay: 19500 },
    ];

    schedule.forEach((item) => {
      addTimer(() => {
        setPhase(item.phase);
      }, item.delay);
    });

    // Animate Synthesis Stream extension during Phase 6 (11.8s to 14.5s = 2700ms duration)
    addTimer(() => {
      const lineStart = performance.now();
      const lineDuration = 2700; // ms to reach Judge

      const stepLine = (now: number) => {
        const elapsed = now - lineStart;
        const rawProgress = Math.min(elapsed / lineDuration, 1.0);
        // Smooth ease-in-out curve
        const easedProgress =
          rawProgress < 0.5
            ? 2 * rawProgress * rawProgress
            : -1 + (4 - 2 * rawProgress) * rawProgress;

        setSynthesisLineProgress(Math.min(Math.max(easedProgress, 0), 1.0));

        if (rawProgress < 1.0) {
          animFrameRef.current = requestAnimationFrame(stepLine);
        } else {
          setSynthesisLineProgress(1.0);
        }
      };

      animFrameRef.current = requestAnimationFrame(stepLine);
    }, 11800);

    // Complete Intro after Phase 10
    addTimer(() => {
      handleFinish(false);
    }, 20300);

    return () => clearAllAnimations();
  }, [prefersReducedMotion, handleFinish]);

  // Derived state properties
  const proBrainState =
    phase === 'PHASE_2_BRAINS_THINK'
      ? 'thinking'
      : phase === 'PHASE_3_SIMULTANEOUS_TRANSFER'
      ? 'arguing'
      : phase === 'PHASE_4_CENTRAL_CONVERGENCE' || phase === 'PHASE_5_SYNTHESIS_STABILIZE'
      ? 'converging'
      : 'idle';

  const conBrainState =
    phase === 'PHASE_2_BRAINS_THINK'
      ? 'thinking'
      : phase === 'PHASE_3_SIMULTANEOUS_TRANSFER'
      ? 'arguing'
      : phase === 'PHASE_4_CENTRAL_CONVERGENCE' || phase === 'PHASE_5_SYNTHESIS_STABILIZE'
      ? 'converging'
      : 'idle';

  // Particle System phase mapping
  const particlePhase =
    phase === 'PHASE_1_BRAINS_FORM'
      ? 'BRAINS_FORM'
      : phase === 'PHASE_2_BRAINS_THINK'
      ? 'BRAINS_THINK'
      : phase === 'PHASE_3_SIMULTANEOUS_TRANSFER'
      ? 'TRANSFER'
      : phase === 'PHASE_4_CENTRAL_CONVERGENCE'
      ? 'CONVERGENCE'
      : phase === 'PHASE_5_SYNTHESIS_STABILIZE'
      ? 'SYNTHESIS_STABILIZE'
      : phase === 'PHASE_6_SYNTHESIS_STREAM'
      ? 'SYNTHESIS_STREAM'
      : phase === 'PHASE_7_JUDGE_EVALUATES'
      ? 'JUDGE_ANALYSIS'
      : 'RESULT';

  // Downward synthesis line strictly hidden until Phase 6!
  const showSynthesisLine =
    phase === 'PHASE_6_SYNTHESIS_STREAM' ||
    phase === 'PHASE_7_JUDGE_EVALUATES' ||
    phase === 'PHASE_8_RESULT_CRYSTALLIZES' ||
    phase === 'PHASE_9_RESULT_STABILIZES';

  const activeLineLength =
    phase === 'PHASE_6_SYNTHESIS_STREAM'
      ? synthesisLineProgress
      : showSynthesisLine
      ? 1.0
      : 0.0;

  // Judge visibility & dormant state
  const isJudgeMounted =
    phase === 'PHASE_6_SYNTHESIS_STREAM' ||
    phase === 'PHASE_7_JUDGE_EVALUATES' ||
    phase === 'PHASE_8_RESULT_CRYSTALLIZES' ||
    phase === 'PHASE_9_RESULT_STABILIZES';

  const isJudgeDormant = phase === 'PHASE_6_SYNTHESIS_STREAM';
  const isJudgeAnalyzing = phase === 'PHASE_7_JUDGE_EVALUATES';

  // Result crystallization vs stabilization text reveal order
  const showNucleus =
    phase === 'PHASE_8_RESULT_CRYSTALLIZES' ||
    phase === 'PHASE_9_RESULT_STABILIZES';

  const isNucleusFormed = phase === 'PHASE_9_RESULT_STABILIZES';

  // Result text badges ONLY fade in during Phase 9, never early!
  const showResultText = phase === 'PHASE_9_RESULT_STABILIZES';

  const isDissolving = phase === 'PHASE_10_FADE_TO_HOME';

  // Progressive Focus & Dimming of Previous Stages (Section 31 & 32)
  const isSynthesizing =
    phase === 'PHASE_4_CENTRAL_CONVERGENCE' || phase === 'PHASE_5_SYNTHESIS_STABILIZE';
  const isJudgeActive =
    phase === 'PHASE_6_SYNTHESIS_STREAM' || phase === 'PHASE_7_JUDGE_EVALUATES';
  const isResultActive =
    phase === 'PHASE_8_RESULT_CRYSTALLIZES' || phase === 'PHASE_9_RESULT_STABILIZES';

  const brainContainerClass = isResultActive
    ? 'opacity-30 scale-95 transition-all duration-1000'
    : isJudgeActive
    ? 'opacity-45 scale-95 transition-all duration-1000'
    : isSynthesizing
    ? 'opacity-65 scale-98 transition-all duration-1000'
    : 'opacity-100 scale-100 transition-all duration-1000';

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-screen h-screen z-[99999] overflow-hidden select-none bg-[#05060A] transition-opacity duration-700 ${
        isFadingOut || isDissolving ? 'opacity-0 pointer-events-none' : 'opacity-100 pointer-events-auto'
      }`}
      aria-label="Futuristic AI Reasoning Experience"
    >
      {/* 1. Underlying Atmospheric Dark Environment (100% Opaque to hide Home dashboard completely) */}
      <div className="absolute inset-0 bg-[#05060A] pointer-events-none z-0" />

      {/* Volumetric Radial Ambient Lighting */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[650px] rounded-full blur-[160px] pointer-events-none z-0 transition-all duration-1000"
        style={{
          background: showNucleus
            ? 'radial-gradient(circle, rgba(254, 240, 138, 0.28) 0%, rgba(99, 102, 241, 0.3) 50%, transparent 75%)'
            : isJudgeAnalyzing
            ? 'radial-gradient(circle, rgba(99, 102, 241, 0.35) 0%, rgba(129, 140, 248, 0.2) 50%, transparent 75%)'
            : isSynthesizing
            ? 'radial-gradient(circle, rgba(129, 140, 248, 0.25) 0%, rgba(99, 102, 241, 0.15) 50%, transparent 75%)'
            : 'radial-gradient(circle, rgba(56, 189, 248, 0.16) 0%, rgba(192, 132, 252, 0.16) 50%, transparent 75%)',
        }}
      />

      {/* 2. Glassmorphic SKIP INTRO → Button */}
      {skipEnabled && (
        <button
          onClick={handleSkip}
          className="absolute top-6 right-6 sm:top-8 sm:right-8 z-50 flex items-center gap-2 px-4 py-2 rounded-full border border-white/20 hover:border-white/40 bg-black/60 hover:bg-black/80 backdrop-blur-xl text-white/90 hover:text-white text-xs font-mono font-medium tracking-wider uppercase shadow-lg shadow-black/50 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer"
          title="Skip Intro and explore AI Debate Simulator"
        >
          <span>SKIP INTRO</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}

      {/* 3. SIMULTANEOUS THOUGHT PARTICLE TRANSFER SYSTEM */}
      <div className="absolute inset-0 pointer-events-none z-20">
        <ThoughtParticleSystem
          phase={particlePhase}
          intensity={1.2}
          showSynthesisLine={showSynthesisLine}
          synthesisLineLength={activeLineLength}
          targetJudgeY={targetJudgeY}
        />
      </div>

      {/* 4. TWO AI BRAINS (AI PRO left, AI CON right - Symmetrical & Simultaneous with Progressive Focus) */}
      <div
        className={`absolute top-[36%] left-6 sm:left-14 lg:left-24 -translate-y-1/2 pointer-events-none z-30 ${brainContainerClass}`}
      >
        <AINeuralBrain
          type="PRO"
          size="md"
          state={proBrainState}
          showLabel={true}
        />
      </div>

      <div
        className={`absolute top-[36%] right-6 sm:right-14 lg:right-24 -translate-y-1/2 pointer-events-none z-30 ${brainContainerClass}`}
      >
        <AINeuralBrain
          type="CON"
          size="md"
          state={conBrainState}
          showLabel={true}
        />
      </div>

      {/* 5. Central Synthesis Point Label Indicator */}
      {(phase === 'PHASE_4_CENTRAL_CONVERGENCE' || phase === 'PHASE_5_SYNTHESIS_STABILIZE') && (
        <div className="absolute top-[26%] left-1/2 -translate-x-1/2 pointer-events-none z-40 text-center animate-fadeIn">
          <div className="px-4 py-1.5 rounded-full bg-slate-950/80 border border-white/20 backdrop-blur-xl text-white text-[11px] font-mono font-bold tracking-widest uppercase shadow-[0_0_25px_rgba(255,255,255,0.4)]">
            <span>SYNTHESIS POINT • COMBINED REASONING</span>
          </div>
          <span className="text-[9px] font-mono text-indigo-300 mt-1 block">
            {phase === 'PHASE_4_CENTRAL_CONVERGENCE'
              ? 'Arriving thought particles converging'
              : 'Stabilized • Preparing synthesis stream'}
          </span>
        </div>
      )}

      {/* 6. INDEPENDENT AI JUDGE (Centered below Synthesis Point - Dormant until stream arrives) */}
      {isJudgeMounted && (
        <div
          ref={judgeRef}
          className="absolute top-[62%] left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-40 transition-all duration-700"
        >
          <IndependentJudge
            visible={true}
            isDormant={isJudgeDormant}
            isAnalyzing={isJudgeAnalyzing}
            isSynthesized={showNucleus}
            hasNucleus={showNucleus}
          />
        </div>
      )}

      {/* 7. FLOATING SYNTHESIS NUCLEUS (Gradual Crystallization from Judge - Purely floating, NO HANDS) */}
      {showNucleus && (
        <>
          {/* Floating Synthesis Nucleus */}
          <div className="absolute top-[62%] left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-50">
            <SynthesisNucleus visible={true} isFormed={isNucleusFormed} />
          </div>

          {/* Declared Final Synthesis Badges - FADES IN LAST in Phase 9 (Section 28) */}
          {showResultText && (
            <>
              <div className="absolute top-[62%] inset-x-0 pointer-events-none z-50 flex items-center justify-between px-6 sm:px-20 lg:px-44 -translate-y-1/2 animate-fadeIn">
                <div className="px-5 py-2.5 rounded-2xl bg-black/70 backdrop-blur-xl border border-sky-400/40 text-sky-200 shadow-[0_0_25px_rgba(56,189,248,0.35)]">
                  <span className="text-xs sm:text-sm font-mono font-extrabold tracking-widest uppercase">
                    ARGUMENT SYNTHESIS
                  </span>
                </div>

                <div className="px-5 py-2.5 rounded-2xl bg-black/70 backdrop-blur-xl border border-purple-400/40 text-purple-200 shadow-[0_0_25px_rgba(192,132,252,0.35)]">
                  <span className="text-xs sm:text-sm font-mono font-extrabold tracking-widest uppercase">
                    INDEPENDENT ARBITRATION
                  </span>
                </div>
              </div>

              {/* Balanced Conclusion Sub-panel */}
              <div className="absolute bottom-12 sm:bottom-14 z-50 flex flex-col items-center pointer-events-none animate-fadeIn inset-x-0">
                <div className="px-6 py-2.5 rounded-full bg-slate-950/90 backdrop-blur-xl border border-amber-300/40 text-center shadow-[0_0_35px_rgba(245,158,11,0.3)]">
                  <div className="text-xs sm:text-sm font-mono font-bold tracking-widest text-white uppercase flex items-center gap-2 justify-center">
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    <span>FINAL SYNTHESIS • BALANCED CONCLUSION</span>
                  </div>
                  <div className="text-[10px] font-mono text-indigo-300 mt-0.5">
                    Bilateral Information Collided → Evaluated by Independent Intelligence
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* Semantic Pipeline Status Bar Indicator */}
      <div className="absolute bottom-5 inset-x-0 flex justify-center pointer-events-none z-40">
        <div className="px-3 py-1 rounded-full bg-black/40 border border-white/10 backdrop-blur-md text-[10px] font-mono text-slate-400 tracking-wider">
          {phase === 'PHASE_1_BRAINS_FORM' && 'BILATERAL ARTIFICIAL INTELLIGENCES INITIALIZING'}
          {phase === 'PHASE_2_BRAINS_THINK' && 'BILATERAL AI REASONING • SIMULTANEOUS THOUGHT ACTIVATION'}
          {phase === 'PHASE_3_SIMULTANEOUS_TRANSFER' && 'SIMULTANEOUS DATA EXCHANGE • DIGITAL THOUGHT PARTICLES'}
          {phase === 'PHASE_4_CENTRAL_CONVERGENCE' && 'ARGUMENT CONVERGENCE • COLLISION AT SYNTHESIS POINT'}
          {phase === 'PHASE_5_SYNTHESIS_STABILIZE' && 'SYNTHESIS STABILIZATION • UNIFIED DIALECTIC REASONING'}
          {phase === 'PHASE_6_SYNTHESIS_STREAM' && 'SYNTHESIS DATA STREAM • TRANSMITTING TO INDEPENDENT JUDGE'}
          {phase === 'PHASE_7_JUDGE_EVALUATES' && 'INDEPENDENT EVALUATION • EVIDENCE • REASONING • BALANCE'}
          {phase === 'PHASE_8_RESULT_CRYSTALLIZES' && 'DIALECTIC EQUILIBRIUM ACHIEVED • RESULT CRYSTALLIZATION'}
          {(phase === 'PHASE_9_RESULT_STABILIZES' || phase === 'PHASE_10_FADE_TO_HOME') && 'FINAL SYNTHESIS • BALANCED CONCLUSION'}
        </div>
      </div>

      {/* Reduced Motion Fallback */}
      {prefersReducedMotion && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#05060A] text-center px-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-950/60 border border-indigo-500/40 flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(99,102,241,0.3)]">
            <span className="w-3.5 h-3.5 rounded-full bg-indigo-400 animate-ping" />
          </div>
          <h2 className="text-lg sm:text-xl font-mono font-bold text-white tracking-widest uppercase">
            AI DEBATE SIMULATOR
          </h2>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Dual-Brain Reasoning Engine Initialized
          </p>
        </div>
      )}
    </div>
  );
};

export default AIReasoningIntro;

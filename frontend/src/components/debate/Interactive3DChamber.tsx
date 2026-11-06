import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ShieldCheck,
  Scale,
  Play,
  Pause,
  RotateCcw,
  FileText,
  ChevronLeft,
  ChevronRight,
  Award,
  Sparkles,
  ExternalLink,
  Cpu,
  CheckCircle2,
} from 'lucide-react';
import { AINeuralBrain } from '../common/AINeuralBrain';
import { ThoughtParticleSystem } from '../common/ThoughtParticleSystem';
import { NeuralCoreView } from '../common/NeuralCoreView';
import { debateApi } from '../../services/api';
import { ShowcaseDebate } from '../../types/debate';
import { ILLUSTRATIVE_SHOWCASE_DEBATES } from '../../lib/showcaseFallback';

export const Interactive3DChamber: React.FC = () => {
  // Showcase Debates State (initialized with curated illustrative fallback)
  const [debates, setDebates] = useState<ShowcaseDebate[]>(ILLUSTRATIVE_SHOWCASE_DEBATES);
  const [currentDebateIndex, setCurrentDebateIndex] = useState<number>(0);
  const [speechStep, setSpeechStep] = useState<'PRO' | 'CON' | 'JUDGE'>('PRO');
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [hoveredEntity, setHoveredEntity] = useState<'PRO' | 'CON' | 'JUDGE' | null>(null);

  // Fetch real completed debates from the database (strictly read-only, 0 LLM calls)
  useEffect(() => {
    let isMounted = true;
    async function loadShowcase() {
      try {
        const response = await debateApi.getShowcaseDebates(8);
        if (isMounted && response?.debates && response.debates.length > 0) {
          setDebates(response.debates);
          setCurrentDebateIndex(0);
          setSpeechStep('PRO');
        } else if (isMounted) {
          setDebates(ILLUSTRATIVE_SHOWCASE_DEBATES);
        }
      } catch (err) {
        console.warn('Unable to load real completed debates for showcase, activating illustrative fallback:', err);
        if (isMounted) {
          setDebates(ILLUSTRATIVE_SHOWCASE_DEBATES);
        }
      }
    }
    loadShowcase();
    return () => {
      isMounted = false;
    };
  }, []);

  // Step transition timer (4.8s per step: PRO -> CON -> JUDGE -> Next Debate)
  useEffect(() => {
    if (!isPlaying || debates.length === 0) return;

    const timer = setInterval(() => {
      setSpeechStep((prevStep) => {
        if (prevStep === 'PRO') return 'CON';
        if (prevStep === 'CON') return 'JUDGE';
        // After JUDGE, advance to next debate and reset to PRO
        setCurrentDebateIndex((prevIdx) => (prevIdx + 1) % debates.length);
        return 'PRO';
      });
    }, 4800);

    return () => clearInterval(timer);
  }, [isPlaying, debates.length]);

  const handlePrevDebate = () => {
    if (debates.length <= 1) return;
    setCurrentDebateIndex((prev) => (prev - 1 + debates.length) % debates.length);
    setSpeechStep('PRO');
  };

  const handleNextDebate = () => {
    if (debates.length <= 1) return;
    setCurrentDebateIndex((prev) => (prev + 1) % debates.length);
    setSpeechStep('PRO');
  };

  const handleReplayDebate = () => {
    setSpeechStep('PRO');
    setIsPlaying(true);
  };

  const currentDebate = debates[currentDebateIndex] || ILLUSTRATIVE_SHOWCASE_DEBATES[0];
  const proArg = currentDebate.proArguments?.[0];
  const conArg = currentDebate.conArguments?.[0];
  const isReal = Boolean(currentDebate.isReal);

  const isJudgeStep = speechStep === 'JUDGE';
  const showSynthesisLine = hoveredEntity === 'JUDGE' || isJudgeStep;

  // Visual particle state based on active entity or speech step
  const particlePhase =
    hoveredEntity === 'PRO'
      ? 'PRO_THINKING'
      : hoveredEntity === 'CON'
      ? 'CON_THINKING'
      : hoveredEntity === 'JUDGE'
      ? 'SYNTHESIS_STREAM'
      : isJudgeStep
      ? 'RESULT'
      : speechStep === 'PRO'
      ? 'TRANSFER'
      : 'CON_THINKING';

  const proBrainState =
    hoveredEntity === 'PRO' || speechStep === 'PRO'
      ? 'thinking'
      : speechStep === 'CON'
      ? 'reacting'
      : 'idle';

  const conBrainState =
    hoveredEntity === 'CON' || speechStep === 'CON'
      ? 'thinking'
      : speechStep === 'PRO'
      ? 'reacting'
      : 'idle';

  return (
    <div className="relative w-full rounded-3xl overflow-hidden border border-slate-200/80 dark:border-white/10 bg-gradient-to-b from-white/90 via-slate-50/70 to-white/95 dark:from-[#080d1e]/90 dark:via-[#070a16]/95 dark:to-[#05060a] shadow-[0_25px_70px_-15px_rgba(99,102,241,0.15)] dark:shadow-[0_25px_70px_-15px_rgba(0,0,0,0.7)] backdrop-blur-2xl p-5 sm:p-7 select-none">
      {/* Background Volumetric Glows */}
      <div className="absolute top-0 left-1/4 w-80 h-80 bg-sky-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute top-0 right-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Top Meta Bar */}
      <div className="relative z-20 flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200/60 dark:border-white/10 mb-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isReal ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
            }`}
          />
          <span className="text-[11px] font-mono tracking-widest uppercase font-bold text-slate-800 dark:text-slate-200">
            AI BRAIN DEBATE CHAMBER
          </span>

          {/* Real Completed Debate vs Illustrative Preview Badge */}
          {isReal ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60 font-bold shadow-xs">
              <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
              <span>REAL COMPLETED DEBATE</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60 font-bold shadow-xs">
              <Sparkles className="w-3 h-3 text-amber-500 shrink-0" />
              <span>ILLUSTRATIVE DEBATE PREVIEW</span>
            </span>
          )}
        </div>

        {/* Carousel & Animation Controls */}
        <div className="flex items-center gap-1.5 font-mono text-xs">
          {/* Position Indicator & Prev / Next Navigation */}
          {debates.length > 1 && (
            <div className="flex items-center gap-1 bg-slate-100/90 dark:bg-slate-900/90 border border-slate-200 dark:border-white/10 rounded-xl px-2 py-0.5 text-[11px] text-slate-700 dark:text-slate-300">
              <button
                type="button"
                onClick={handlePrevDebate}
                className="p-0.5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors cursor-pointer"
                title="Previous debate"
                aria-label="Previous debate"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="px-1 text-[10px] font-bold">
                {currentDebateIndex + 1} of {debates.length}
              </span>
              <button
                type="button"
                onClick={handleNextDebate}
                className="p-0.5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors cursor-pointer"
                title="Next debate"
                aria-label="Next debate"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Replay Debate Animation */}
          <button
            type="button"
            onClick={handleReplayDebate}
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl text-[10px] font-mono border border-indigo-200/80 dark:border-indigo-500/30 bg-indigo-50/80 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 transition-all cursor-pointer shadow-xs active:scale-95"
            title="Replay this debate animation from PRO speech"
          >
            <RotateCcw className="w-3 h-3 text-indigo-500" />
            <span className="hidden sm:inline">REPLAY</span>
          </button>

          {/* Play / Pause Toggle */}
          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl text-[10px] font-mono border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
            title={isPlaying ? 'Pause debate auto-rotation' : 'Resume debate auto-rotation'}
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
        </div>
      </div>

      {/* Proposition & Document Header */}
      <div className="relative z-20 my-2 text-center space-y-1">
        <div className="inline-flex flex-wrap items-center justify-center gap-2 px-3 py-1 rounded-full bg-slate-100/90 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 text-[10px] font-mono text-slate-700 dark:text-slate-300 shadow-sm max-w-full">
          {currentDebate.documentName ? (
            <>
              <FileText className="w-3 h-3 text-indigo-500 shrink-0" />
              <span className="font-bold text-slate-900 dark:text-white max-w-[260px] truncate">
                {currentDebate.documentName}
              </span>
              {isReal && currentDebate.createdAt && (
                <>
                  <span className="text-slate-400">•</span>
                  <span className="text-slate-500 dark:text-slate-400">
                    {currentDebate.createdAt}
                  </span>
                </>
              )}
            </>
          ) : (
            <>
              <Scale className="w-3 h-3 text-indigo-500 shrink-0" />
              <span className="font-bold text-slate-900 dark:text-white">
                {isReal ? 'General Proposition' : 'Dialectic Proposition'}
              </span>
              {isReal && currentDebate.createdAt && (
                <>
                  <span className="text-slate-400">•</span>
                  <span className="text-slate-500 dark:text-slate-400">
                    {currentDebate.createdAt}
                  </span>
                </>
              )}
            </>
          )}
        </div>

        <h3 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white max-w-xl mx-auto leading-snug line-clamp-2 px-2">
          "{currentDebate.topic}"
        </h3>
      </div>

      {/* 3D Visual Chamber: PRO Brain (Left), Particles & Synthesis Stream (Center), CON Brain (Right), Judge (Below) */}
      <div className="relative w-full h-72 sm:h-80 my-2">
        {/* Layer 1: Thought Particle Transfer System with Downward Synthesis Line */}
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
            {/* AI PRO Brain */}
            <div
              onMouseEnter={() => setHoveredEntity('PRO')}
              onMouseLeave={() => setHoveredEntity(null)}
              onClick={() => setSpeechStep('PRO')}
              className="cursor-pointer transition-transform duration-300 hover:scale-105"
              title="Click to view PRO argument"
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

            {/* AI CON Brain */}
            <div
              onMouseEnter={() => setHoveredEntity('CON')}
              onMouseLeave={() => setHoveredEntity(null)}
              onClick={() => setSpeechStep('CON')}
              className="cursor-pointer transition-transform duration-300 hover:scale-105"
              title="Click to view CON argument"
            >
              <AINeuralBrain
                type="CON"
                size="sm"
                state={conBrainState}
                showLabel={true}
              />
            </div>
          </div>

          {/* Lower Center: Independent AI Judge */}
          <div
            onMouseEnter={() => setHoveredEntity('JUDGE')}
            onMouseLeave={() => setHoveredEntity(null)}
            onClick={() => setSpeechStep('JUDGE')}
            className="flex flex-col items-center justify-center cursor-pointer transition-transform duration-300 hover:scale-105 pb-1"
            title="Click to view Judge evaluation"
          >
            <div className="flex flex-col items-center">
              <NeuralCoreView
                size="xs"
                state={
                  hoveredEntity === 'JUDGE' || isJudgeStep
                    ? 'synthesizing'
                    : 'idle'
                }
                glowColor={isJudgeStep ? 'amber' : 'indigo'}
              />

              <div
                className={`mt-1 px-2.5 py-0.5 rounded-full text-[9px] font-mono uppercase tracking-wider font-bold transition-all ${
                  hoveredEntity === 'JUDGE' || isJudgeStep
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

      {/* Floating Holographic Argument Ribbon */}
      <div className="relative z-20 mt-3 p-4 rounded-2xl glass-card border border-slate-200/80 dark:border-white/10 bg-white/90 dark:bg-[#0c1228]/90 transition-all duration-500 shadow-md">
        {/* Stage Navigation Pills (PRO • CON • JUDGE) & Winner */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-100 dark:border-white/5">
          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            <button
              type="button"
              onClick={() => setSpeechStep('PRO')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                speechStep === 'PRO'
                  ? 'bg-sky-500 text-white shadow-sm shadow-sky-500/30'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-sky-600'
              }`}
            >
              AI PRO
            </button>
            <button
              type="button"
              onClick={() => setSpeechStep('CON')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                speechStep === 'CON'
                  ? 'bg-purple-600 text-white shadow-sm shadow-purple-600/30'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-purple-600'
              }`}
            >
              AI CON
            </button>
            <button
              type="button"
              onClick={() => setSpeechStep('JUDGE')}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                speechStep === 'JUDGE'
                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-indigo-600'
              }`}
            >
              INDEPENDENT JUDGE
            </button>
          </div>

          {/* Adjudicated Winner & Scores */}
          {currentDebate.judgeWinner && (
            <div className="flex items-center gap-1 text-[11px] font-mono font-bold">
              <span
                className={`px-2 py-0.5 rounded-full border text-[10px] uppercase flex items-center gap-1 ${
                  currentDebate.judgeWinner === 'PRO'
                    ? 'bg-sky-100 dark:bg-sky-950/60 text-sky-800 dark:text-sky-300 border border-sky-300 dark:border-sky-700/60'
                    : currentDebate.judgeWinner === 'CON'
                    ? 'bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700/60'
                    : 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60'
                }`}
              >
                <Award className="w-3 h-3" />
                <span>Winner: {currentDebate.judgeWinner}</span>
                {isReal && currentDebate.judgeProScore != null && currentDebate.judgeConScore != null && (
                  <span className="font-semibold text-[9px] opacity-90 pl-1 border-l border-current/20">
                    {currentDebate.judgeProScore} - {currentDebate.judgeConScore}
                  </span>
                )}
              </span>
            </div>
          )}
        </div>

        {/* PRO Speech Card */}
        {speechStep === 'PRO' && (
          <div className="space-y-2 animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-sky-100 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-300 dark:border-sky-500/40">
                {proArg?.roundLabel || 'ROUND 01 • PRO (AFFIRMATIVE)'}
              </span>
              {proArg?.title && (
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                  {proArg.title}
                </span>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-normal">
              "{proArg?.content || 'Affirmative position establishing the empirical and logical foundation.'}"
            </p>

            {isReal && proArg?.evidence && (
              <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span className="truncate max-w-[280px] sm:max-w-none">{proArg.evidence}</span>
                </span>
                {proArg.pageCitation && (
                  <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-500/30 font-bold shrink-0">
                    {proArg.pageCitation}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* CON Speech Card */}
        {speechStep === 'CON' && (
          <div className="space-y-2 animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-500/40">
                {conArg?.roundLabel || 'ROUND 01 • CON (CHALLENGING)'}
              </span>
              {conArg?.title && (
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                  {conArg.title}
                </span>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-normal">
              "{conArg?.content || 'Negative counter-examination probing empirical boundaries and counter-arguments.'}"
            </p>

            {isReal && conArg?.evidence && (
              <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span className="truncate max-w-[280px] sm:max-w-none">{conArg.evidence}</span>
                </span>
                {conArg.pageCitation && (
                  <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-500/30 font-bold shrink-0">
                    {conArg.pageCitation}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Judge Verdict Card */}
        {speechStep === 'JUDGE' && (
          <div className="space-y-2 animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-500/40">
                INDEPENDENT JUDICIAL ARBITRATION
              </span>
              <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                Verified Synthesis & Verdict
              </span>
            </div>

            <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-normal">
              "{currentDebate.judgeVerdict || currentDebate.judgeReasoning || 'Bilateral synthesis weighing grounded affirmative findings against critical systemic risks.'}"
            </p>

            <div className="mt-2 pt-2 border-t border-slate-100 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                <span>
                  {currentDebate.judgeModel || currentDebate.judgeProvider || 'Dual-agent arbitration'}
                </span>
              </span>
              {isReal && (
                <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                  Verified Historical Score
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Chamber Call to Action Bar */}
      <div className="relative z-20 mt-4 pt-3 border-t border-slate-200/60 dark:border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
          <Scale className="w-4 h-4 text-indigo-500 shrink-0" />
          <span>Enter the live reasoning lab to test custom queries.</span>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          {/* Replay Full Debate link for real historical debates */}
          {isReal && currentDebate.id && (
            <Link to={`/history/${currentDebate.id}`} className="w-full sm:w-auto">
              <button
                type="button"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all font-mono uppercase tracking-wider cursor-pointer"
                title="View full saved transcript and evaluation"
              >
                <span>Replay Full</span>
                <ExternalLink className="w-3 h-3 text-slate-400" />
              </button>
            </Link>
          )}

          <Link to="/debate" className="w-full sm:w-auto">
            <button
              type="button"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 shadow-md shadow-indigo-600/25 transition-all font-mono uppercase tracking-wider cursor-pointer"
            >
              <span>ENTER DEBATE CHAMBER</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Interactive3DChamber;

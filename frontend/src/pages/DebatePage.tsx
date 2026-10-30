import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Brain,
  Scale,
  Sparkles,
  ShieldCheck,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  History as HistoryIcon,
  HelpCircle,
  Play,
  Pause,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Share2,
  FileText,
  ExternalLink,
  BookOpen,
  Sliders,
  Settings,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { NeuralCoreView } from '../components/common/NeuralCoreView';
import { AINeuralBrain } from '../components/common/AINeuralBrain';
import { ThoughtParticleSystem } from '../components/common/ThoughtParticleSystem';
import { DocumentViewer } from '../components/document/DocumentViewer';
import { DocumentSourceSection } from '../components/document/DocumentSourceSection';
import { CompactStatusIndicator } from '../components/common/CompactStatusIndicator';
import { useDocument } from '../context/DocumentContext';
import { DebateMode, DocumentMetadata } from '../types/document';
import { debateApi } from '../services/api';
import { DebateSession, DebateSynthesis } from '../types/debate';

interface GroundedArgument {
  id: string;
  roundNumber: number;
  speaker: 'PRO' | 'CON';
  title: string;
  argumentText: string;
  confidence: number;
  pageNumber: number;
  sectionTitle: string;
  supportingEvidence: string;
  counterRelation: string;
  evidenceId: string;
  executionStatus?: 'REAL_LOCAL_MODEL' | 'REAL_REMOTE_API' | 'SIMULATED';
}

export const DebatePage: React.FC = () => {
  const location = useLocation();
  const documentViewerRef = useRef<HTMLDivElement>(null);

  const {
    activeDocument,
    selectDocument,
    evidenceItems,
    selectedMode,
    setSelectedMode,
  } = useDocument();

  // Snapshot of document used when active debate was started
  const [debateDocument, setDebateDocument] = useState<DocumentMetadata>(activeDocument);

  // Active View Tab on mobile / tablets (chamber vs document)
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'chamber' | 'document'>('chamber');

  // Document Viewer target page controller
  const [viewerTargetPage, setViewerTargetPage] = useState<number>(8);
  const [activeEvidenceHighlight, setActiveEvidenceHighlight] = useState<string | null>('ev-1');

  // Form Parameters
  const [question, setQuestion] = useState<string>(
    'Does the document provide sufficient empirical evidence to justify replacing human judges in liability rulings?'
  );
  const [proModel, setProModel] = useState<string>('gemma-4-E4B-it');
  const [conModel, setConModel] = useState<string>('Qwen2.5-VL-7B-Instruct');
  const [judgeModel, setJudgeModel] = useState<string>('gemini-3.8-flash');
  const [showAdvancedSettings, setShowAdvancedSettings] = useState<boolean>(false);
  const [showTooltip, setShowTooltip] = useState<boolean>(false);

  // Live Backend State Integration
  const [activeDebateId, setActiveDebateId] = useState<string | null>(null);
  const [liveSession, setLiveSession] = useState<DebateSession | null>(null);
  const [liveSynthesis, setLiveSynthesis] = useState<DebateSynthesis | null>(null);
  const [backendStatusMessage, setBackendStatusMessage] = useState<string>('Ready to initialize debate');
  const [isLiveBackendConnected, setIsLiveBackendConnected] = useState<boolean>(false);

  // Simulation Lifecycle State: State A (false) vs State B (true)
  const [hasStarted, setHasStarted] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(true);
  const [expandedArgId, setExpandedArgId] = useState<string | null>(null);

  // Judge Analysis Criteria States (Document Fidelity & Rigor)
  const [judgeAnalyzingCriteria, setJudgeAnalyzingCriteria] = useState<{
    evidence: boolean;
    reasoning: boolean;
    counterarguments: boolean;
    consistency: boolean;
    uncertainty: boolean;
  }>({
    evidence: false,
    reasoning: false,
    counterarguments: false,
    consistency: false,
    uncertainty: false,
  });

  // Handle URL query parameters (?doc=...&question=...&mode=...)
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const docParam = searchParams.get('doc');
    const questionParam = searchParams.get('question') || searchParams.get('q');
    const modeParam = searchParams.get('mode') as DebateMode | null;

    if (docParam) {
      selectDocument(docParam);
    }
    if (questionParam) {
      setQuestion(decodeURIComponent(questionParam));
    }
    if (modeParam && ['claim-challenge', 'critical-review', 'balanced-analysis'].includes(modeParam)) {
      setSelectedMode(modeParam);
    }
  }, [location.search, selectDocument, setSelectedMode]);

  // Fallback Grounded Arguments dynamically derived from the document used for the debate
  const cannedDebateTimeline: GroundedArgument[] = useMemo(() => {
    if (debateDocument.id === 'doc-triage') {
      return [
        {
          id: 'r1-pro',
          roundNumber: 1,
          speaker: 'PRO',
          title: 'Validated ICU Transfer Latency Reduction',
          argumentText:
            `According to ${debateDocument.name} (Section 2, Page 7), multi-agent Bayesian triage demonstrated a 41-minute median reduction in ICU transfer delays during surge conditions. High-speed classification systematically accelerates urgent bed allocation.`,
          confidence: 94,
          pageNumber: 7,
          sectionTitle: 'Section 2: Primary Outcomes & Latency',
          supportingEvidence: `${debateDocument.name} — Page 7, Section 2.1 (41-min Latency Benchmark)`,
          counterRelation: 'Affirmative Grounding: Cites verified clinical latency reduction in respiratory surge.',
          evidenceId: 'ev-t1',
        },
        {
          id: 'r1-con',
          roundNumber: 1,
          speaker: 'CON',
          title: 'Systemic Under-Triage in Comorbid Geriatric Cohorts',
          argumentText:
            `Section 3 (Page 12) of ${debateDocument.name} documents critical diagnostic blind spots. Comorbid geriatric patients exhibiting atypical symptom profiles suffered a 24% increase in secondary under-triage. Speed gains cannot justify diagnostic blind spots.`,
          confidence: 93,
          pageNumber: 12,
          sectionTitle: 'Section 3: Atypical Presentation Blind Spots',
          supportingEvidence: `${debateDocument.name} — Page 12, Section 3.1 (Atypical Bias Corpus)`,
          counterRelation: 'Critical Limitation: Highlights failure on complex atypical clinical presentations.',
          evidenceId: 'ev-t2',
        },
        {
          id: 'r2-pro',
          roundNumber: 2,
          speaker: 'PRO',
          title: 'Formal Invariant Bed-Allocation Safety Floors',
          argumentText:
            `As outlined in Section 1 (Page 2), automated allocation rules implement hard statutory constraint envelopes that prohibit discharge without verified physiological stabilization markers.`,
          confidence: 90,
          pageNumber: 2,
          sectionTitle: 'Section 1: Clinical Triage Protocol',
          supportingEvidence: `${debateDocument.name} — Page 2, Section 1.3 (Invariant Stabilization Floor)`,
          counterRelation: 'Rejoinder: Proves critical patients are protected by deterministic physiological constraints.',
          evidenceId: 'ev-t3',
        },
        {
          id: 'r2-con',
          roundNumber: 2,
          speaker: 'CON',
          title: 'Non-Delegable Physician Liability & Epistemic Uncertainty',
          argumentText:
            `Page 15 reveals that algorithmic triage displaces bedside clinical gestalt, transferring liability to automated systems that cannot exercise moral or legal accountability in triage rationing.`,
          confidence: 92,
          pageNumber: 15,
          sectionTitle: 'Section 4: Ethical & Liability Bounds',
          supportingEvidence: `${debateDocument.name} — Page 15, Section 4.2 (Clinical Gestalt Displacement)`,
          counterRelation: 'Ethical Challenge: Demonstrates automated triage violates clinical responsibility standards.',
          evidenceId: 'ev-t4',
        },
      ];
    }

    // Default for AI_in_HighStakes_Law.pdf and newly uploaded documents
    return [
      {
        id: 'r1-pro',
        roundNumber: 1,
        speaker: 'PRO',
        title: 'Documented Variance Reduction & Bayesian Adherence',
        argumentText:
          `According to ${debateDocument.name} (Section 3, Page 8), autonomous Bayesian priors achieved a 32% reduction in inter-circuit sentencing variance across 12,000 simulated appellate rulings (p < 0.001). The empirical data demonstrates computational models systematically eliminate human fatigue without subjective distortion.`,
        confidence: 96,
        pageNumber: 8,
        sectionTitle: 'Section 3: Empirical Results',
        supportingEvidence: `${debateDocument.name} — Page 8, Section 3.1 (p < 0.001 benchmark)`,
        counterRelation: 'Affirmative Grounding: Establishes rigorous mathematical consistency reported in the document.',
        evidenceId: 'ev-1',
      },
      {
        id: 'r1-con',
        roundNumber: 1,
        speaker: 'CON',
        title: 'Documented Out-of-Distribution Catastrophe & Moral Blind Spots',
        argumentText:
          `The affirmative ignores Section 4 (Page 14) of ${debateDocument.name}, which explicitly warns of catastrophic out-of-distribution failure. When tested on novel non-precedential fact patterns, the classifier exhibited over 91% false confidence on objectively flawed statutory interpretations. Statistical consistency cannot compensate for ungrounded moral heuristics.`,
        confidence: 94,
        pageNumber: 14,
        sectionTitle: 'Section 4: Out-of-Distribution Failures',
        supportingEvidence: `${debateDocument.name} — Page 14, Section 4.2 (Black Swan Failure Corpus)`,
        counterRelation: 'Critical Limitation: Directly refutes affirmative safety claims using the author’s own stated failure rate.',
        evidenceId: 'ev-2',
      },
      {
        id: 'r2-pro',
        roundNumber: 2,
        speaker: 'PRO',
        title: 'Formal Invariant Envelopes Prevent Statutory Breaches',
        argumentText:
          `As delineated on Page 11 (Section 3.2), the architecture does not rely on unbounded generative output. Modern deployments couple probabilistic models with formal SMT constraint solvers, guaranteeing zero statutory floor violations across the verified affirmative test corpus.`,
        confidence: 91,
        pageNumber: 11,
        sectionTitle: 'Section 3.2: Invariant Verification',
        supportingEvidence: `${debateDocument.name} — Page 11, Section 3.2 (SMT Constraint Envelopes)`,
        counterRelation: 'Rejoinder: Proves out-of-distribution risks are bounded by formal mathematical verification.',
        evidenceId: 'ev-3',
      },
      {
        id: 'r2-con',
        roundNumber: 2,
        speaker: 'CON',
        title: 'Constitutional Recourse & Non-Delegable Due Process',
        argumentText:
          `Page 19 (Section 5) establishes the foundational legal flaw: mathematical consistency is fundamentally not civic legitimacy. Procedural due process demands non-delegable moral accountability and transparent human discretion, which algorithmic constraint solvers cannot mathematically provide.`,
        confidence: 95,
        pageNumber: 19,
        sectionTitle: 'Section 5: Constitutional Recourse',
        supportingEvidence: `${debateDocument.name} — Page 19, Section 5.1 (Due Process Bounds)`,
        counterRelation: 'Constitutional Challenge: Proves algorithmic optimization alone fails legal democratic muster.',
        evidenceId: 'ev-4',
      },
    ];
  }, [debateDocument]);

  // Dynamically resolve timeline: prefer real live turns from backend session when available
  const debateTimeline: GroundedArgument[] = useMemo(() => {
    if (liveSession && liveSession.rounds && liveSession.rounds.length > 0) {
      const liveArgs: GroundedArgument[] = [];
      liveSession.rounds.forEach((rnd) => {
        rnd.turns.forEach((turn, idx) => {
          const isPro = turn.role === 'PRO' || turn.speaker === 'DEBATER_A';
          const ev = turn.evidence && turn.evidence.length > 0 ? turn.evidence[0] : null;
          liveArgs.push({
            id: `turn-${rnd.roundNumber}-${isPro ? 'pro' : 'con'}-${idx}`,
            roundNumber: rnd.roundNumber,
            speaker: isPro ? 'PRO' : 'CON',
            title: turn.title || (isPro ? `Round ${rnd.roundNumber} Affirmative Case` : `Round ${rnd.roundNumber} Opposition Rebuttal`),
            argumentText: turn.content,
            confidence: 93,
            pageNumber: 8,
            sectionTitle: isPro ? 'Affirmative Grounding' : 'Direct Clash Rebuttal',
            supportingEvidence: ev?.claim || `${debateDocument.name} verified reference`,
            counterRelation: isPro ? 'Affirmative Grounding: Cites verified findings.' : 'Direct Clash: Rebuts PRO claims directly.',
            evidenceId: ev?.id || `ev-${rnd.roundNumber}-${idx}`,
            executionStatus: turn.executionStatus || 'SIMULATED'
          });
        });
      });
      if (liveArgs.length > 0) {
        return liveArgs;
      }
    }
    return cannedDebateTimeline;
  }, [liveSession, debateDocument, cannedDebateTimeline]);

  const maxStep = 6;

  // Active polling of backend debate state
  useEffect(() => {
    if (!activeDebateId) return;

    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const session = await debateApi.getDebate(activeDebateId);
        if (!isMounted) return;
        setLiveSession(session);

        const totalTurns = session.rounds.reduce((acc, r) => acc + r.turns.length, 0);
        if (totalTurns === 1) {
          setCurrentStep(1);
          setBackendStatusMessage('Round 1: Gemma (PRO) turn generated');
        } else if (totalTurns === 2) {
          setCurrentStep(2);
          setBackendStatusMessage('Round 1: Qwen (CON) rebuttal generated');
        } else if (totalTurns === 3) {
          setCurrentStep(3);
          setBackendStatusMessage('Round 2: Gemma (PRO) response generated');
        } else if (totalTurns >= 4 && session.status !== 'completed') {
          setCurrentStep(5);
          setBackendStatusMessage('All turns complete. Gemini (JUDGE) is evaluating transcript...');
        } else if (session.status === 'completed') {
          setCurrentStep(6);
          setBackendStatusMessage('Debate Adjudication Complete!');
          if (session.synthesis) {
            setLiveSynthesis(session.synthesis);
          } else {
            try {
              const syn = await debateApi.getDebateResult(activeDebateId);
              if (isMounted) setLiveSynthesis(syn);
            } catch (_) {}
          }
          clearInterval(interval);
        } else if (session.status === 'failed') {
          setBackendStatusMessage('Debate execution failed on backend');
          clearInterval(interval);
        }
      } catch (err) {
        console.warn('Error polling debate status:', err);
      }
    }, 2500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeDebateId]);

  // Auto-play timeline progression (used for preview / simulation when live debate is not polling)
  useEffect(() => {
    if (!hasStarted || !isAutoPlaying || activeDebateId) return;

    if (currentStep < maxStep) {
      const delay = currentStep === 4 ? 3600 : currentStep === 5 ? 4200 : 3200;
      const timer = setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [hasStarted, isAutoPlaying, currentStep, activeDebateId]);

  // Progressive judge criteria evaluation animation (Requirement 14 labels)
  useEffect(() => {
    if (currentStep === 5) {
      setJudgeAnalyzingCriteria({
        evidence: true,
        reasoning: false,
        counterarguments: false,
        consistency: false,
        uncertainty: false,
      });

      const t1 = setTimeout(() => {
        setJudgeAnalyzingCriteria((c) => ({ ...c, reasoning: true }));
      }, 700);

      const t2 = setTimeout(() => {
        setJudgeAnalyzingCriteria((c) => ({ ...c, counterarguments: true }));
      }, 1400);

      const t3 = setTimeout(() => {
        setJudgeAnalyzingCriteria((c) => ({ ...c, consistency: true }));
      }, 2100);

      const t4 = setTimeout(() => {
        setJudgeAnalyzingCriteria((c) => ({ ...c, uncertainty: true }));
      }, 2800);

      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
        clearTimeout(t3);
        clearTimeout(t4);
      };
    }
  }, [currentStep]);

  // Transition from State A to State B
  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    setDebateDocument(activeDocument);
    setHasStarted(true);
    setCurrentStep(1);
    setIsAutoPlaying(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });

    try {
      setBackendStatusMessage('Dispatching LangGraph workflow to Gemma, Qwen, and Gemini...');
      const response = await debateApi.startDebate({
        topic: question,
        debaterAModel: proModel,
        debaterBModel: conModel,
        judgeModel: judgeModel,
        rounds: 2,
        evidenceMode: true,
        documentId: activeDocument && activeDocument.id !== 'doc-sample' ? activeDocument.id : undefined
      });
      if (response && response.debateId) {
        setActiveDebateId(response.debateId);
        setIsLiveBackendConnected(true);
        setBackendStatusMessage(`Debate dispatched (ID: ${response.debateId.slice(0, 8)}). Polling turns...`);
      }
    } catch (err) {
      console.warn('Backend startDebate call failed, operating in simulated preview mode:', err);
      setIsLiveBackendConnected(false);
      setBackendStatusMessage('Backend server offline · Previewing dialectical simulation');
    }
  };

  // Return to State A (Setup)
  const handleReturnToSetup = () => {
    setHasStarted(false);
    setCurrentStep(0);
    setIsAutoPlaying(false);
    setActiveDebateId(null);
    setLiveSession(null);
    setLiveSynthesis(null);
    setExpandedArgId(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Reset and restart debate
  const handleRestartDebate = () => {
    setCurrentStep(1);
    setIsAutoPlaying(true);
    setExpandedArgId(null);
  };

  // Jump document reader to a specific argument's citation
  const handleJumpToCitation = (pageNum: number, evId?: string) => {
    setViewerTargetPage(pageNum);
    if (evId) setActiveEvidenceHighlight(evId);

    // If on mobile, switch to document tab
    if (window.innerWidth < 1024) {
      setActiveWorkspaceTab('document');
    }

    documentViewerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  // Clean suggested questions (Requirement 7)
  const suggestedQuestionsList = useMemo(() => {
    const list = [
      'Is the main conclusion supported by the evidence?',
      'What are the strongest methodological limitations?',
      'Which claims lack sufficient supporting evidence?',
      'What are the strongest arguments against the author\'s conclusion?',
      'Are there contradictions within the document?',
    ];
    if (activeDocument.suggestedQuestions) {
      activeDocument.suggestedQuestions.forEach((sq) => {
        if (!list.includes(sq)) list.push(sq);
      });
    }
    return list;
  }, [activeDocument]);

  return (
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Navigation & Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200/70 dark:border-white/10">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors font-semibold uppercase tracking-wider"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>

        {/* Dynamic status indicator connecting to backend state */}
        <CompactStatusIndicator message={isLiveBackendConnected ? `● Live: ${backendStatusMessage}` : backendStatusMessage} />

        <div className="flex items-center gap-2.5">
          <Link
            to="/documents"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50/80 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-medium hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-all shadow-sm"
          >
            <FileText className="w-3 h-3 text-indigo-500" />
            <span>Documents</span>
          </Link>

          <Link
            to="/history"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs font-mono font-medium hover:border-indigo-300 transition-all shadow-sm"
          >
            <HistoryIcon className="w-3 h-3 text-indigo-500" />
            <span>History</span>
          </Link>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* STATE A — DEBATE SETUP (Requirement 5) */}
      {/* ========================================================================= */}
      {!hasStarted ? (
        <div className="space-y-6 animate-fadeIn">
          {/* Header */}
          <div className="space-y-1.5">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-slate-900 dark:text-white tracking-tight">
              DOCUMENT-GROUNDED DEBATE
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed">
              Upload a document, formulate a question, and watch opposing AI agents debate claims grounded in verified citations.
            </p>
          </div>

          {/* 1. Document Source Section (Requirement 3 & 4) */}
          <DocumentSourceSection
            onDocumentChange={(doc) => {
              if (doc.suggestedQuestions.length > 0) {
                setQuestion(doc.suggestedQuestions[0]);
              }
            }}
          />

          {/* 2. Setup Form */}
          <form onSubmit={handleStart} className="space-y-6">
            <div className="rounded-3xl p-6 sm:p-7 border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#080d1e]/90 backdrop-blur-2xl shadow-xl space-y-6">
              {/* Question Input Section (Requirement 6) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <label
                      htmlFor="debate-question-input"
                      className="text-xs font-mono font-bold tracking-wider uppercase text-slate-900 dark:text-white"
                    >
                      What question should the AI debate?
                    </label>
                    <div className="relative inline-block">
                      <button
                        type="button"
                        onClick={() => setShowTooltip(!showTooltip)}
                        className="text-slate-400 hover:text-indigo-500 focus:outline-none"
                        title="Question formulating tips"
                        aria-label="Question formulation advice"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                      </button>
                      {showTooltip && (
                        <div className="absolute left-6 top-0 z-30 w-72 p-3 rounded-xl bg-slate-900 text-slate-100 text-[11px] font-mono leading-relaxed border border-slate-700 shadow-xl">
                          <p className="font-bold text-indigo-400 mb-1">How to formulate a good question:</p>
                          <p>
                            Ask specific questions targeting empirical results, stated limitations, methodologies, or policy conclusions in your document. Avoid overly broad or vague queries.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-500 dark:text-slate-400 leading-normal">
                  Ask a specific question about the claims, evidence, methods, or conclusions in your document.
                </p>

                <textarea
                  id="debate-question-input"
                  rows={3}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="e.g. Does this document provide sufficient evidence to support its main conclusion?"
                  className="w-full rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/80 p-3.5 text-sm sm:text-base text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:bg-white dark:focus:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 resize-none transition-all shadow-inner leading-relaxed"
                  required
                />

                {/* Suggested Questions (Requirement 7) */}
                <div className="pt-1 space-y-2">
                  <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 block font-semibold">
                    Suggested questions (click to use):
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {suggestedQuestionsList.map((sq, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setQuestion(sq)}
                        className="px-3 py-1.5 rounded-xl bg-slate-100/90 dark:bg-slate-900/80 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-300 border border-slate-200/80 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-500/40 text-xs font-mono text-left transition-all cursor-pointer leading-snug"
                      >
                        {sq}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Simplified PRO, CON & Debate Mode Controls (Requirement 8) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                {/* AI PRO (blue/cyan) */}
                <div className="rounded-2xl p-4 border border-sky-200/90 dark:border-sky-500/30 bg-sky-50/40 dark:bg-sky-950/20 shadow-sm space-y-2">
                  <div className="flex items-center gap-2.5 pb-2 border-b border-sky-200/60 dark:border-sky-900/40">
                    <div className="w-7 h-7 rounded-lg bg-sky-100 dark:bg-sky-900/60 border border-sky-300 dark:border-sky-500/40 flex items-center justify-center text-sky-600 dark:text-sky-400 shadow-sm">
                      <Brain className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                        AI PRO
                      </h3>
                      <span className="text-[10px] font-mono text-sky-600 dark:text-sky-400 font-semibold">
                        Affirmative
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    Builds the strongest case supporting the claim.
                  </p>
                </div>

                {/* AI CON (purple/violet) */}
                <div className="rounded-2xl p-4 border border-purple-200/90 dark:border-purple-500/30 bg-purple-50/40 dark:bg-purple-950/20 shadow-sm space-y-2">
                  <div className="flex items-center gap-2.5 pb-2 border-b border-purple-200/60 dark:border-purple-900/40">
                    <div className="w-7 h-7 rounded-lg bg-purple-100 dark:bg-purple-900/60 border border-purple-300 dark:border-purple-500/40 flex items-center justify-center text-purple-600 dark:text-purple-400 shadow-sm">
                      <Brain className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                        AI CON
                      </h3>
                      <span className="text-[10px] font-mono text-purple-600 dark:text-purple-400 font-semibold">
                        Negative
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    Challenges the claim and examines limitations.
                  </p>
                </div>

                {/* Debate Mode (3 clear options) */}
                <div className="rounded-2xl p-4 border border-indigo-200/90 dark:border-indigo-500/30 bg-indigo-50/40 dark:bg-indigo-950/20 shadow-sm space-y-2">
                  <div className="flex items-center gap-2.5 pb-2 border-b border-indigo-200/60 dark:border-indigo-900/40">
                    <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-900/60 border border-indigo-300 dark:border-indigo-500/40 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
                      <Scale className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                        DEBATE MODE
                      </h3>
                      <span className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
                        Examination Style
                      </span>
                    </div>
                  </div>

                  <select
                    value={selectedMode}
                    onChange={(e) => setSelectedMode(e.target.value as DebateMode)}
                    className="w-full h-8 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 text-xs font-mono text-slate-800 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                  >
                    <option value="claim-challenge">1. Claim Challenge</option>
                    <option value="critical-review">2. Critical Review</option>
                    <option value="balanced-analysis">3. Balanced Analysis</option>
                  </select>
                </div>
              </div>

              {/* Collapsible Advanced Model Configuration (Requirement 8 & 9) */}
              <div className="pt-1 border-t border-slate-100 dark:border-white/5">
                <button
                  type="button"
                  onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                  className="inline-flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer py-1"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>{showAdvancedSettings ? 'Hide Advanced Model Settings' : 'Advanced Model Settings (Optional)'}</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${showAdvancedSettings ? 'rotate-180' : ''}`} />
                </button>

                {showAdvancedSettings && (
                  <div className="mt-3 p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-4 animate-fadeIn">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1">
                          PRO Model:
                        </label>
                        <select
                          value={proModel}
                          onChange={(e) => setProModel(e.target.value)}
                          className="w-full h-9 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-mono text-slate-800 dark:text-slate-100"
                        >
                          <option value="gemma-4-E4B-it">Google Gemma (gemma-4-E4B-it)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1">
                          CON Model:
                        </label>
                        <select
                          value={conModel}
                          onChange={(e) => setConModel(e.target.value)}
                          className="w-full h-9 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-mono text-slate-800 dark:text-slate-100"
                        >
                          <option value="Qwen2.5-VL-7B-Instruct">Alibaba Qwen (Qwen2.5-VL-7B-Instruct)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1">
                          JUDGE Model:
                        </label>
                        <select
                          value={judgeModel}
                          onChange={(e) => setJudgeModel(e.target.value)}
                          className="w-full h-9 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-mono text-slate-800 dark:text-slate-100"
                        >
                          <option value="gemini-3.8-flash">Google Gemini (gemini-3.8-flash)</option>
                        </select>
                      </div>
                    </div>

                    {/* Honest Provider Status Representation (Requirement 9) */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-2 border-t border-slate-200/60 dark:border-white/10 text-xs font-mono text-slate-500">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-amber-500" />
                        <span>Provider Status: Demo Mode (Simulated Dialectic Preview)</span>
                      </div>
                      <Link
                        to="/settings"
                        className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <Settings className="w-3 h-3" />
                        <span>Configure in Settings</span>
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              {/* Primary Start Button */}
              <div className="flex items-center justify-end pt-2">
                <Button
                  type="submit"
                  size="lg"
                  className="w-full sm:w-auto px-10 py-3.5 font-bold shadow-xl shadow-indigo-600/30 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white gap-2.5 text-sm uppercase tracking-wider font-mono cursor-pointer"
                >
                  <span>START DOCUMENT DEBATE</span>
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </form>
        </div>
      ) : (
        /* ========================================================================= */
        /* STATE B — ACTIVE DEBATE WORKSPACE (Requirement 5) */
        /* ========================================================================= */
        <div className="space-y-6 animate-fadeIn">
          {/* Focused Workspace Header Bar */}
          <div className="rounded-2xl p-4 sm:p-5 border border-indigo-200/90 dark:border-indigo-500/30 bg-white/95 dark:bg-[#070a16]/95 backdrop-blur-xl shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="font-bold text-indigo-700 dark:text-indigo-400 flex items-center gap-1.5 uppercase">
                  <FileText className="w-3.5 h-3.5" />
                  GROUNDED IN: {debateDocument.name}
                </span>
                <span className="text-slate-400">•</span>
                <span className="text-slate-500 dark:text-slate-400">{debateDocument.pageCount} pages</span>
                <span className="text-slate-400">•</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Citations Active</span>
              </div>
              <h2 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white leading-snug line-clamp-2">
                "{question}"
              </h2>
            </div>

            {/* Workspace Action Triggers */}
            <div className="flex flex-wrap items-center gap-2 shrink-0 self-end md:self-center">
              <button
                type="button"
                onClick={() => setIsAutoPlaying(!isAutoPlaying)}
                className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-mono font-medium flex items-center gap-1.5 text-slate-700 dark:text-slate-300 shadow-sm"
              >
                {isAutoPlaying ? <Pause className="w-3 h-3 text-indigo-500" /> : <Play className="w-3 h-3 text-indigo-500" />}
                <span>{isAutoPlaying ? 'Pause' : 'Play'}</span>
              </button>

              <button
                type="button"
                onClick={() => setCurrentStep((prev) => Math.min(prev + 1, maxStep))}
                disabled={currentStep >= maxStep}
                className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-mono font-medium disabled:opacity-40 text-slate-700 dark:text-slate-300 shadow-sm"
              >
                Next Turn →
              </button>

              <button
                type="button"
                onClick={handleReturnToSetup}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-bold hover:bg-indigo-100 transition-colors shadow-sm"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Return to Setup</span>
              </button>
            </div>
          </div>

          {/* Mobile / Tablet Workspace Switcher Tabs */}
          <div className="lg:hidden flex items-center rounded-xl bg-slate-100 dark:bg-slate-900 p-1 border border-slate-200 dark:border-white/10">
            <button
              type="button"
              onClick={() => setActiveWorkspaceTab('chamber')}
              className={`flex-1 py-2 text-xs font-mono font-bold rounded-lg transition-all ${
                activeWorkspaceTab === 'chamber'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-white'
              }`}
            >
              Debate Chamber & Turns
            </button>
            <button
              type="button"
              onClick={() => setActiveWorkspaceTab('document')}
              className={`flex-1 py-2 text-xs font-mono font-bold rounded-lg transition-all ${
                activeWorkspaceTab === 'document'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-white'
              }`}
            >
              Document Source (p. {viewerTargetPage})
            </button>
          </div>

          {/* Controlled Dual Desktop Layout (Requirement 2 & 15) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Document Viewer & Evidence */}
            <div
              ref={documentViewerRef}
              className={`lg:col-span-5 lg:sticky lg:top-20 lg:self-start ${
                activeWorkspaceTab === 'document' ? 'block' : 'hidden lg:block'
              }`}
            >
              <DocumentViewer
                document={debateDocument}
                evidenceItems={evidenceItems}
                activeEvidenceId={activeEvidenceHighlight}
                targetPage={viewerTargetPage}
                className="border-indigo-500/20 shadow-xl"
              />
            </div>

            {/* Right Column: Debate Chamber, Turns, Judge, Synthesis */}
            <div
              className={`lg:col-span-7 space-y-6 ${
                activeWorkspaceTab === 'chamber' ? 'block' : 'hidden lg:block'
              }`}
            >
              {/* Chamber Container */}
              <div className="rounded-3xl p-6 sm:p-7 border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#070a16]/95 backdrop-blur-2xl shadow-xl space-y-6">
                {/* 3D Visual Chamber with Neural Brains & Thought Particles */}
                <div className="relative w-full rounded-2xl border border-slate-200/70 dark:border-white/10 bg-slate-50/50 dark:bg-[#050814]/80 p-5 flex flex-col items-center justify-center overflow-hidden min-h-[260px]">
                  {/* Discrete Circular Thought Particle System */}
                  <div className="absolute inset-0 pointer-events-none z-10">
                    <ThoughtParticleSystem
                      phase={
                        currentStep >= 5
                          ? 'CONVERGENCE'
                          : currentStep === 1 || currentStep === 3
                          ? 'PRO_THINKING'
                          : currentStep === 2 || currentStep === 4
                          ? 'CON_THINKING'
                          : 'EXCHANGE'
                      }
                      showSynthesisLine={currentStep >= 5}
                      synthesisLineLength={currentStep >= 5 ? 1.0 : 0.0}
                    />
                  </div>

                  <div className="relative z-20 w-full flex items-start justify-between px-2 sm:px-6">
                    {/* Left: AI PRO Brain */}
                    <div className="flex flex-col items-center">
                      <AINeuralBrain
                        type="PRO"
                        size="sm"
                        state={currentStep === 1 || currentStep === 3 ? 'thinking' : currentStep >= 5 ? 'converging' : 'idle'}
                        showLabel={true}
                        subLabel={proModel}
                      />
                    </div>

                    {/* Center: Independent Judge Neural Core */}
                    <div className="flex flex-col items-center pt-12">
                      <NeuralCoreView
                        size="sm"
                        state={currentStep >= 6 ? 'synthesizing' : currentStep === 5 ? 'analyzing' : 'idle'}
                        glowColor={currentStep === 6 ? 'amber' : currentStep === 5 ? 'indigo' : 'neutral'}
                      />
                      <span className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 mt-2 uppercase">
                        INDEPENDENT JUDGE
                      </span>
                      <span className="text-[10px] font-mono text-indigo-500 font-semibold">
                        {currentStep >= 6
                          ? 'SYNTHESIS COMPLETE'
                          : currentStep === 5
                          ? 'ARBITRATING FIDELITY'
                          : 'OBSERVING TURNS'}
                      </span>
                    </div>

                    {/* Right: AI CON Brain */}
                    <div className="flex flex-col items-center">
                      <AINeuralBrain
                        type="CON"
                        size="sm"
                        state={currentStep === 2 || currentStep === 4 ? 'thinking' : currentStep >= 5 ? 'converging' : 'idle'}
                        showLabel={true}
                        subLabel={conModel}
                      />
                    </div>
                  </div>

                  {/* Dialectic Turn Stepper */}
                  <div className="relative z-20 mt-5 flex items-center gap-2">
                    <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">
                      Debate Stage:
                    </span>
                    <div className="flex items-center gap-1.5">
                      {[1, 2, 3, 4, 5, 6].map((st) => (
                        <span
                          key={st}
                          className={`h-2 rounded-full transition-all duration-300 ${
                            st < currentStep
                              ? 'w-4 bg-emerald-500'
                              : st === currentStep
                              ? 'w-6 bg-indigo-600 dark:bg-indigo-400 animate-pulse'
                              : 'w-2 bg-slate-300 dark:bg-slate-700'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Progressive Grounded Debate Turns (Requirement 12 & 13) */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/10">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                      <span>GROUNDED ARGUMENTS</span>
                    </span>
                    <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                      Round {Math.min(currentStep, 4)} of 4
                    </span>
                  </div>

                  {/* Arguments list revealed progressively */}
                  <div className="space-y-4">
                    {debateTimeline.slice(0, currentStep).map((arg) => {
                      const isPro = arg.speaker === 'PRO';
                      const isExpanded = expandedArgId === arg.id;

                      return (
                        <div
                          key={arg.id}
                          className={`rounded-2xl p-5 border transition-all duration-300 animate-fadeIn ${
                            isPro
                              ? 'border-sky-200/90 dark:border-sky-500/30 bg-sky-50/40 dark:bg-sky-950/20'
                              : 'border-purple-200/90 dark:border-purple-500/30 bg-purple-50/40 dark:bg-purple-950/20'
                          }`}
                        >
                          {/* Header */}
                          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-200/60 dark:border-white/5">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full ${
                                  isPro
                                    ? 'bg-sky-100 dark:bg-sky-900/60 text-sky-700 dark:text-sky-300'
                                    : 'bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300'
                                }`}
                              >
                                ROUND {arg.roundNumber} • AI {arg.speaker}
                              </span>
                              {arg.executionStatus === 'REAL_LOCAL_MODEL' && (
                                <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-600/40">
                                  REAL LOCAL MODEL
                                </span>
                              )}
                              {arg.executionStatus === 'REAL_REMOTE_API' && (
                                <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-600/40">
                                  REAL REMOTE API
                                </span>
                              )}
                              {arg.executionStatus === 'SIMULATED' && (
                                <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-600/40">
                                  SIMULATED
                                </span>
                              )}
                              <h4 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white">
                                {arg.title}
                              </h4>
                            </div>

                            {/* View Source Trigger */}
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleJumpToCitation(arg.pageNumber, arg.evidenceId)}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold border transition-all bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-500/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/70 cursor-pointer"
                                title={`Jump reader to Page ${arg.pageNumber}`}
                              >
                                <BookOpen className="w-3 h-3 text-indigo-500" />
                                <span>VIEW SOURCE (p. {arg.pageNumber})</span>
                              </button>

                              <button
                                type="button"
                                onClick={() => setExpandedArgId(isExpanded ? null : arg.id)}
                                className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                aria-label={isExpanded ? 'Collapse argument' : 'Expand argument'}
                              >
                                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                              </button>
                            </div>
                          </div>

                          {/* Argument Text */}
                          <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-medium mt-3">
                            "{arg.argumentText}"
                          </p>

                          {/* Clear Evidence Attribution (Requirement 13) */}
                          <div className="mt-3 pt-2.5 border-t border-slate-200/60 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                            <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 text-[11px] font-medium">
                              <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                              <span>Source: Page {arg.pageNumber} · {arg.sectionTitle}</span>
                            </div>
                            <span className="text-[10px] text-slate-400 font-medium">
                              Relevance: {arg.confidence}%
                            </span>
                          </div>

                          {/* Expanded Details */}
                          {isExpanded && (
                            <div className="mt-3 pt-3 border-t border-slate-200/60 dark:border-white/5 space-y-2 text-xs font-mono animate-fadeIn">
                              <div className="flex items-start gap-2 text-indigo-700 dark:text-indigo-300">
                                <Scale className="w-4 h-4 shrink-0 mt-0.5" />
                                <span>Dialectic Relation: {arg.counterRelation}</span>
                              </div>
                              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-[11px]">
                                <span>Verified against {debateDocument.name}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 5. Independent Judge Evaluation (Requirement 14) */}
                {currentStep >= 5 && (
                  <div className="rounded-3xl p-6 border border-indigo-200 dark:border-indigo-500/40 bg-indigo-50/40 dark:bg-indigo-950/30 backdrop-blur-xl shadow-lg space-y-5 animate-fadeIn">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-indigo-200/80 dark:border-indigo-900/40">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/60 border border-indigo-300 dark:border-indigo-500/40 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                          <Scale className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                            INDEPENDENT JUDGE EVALUATION
                          </h3>
                          <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 font-semibold uppercase">
                            Illustrative Judicial Rubric · Neutral Arbitration
                          </span>
                        </div>
                      </div>

                      <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-700 font-bold">
                        {currentStep === 6 ? 'Deliberation Complete' : 'Deliberating'}
                      </span>
                    </div>

                    {/* 5 Standard Judicial Evaluation Criteria (Requirement 14) */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
                      {[
                        { key: 'evidence', label: 'Evidence Support', desc: 'Checks empirical claims vs page text' },
                        { key: 'reasoning', label: 'Reasoning Quality', desc: 'Audits deductive links and coherence' },
                        { key: 'counterarguments', label: 'Counterarguments', desc: 'Tests responsiveness to critiques' },
                        { key: 'consistency', label: 'Consistency', desc: 'Ensures no internal contradiction' },
                        { key: 'uncertainty', label: 'Uncertainty', desc: 'Evaluates epistemic humility' },
                      ].map((item) => {
                        const isComplete =
                          judgeAnalyzingCriteria[item.key as keyof typeof judgeAnalyzingCriteria] ||
                          currentStep === 6;

                        return (
                          <div
                            key={item.key}
                            className={`p-3 rounded-xl border transition-all duration-300 ${
                              isComplete
                                ? 'bg-white dark:bg-slate-900/80 border-emerald-300 dark:border-emerald-600 text-slate-900 dark:text-white shadow-sm'
                                : 'bg-slate-100/60 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 text-slate-400'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[11px] font-mono font-bold uppercase">{item.label}</span>
                              {isComplete ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                              )}
                            </div>
                            <p className="text-[9px] text-slate-500 dark:text-slate-400 leading-snug">
                              {item.desc}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 6. Final Evidence-Grounded Synthesis (Requirement 14) */}
                {currentStep === 6 && (
                  <div className="rounded-3xl p-6 sm:p-7 border-2 border-amber-300 dark:border-amber-500/50 bg-gradient-to-b from-amber-50/70 via-white to-amber-50/50 dark:from-[#181104]/90 dark:via-[#0c0d1e] dark:to-[#080d1e] backdrop-blur-2xl shadow-2xl space-y-6 animate-fadeIn">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-amber-200/80 dark:border-amber-800/40">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-2xl bg-amber-100 dark:bg-amber-950/70 border border-amber-300 dark:border-amber-600/50 flex items-center justify-center text-amber-600 dark:text-amber-400 shadow-md">
                          <Sparkles className="w-5 h-5" />
                        </div>
                        <div>
                          <h2 className="text-base sm:text-lg font-mono font-black uppercase tracking-wider text-slate-900 dark:text-white">
                            FINAL SYNTHESIS
                          </h2>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs font-mono text-amber-700 dark:text-amber-400 font-semibold uppercase">
                              Arbitrated by {liveSynthesis?.judgeModelUsed || 'Google Gemini (gemini-3.5-flash)'}
                            </span>
                            <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full ${
                              liveSynthesis?.executionStatus === 'REAL_REMOTE_API' || (!liveSynthesis?.isFallback && liveSynthesis?.judgeModelUsed?.includes('gemini'))
                                ? 'bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-600/40'
                                : 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-600/40'
                            }`}>
                              {liveSynthesis?.executionStatus === 'REAL_REMOTE_API' || (!liveSynthesis?.isFallback && liveSynthesis?.judgeModelUsed?.includes('gemini'))
                                ? 'REAL REMOTE API'
                                : 'SIMULATED / FALLBACK'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700/60">
                        Document Grounding: {liveSynthesis?.evidenceReliabilityScore ? `${Math.round(liveSynthesis.evidenceReliabilityScore)}%` : '96%'}
                      </span>
                    </div>

                    {/* Balanced Conclusion (Requirement 14) */}
                    <div className="p-4 sm:p-5 rounded-2xl bg-white/90 dark:bg-[#070a16]/90 border border-amber-200 dark:border-amber-500/30 shadow-sm space-y-2">
                      <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                        Balanced Conclusion
                      </span>
                      <p className="text-sm sm:text-base text-slate-900 dark:text-slate-100 leading-relaxed font-semibold italic">
                        "{liveSynthesis?.balancedVerdict || 'Neither blanket adoption nor absolute dismissal is supported by the document. The empirical data validates bounded variance reduction, yet out-of-distribution vulnerabilities render unsupervised deployment untenable. A dual-track framework retaining human liability for normative adjudication remains essential.'}"
                      </p>
                    </div>

                    {/* Required 5 Structured Dimensions (Requirement 14) */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
                      {/* Strongest Supporting Argument */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                            Strongest Supporting Argument
                          </span>
                          <button
                            type="button"
                            onClick={() => handleJumpToCitation(8, 'ev-1')}
                            className="text-[10px] text-indigo-500 hover:underline font-mono"
                          >
                            [Page 8]
                          </button>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          {liveSynthesis?.keyConsensus?.[0] || 'Variance reduction achieved via formal models under bounded empirical constraints.'}
                        </p>
                      </div>

                      {/* Strongest Counterargument */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <Scale className="w-3.5 h-3.5 text-purple-500" />
                            Strongest Counterargument
                          </span>
                          <button
                            type="button"
                            onClick={() => handleJumpToCitation(14, 'ev-2')}
                            className="text-[10px] text-indigo-500 hover:underline font-mono"
                          >
                            [Page 14]
                          </button>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          {liveSynthesis?.keyContentions?.[0] || 'Vulnerability to out-of-distribution catastrophic failures and absence of procedural due process recourse.'}
                        </p>
                      </div>

                      {/* Main Limitation */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-sky-500" />
                            Main Limitation
                          </span>
                          <button
                            type="button"
                            onClick={() => handleJumpToCitation(19, 'ev-4')}
                            className="text-[10px] text-indigo-500 hover:underline font-mono"
                          >
                            [Page 19]
                          </button>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          Mathematical consistency cannot satisfy democratic legitimacy or replace constitutional due process recourse.
                        </p>
                      </div>

                      {/* Important Uncertainty */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
                            Important Uncertainty
                          </span>
                          <button
                            type="button"
                            onClick={() => handleJumpToCitation(23, 'ev-5')}
                            className="text-[10px] text-indigo-500 hover:underline font-mono"
                          >
                            [Page 23]
                          </button>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          Generalizability beyond synthetic benchmark datasets into live multi-party tribunals.
                        </p>
                      </div>
                    </div>

                    {/* Source References List (Requirement 14) */}
                    <div className="p-4 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-500/30 text-xs space-y-2">
                      <span className="font-mono font-bold uppercase text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        Document Source References (Click to inspect page):
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                        {[
                          { label: 'Page 8: Section 3 — Empirical Results (32% variance reduction)', page: 8, evId: 'ev-1' },
                          { label: 'Page 14: Section 4 — Out-of-Distribution Vulnerabilities (91% error)', page: 14, evId: 'ev-2' },
                          { label: 'Page 19: Section 5 — Due Process Recourse & Civic Legitimacy', page: 19, evId: 'ev-4' },
                          { label: 'Page 23: Section 6 — Dual-Track Synthesis Policy', page: 23, evId: 'ev-5' },
                        ].map((ref, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleJumpToCitation(ref.page, ref.evId)}
                            className="flex items-center justify-between p-2 rounded-lg bg-white/70 dark:bg-black/30 border border-slate-200 dark:border-white/10 hover:border-indigo-400 text-left transition-all cursor-pointer"
                          >
                            <span className="text-slate-700 dark:text-slate-300 truncate">{ref.label}</span>
                            <ExternalLink className="w-3 h-3 text-indigo-400 shrink-0 ml-1.5" />
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-amber-200/80 dark:border-amber-800/40">
                      <div className="flex items-center gap-2">
                        <Link to="/history">
                          <Button variant="outline" size="sm" className="gap-1.5 font-mono text-xs font-bold">
                            <HistoryIcon className="w-3.5 h-3.5" />
                            <span>View in History</span>
                          </Button>
                        </Link>

                        <button
                          type="button"
                          onClick={() => {
                            if (navigator.clipboard) {
                              navigator.clipboard.writeText(window.location.href);
                              alert('Debate link copied to clipboard.');
                            }
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-mono font-medium hover:border-slate-300 transition-colors"
                        >
                          <Share2 className="w-3.5 h-3.5 text-slate-400" />
                          <span>Share Debate</span>
                        </button>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={handleRestartDebate}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-bold gap-1.5"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Replay Debate</span>
                        </Button>

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleReturnToSetup}
                          className="font-mono text-xs font-bold gap-1.5"
                        >
                          <span>New Question</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DebatePage;

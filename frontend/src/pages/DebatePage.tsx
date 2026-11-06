import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Scale,
  Sparkles,
  ShieldCheck,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  History as HistoryIcon,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Share2,
  FileText,
  FileImage,
  ExternalLink,
  BookOpen,
  Sliders,
  AlertCircle,
  AlertTriangle,
  Bot,
  Loader2,
  Check,
  Gavel,
  Globe,
  RefreshCw,
  XCircle,
  StopCircle,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { NeuralCoreView } from '../components/common/NeuralCoreView';
import { AINeuralBrain } from '../components/common/AINeuralBrain';
import { ThoughtParticleSystem } from '../components/common/ThoughtParticleSystem';
import { DocumentViewer } from '../components/document/DocumentViewer';
import { DocumentKnowledgeModal } from '../components/document/DocumentKnowledgeModal';
import { ExistingDocumentPicker } from '../components/document/ExistingDocumentPicker';
import { CompactStatusIndicator } from '../components/common/CompactStatusIndicator';
import { useDocument } from '../context/DocumentContext';
import { validateDocumentFile } from '../lib/documentValidation';
import { DebateMode, DocumentMetadata } from '../types/document';
import { debateApi } from '../services/api';
import { DebateSession, DebateSynthesis, ResearchResponse, ResearchStage } from '../types/debate';
import { getDocumentSuggestedPropositions } from '../lib/suggestedPropositions';

const EXAMPLE_PROPOSITIONS = [
  'Will artificial intelligence replace human jobs?',
  'Should AI be used in education?',
  'Can renewable energy fully replace fossil fuels?',
  'Are Transformer architectures superior to recurrent networks?',
  'Should social media platforms be regulated?',
  'Does automation benefit developing economies?',
];

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

function formatElapsedTime(seconds: number): string {
  const safeSec = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(safeSec / 3600);
  const mins = Math.floor((safeSec % 3600) / 60);
  const secs = safeSec % 60;
  if (hrs > 0) {
    return `${hrs}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

function resolveDebateStartMs(deb: DebateSession): number | null {
  if (typeof deb.startedAtEpochMs === 'number' && deb.startedAtEpochMs > 0) {
    return deb.startedAtEpochMs;
  }
  if (deb.startedAtIso) {
    const ms = new Date(deb.startedAtIso).getTime();
    if (!isNaN(ms)) return ms;
  }
  if (deb.createdAt) {
    const raw = deb.createdAt.trim();
    if (raw.endsWith('Z') || raw.includes('+') || raw.includes('GMT')) {
      const ms = new Date(raw).getTime();
      if (!isNaN(ms)) return ms;
    }
    const utcParsed = new Date(raw + ' UTC').getTime();
    if (!isNaN(utcParsed)) return utcParsed;
    const directParsed = new Date(raw).getTime();
    if (!isNaN(directParsed)) return directParsed;
  }
  return null;
}

function resolveDebateCompleteMs(deb: DebateSession): number | null {
  if (typeof deb.completedAtEpochMs === 'number' && deb.completedAtEpochMs > 0) {
    return deb.completedAtEpochMs;
  }
  if (deb.completedAt) {
    const raw = deb.completedAt.trim();
    if (raw.endsWith('Z') || raw.includes('+') || raw.includes('GMT')) {
      const ms = new Date(raw).getTime();
      if (!isNaN(ms)) return ms;
    }
    const utcParsed = new Date(raw + ' UTC').getTime();
    if (!isNaN(utcParsed)) return utcParsed;
    const directParsed = new Date(raw).getTime();
    if (!isNaN(directParsed)) return directParsed;
  }
  return null;
}

export const DebatePage: React.FC = () => {
  const location = useLocation();
  const documentViewerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    documents,
    activeDocument,
    selectDocument,
    uploadDocument,
    activeKnowledge,
    isProcessing,
    evidenceItems,
    selectedMode,
    setSelectedMode,
  } = useDocument();

  // Snapshot of document used when active debate was started (null for web debates)
  const [debateDocument, setDebateDocument] = useState<DocumentMetadata | null>(null);

  // Active View Tab on mobile / tablets (chamber vs document)
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'chamber' | 'document'>('chamber');

  // Document Viewer target page controller
  const [viewerTargetPage, setViewerTargetPage] = useState<number>(8);
  const [activeEvidenceHighlight, setActiveEvidenceHighlight] = useState<string | null>('ev-1');

  // Form Parameters & Evidence Source Modes
  const [sourceMode, setSourceMode] = useState<'document' | 'web' | null>(null);
  const [isDebateEnded, setIsDebateEnded] = useState<boolean>(false);
  const [cancellationError, setCancellationError] = useState<string | null>(null);
  const [question, setQuestion] = useState<string>('');
  const [rounds, setRounds] = useState<number>(3); // Standardized to 3 default (Options: 1, 3, 5)
  const [strictFactChecking, setStrictFactChecking] = useState<boolean>(true);
  const proModel = 'gemma-4-E4B-it';
  const conModel = 'Qwen2.5-VL-7B-Instruct';
  const [judgeProvider, setJudgeProvider] = useState<'gemini' | 'nvidia'>('nvidia');
  const [judgeModel, setJudgeModel] = useState<string>('nvidia/nemotron-3.5-super-vl-120b-a12b');
  const [showAdvancedSettings, setShowAdvancedSettings] = useState<boolean>(false);
  const [showCriteriaBreakdown, setShowCriteriaBreakdown] = useState<boolean>(true);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Web Research Pipeline States
  const [isResearching, setIsResearching] = useState<boolean>(false);
  const [researchResponse, setResearchResponse] = useState<ResearchResponse | null>(null);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [researchStages, setResearchStages] = useState<ResearchStage[]>([]);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState<boolean>(false);

  // Modals
  const [isKnowledgeModalOpen, setIsKnowledgeModalOpen] = useState<boolean>(false);
  const [isDocumentPickerOpen, setIsDocumentPickerOpen] = useState<boolean>(false);

  // Live Backend State Integration
  const [activeDebateId, setActiveDebateId] = useState<string | null>(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const qId = params.get('id');
      if (qId) return qId;
      return null;
    } catch (_) {
      return null;
    }
  });
  const [liveSession, setLiveSession] = useState<DebateSession | null>(null);
  const [liveSynthesis, setLiveSynthesis] = useState<DebateSynthesis | null>(null);
  const [backendStatusMessage, setBackendStatusMessage] = useState<string>('Ready to initialize debate');
  const [isLiveBackendConnected, setIsLiveBackendConnected] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [showEndDebateModal, setShowEndDebateModal] = useState<boolean>(false);

  // Authoritative persistent timestamps for drift-free stopwatch
  const [debateStartTimeMs, setDebateStartTimeMs] = useState<number | null>(null);
  const [debateCompletedTimeMs, setDebateCompletedTimeMs] = useState<number | null>(null);

  // Simulation Lifecycle State: State A (false) vs State B (true)
  const [hasStarted, setHasStarted] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [expandedArgId, setExpandedArgId] = useState<string | null>(null);

  // Synchronize debateDocument with activeDocument ONLY in setup mode (when no debate is active)
  useEffect(() => {
    if (!hasStarted && !activeDebateId) {
      if (sourceMode === 'document') {
        setDebateDocument(activeDocument);
      } else {
        setDebateDocument(null);
      }
    }
  }, [activeDocument, hasStarted, activeDebateId, sourceMode]);

  // Sync activeDebateId with sessionStorage and localStorage only when active
  useEffect(() => {
    if (activeDebateId) {
      sessionStorage.setItem('activeDebateId', activeDebateId);
      localStorage.setItem('activeDebateId', activeDebateId);
    }
  }, [activeDebateId]);

  // Comprehensive persistent debate restoration across page navigation and browser refresh
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      let candidateId: string | null = null;
      let isExplicitUrlParam = false;

      try {
        const params = new URLSearchParams(window.location.search);
        const urlId = params.get('id');
        if (urlId) {
          candidateId = urlId;
          isExplicitUrlParam = true;
        }
      } catch (_) {}

      // If no explicit ?id= in URL, query backend for any genuinely active debate
      if (!candidateId) {
        try {
          const activeCheck = await debateApi.getActiveDebate();
          if (activeCheck && activeCheck.hasActive && activeCheck.debateId && isMounted) {
            candidateId = activeCheck.debateId;
          }
        } catch (_) {}
      }

      // If still no active debate, clear any stale IDs in browser storage so page stays in idle State A
      if (!candidateId) {
        sessionStorage.removeItem('activeDebateId');
        localStorage.removeItem('activeDebateId');
        if (isMounted) {
          setActiveDebateId(null);
          setHasStarted(false);
          setDebateStartTimeMs(null);
          setDebateCompletedTimeMs(null);
          setElapsedSeconds(0);
        }
        return;
      }

      if (!isMounted) return;

      try {
        const deb = await debateApi.getDebate(candidateId);
        if (!isMounted || !deb) return;

        // If not explicit in URL and debate is finished (failed/cancelled/completed), do not hijack empty Chamber
        if (!isExplicitUrlParam && (deb.status === 'failed' || deb.status === 'cancelled')) {
          sessionStorage.removeItem('activeDebateId');
          localStorage.removeItem('activeDebateId');
          return;
        }

        setActiveDebateId(deb.id);
        sessionStorage.setItem('activeDebateId', deb.id);
        localStorage.setItem('activeDebateId', deb.id);
        window.history.replaceState(null, '', `/debate?id=${deb.id}`);

        setHasStarted(true);
        setIsLiveBackendConnected(true);
        setQuestion(deb.topic);
        setLiveSession(deb);

        // 1. Authoritative Evidence Mode & Source Restoration from backend record
        const isWeb =
          deb.sourceScope === 'web' ||
          deb.config?.sourceScope === 'web' ||
          (!deb.documentId && !deb.config?.documentId && ((deb.researchSources && deb.researchSources.length > 0) || !deb.documentName));

        if (isWeb) {
          setSourceMode('web');
          setDebateDocument(null);
          // Restore research sources into researchResponse for the shared evidence drawer
          if (deb.researchSources && deb.researchSources.length > 0) {
            setResearchResponse({
              topic: deb.topic,
              query: deb.topic,
              sources: deb.researchSources.map((s: any) => ({
                id: s.id || String(Math.random()),
                title: s.title || '',
                url: s.url || '',
                snippet: s.snippet || s.content || '',
                publishedDate: s.publishedDate || s.published_date || '',
                retrievalTimestamp: s.retrievalTimestamp || '',
              })),
              evidenceItems: [],
              stages: [],
              indexedChunks: deb.researchSources.length,
              status: 'completed',
              message: 'Restored from debate record',
            });
          }
        } else {
          setSourceMode('document');
          const targetDocId = deb.documentId || deb.config?.documentId;
          if (targetDocId) {
            // Find in current documents or fetch directly from backend
            let matchedDoc: DocumentMetadata | null = documents.find((d) => d.id === targetDocId) || null;
            if (!matchedDoc) {
              try {
                const fetchedDoc = await debateApi.getDocument(targetDocId);
                if (fetchedDoc && fetchedDoc.id) {
                  matchedDoc = fetchedDoc;
                }
              } catch (_) {}
            }
            if (!matchedDoc) {
              try {
                const allDocs = await debateApi.getDocuments();
                matchedDoc = allDocs.find((d) => d.id === targetDocId) || null;
              } catch (_) {}
            }

            if (matchedDoc) {
              setDebateDocument(matchedDoc);
              selectDocument(matchedDoc.id);
            } else {
              // Exact associated document not found: Show clear missing state, NEVER silently substitute another PDF
              setDebateDocument({
                id: targetDocId,
                name: deb.documentName || deb.config?.documentName || 'Associated Document',
                fileType: (deb.documentType || deb.config?.documentType || 'pdf') as any,
                fileSize: '0 KB',
                fileSizeBytes: 0,
                pageCount: 0,
                uploadedAt: deb.createdAt || '',
                status: 'error',
                summary: 'Document record missing from repository',
                keyClaimsCount: 0,
                evidencePointsCount: 0,
                debatesCount: 0,
                sections: [],
                suggestedQuestions: [],
                isMissing: true,
              });
            }
          } else if (deb.documentName || deb.config?.documentName) {
            const targetName = deb.documentName || deb.config?.documentName;
            const matchedDoc = documents.find((d) => d.name === targetName) || null;
            if (matchedDoc) {
              setDebateDocument(matchedDoc);
              selectDocument(matchedDoc.id);
            } else {
              setDebateDocument(null);
            }
          } else {
            setDebateDocument(null);
          }
        }

        if (deb.config) {
          setRounds(deb.config.rounds || 3);
        }

        // Authoritative timestamp extraction (UTC-safe, zero timezone drift)
        const startMs = resolveDebateStartMs(deb);
        const compMs = resolveDebateCompleteMs(deb);
        setDebateStartTimeMs(startMs);
        setDebateCompletedTimeMs(compMs);

        if (deb.status === 'completed' || deb.status === 'cancelled' || deb.status === 'failed') {
          if (typeof deb.elapsedSeconds === 'number' && deb.elapsedSeconds >= 0) {
            setElapsedSeconds(deb.elapsedSeconds);
          } else if (startMs && compMs) {
            setElapsedSeconds(Math.max(0, Math.floor((compMs - startMs) / 1000)));
          } else if (startMs) {
            setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));
          }
        } else if (startMs) {
          setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));
        }

        // Restore accurate current step
        const totalTurns = deb.rounds ? deb.rounds.reduce((acc, r) => acc + r.turns.length, 0) : 0;
        const expectedTurns = (deb.config?.rounds || 3) * 2;
        if (deb.status === 'completed') {
          setCurrentStep(expectedTurns + 2);
          if (deb.synthesis) setLiveSynthesis(deb.synthesis);
          setBackendStatusMessage('Debate Adjudication Complete!');
        } else if (deb.status === 'cancelled') {
          setCurrentStep(totalTurns);
          setBackendStatusMessage('Debate was cancelled.');
        } else if (deb.status === 'failed') {
          setCurrentStep(totalTurns);
          setBackendStatusMessage(`Debate Failed: ${deb.errorMessage || deb.error_message || 'Execution error'}`);
        } else if (totalTurns >= expectedTurns) {
          setCurrentStep(expectedTurns + 1);
          setBackendStatusMessage(`All ${expectedTurns} turns complete. Evaluating transcript...`);
        } else {
          setCurrentStep(totalTurns);
          setBackendStatusMessage(`Active debate restored (ID: ${deb.id.slice(0, 8)}). Resuming live tracking...`);
        }
      } catch (err) {
        console.warn('Failed to restore debate session:', err);
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // Live Token Streaming & Performance Telemetry
  const [streamingSpeaker, setStreamingSpeaker] = useState<'PRO' | 'CON' | null>(null);
  const [streamingRound, setStreamingRound] = useState<number>(1);
  const [streamingText, setStreamingText] = useState<string>('');
  const [streamingModel, setStreamingModel] = useState<string>('');
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [tokenCount, setTokenCount] = useState<number>(0);

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

  // Handle URL query parameters (?doc=...&question=...&mode=...&source=...)
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const docParam = searchParams.get('doc');
    const questionParam = searchParams.get('question') || searchParams.get('q');
    const modeParam = searchParams.get('mode') as DebateMode | null;
    const sourceParam = searchParams.get('source');

    if (docParam) {
      selectDocument(docParam);
      setSourceMode('document');
    } else if (sourceParam === 'document') {
      setSourceMode('document');
    } else if (sourceParam === 'web') {
      setSourceMode('web');
    }

    if (questionParam) {
      setQuestion(decodeURIComponent(questionParam));
    }
    if (modeParam && ['claim-challenge', 'critical-review', 'balanced-analysis'].includes(modeParam)) {
      setSelectedMode(modeParam);
    }
  }, [location.search, selectDocument, setSelectedMode]);

  // Dynamically resolve timeline strictly from real live turns from backend session
  const debateTimeline: GroundedArgument[] = useMemo(() => {
    if (liveSession && liveSession.rounds && liveSession.rounds.length > 0) {
      const liveArgs: GroundedArgument[] = [];
      liveSession.rounds.forEach((rnd) => {
        rnd.turns.forEach((turn, idx) => {
          const isPro = turn.role === 'PRO' || turn.speaker === 'DEBATER_A';
          const ev = turn.evidence && turn.evidence.length > 0 ? (turn.evidence[0] as any) : null;
          const isDocImage = debateDocument && ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((debateDocument.fileType || '').toLowerCase());
          let pageNum: number | undefined = undefined;
          if (ev?.pageNumber) pageNum = Number(ev.pageNumber);
          else if (ev?.page) pageNum = Number(ev.page);
          else if (ev?.source) {
            const m = String(ev.source).match(/page\s*(\d+)/i);
            if (m) pageNum = parseInt(m[1], 10);
          }

          const evId = ev?.evidence_id || ev?.evidenceId || ev?.id || `ev-${rnd.roundNumber}-${idx}`;

          liveArgs.push({
            id: `turn-${rnd.roundNumber}-${isPro ? 'pro' : 'con'}-${idx}`,
            roundNumber: rnd.roundNumber,
            speaker: isPro ? 'PRO' : 'CON',
            title: turn.title || (isPro ? `Round ${rnd.roundNumber} Affirmative Case` : `Round ${rnd.roundNumber} Opposition Rebuttal`),
            argumentText: turn.content,
            confidence: (turn as any).confidence || (ev?.confidenceScore ? Math.round(ev.confidenceScore) : 92),
            pageNumber: isDocImage ? 1 : (pageNum || 1),
            sectionTitle: ev?.sectionTitle || ev?.section || (isDocImage ? 'Visual Evidence' : (isPro ? 'Affirmative Case' : 'Counter-Examination Rebuttal')),
            supportingEvidence: ev?.claim || (ev?.content ? `"${ev.content.slice(0, 160)}..."` : `${debateDocument?.name || 'Document'} verified reference`),
            counterRelation: isPro ? 'Affirmative Grounding: Cites verified documentary findings.' : 'Direct Clash: Rebuts PRO claims directly.',
            evidenceId: evId,
            executionStatus: turn.executionStatus || 'REAL_LOCAL_MODEL'
          });
        });
      });
      return liveArgs;
    }
    return [];
  }, [liveSession, debateDocument]);

  // Single authoritative source of truth for evidence mode in active/running/replay debate
  const isCurrentDebateWeb = useMemo(() => {
    if (sourceMode === 'web') return true;
    if (liveSession?.config?.sourceScope === 'web' || (liveSession as any)?.sourceScope === 'web') return true;
    if (liveSession?.researchSources && liveSession.researchSources.length > 0 && !liveSession?.config?.documentId && !(liveSession as any)?.documentId) return true;
    if (!debateDocument && !liveSession?.config?.documentId && !(liveSession as any)?.documentId) return true;
    return false;
  }, [sourceMode, liveSession, debateDocument]);

  // Dynamic calculation of debate rounds and steps
  const activeRounds = useMemo(() => {
    const r = liveSession?.config?.rounds || rounds || 3;
    return [1, 3, 5].includes(r) ? r : 3;
  }, [liveSession?.config?.rounds, rounds]);

  const totalTurnsExpected = activeRounds * 2;
  const judgeStep = totalTurnsExpected + 1;
  const completedStep = totalTurnsExpected + 2;
  const totalSteps = completedStep;

  const currentDisplayRound = useMemo(() => {
    if (streamingRound) return Math.min(Math.max(1, streamingRound), activeRounds);
    if (currentStep <= 0) return 1;
    if (currentStep >= judgeStep) return activeRounds;
    return Math.min(Math.max(1, Math.ceil(currentStep / 2)), activeRounds);
  }, [streamingRound, currentStep, judgeStep, activeRounds]);

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
        const expectedTurns = (session.config?.rounds || activeRounds) * 2;
        const currentJudgeStep = expectedTurns + 1;
        const currentCompletedStep = expectedTurns + 2;

        if (session.status === 'completed') {
          setCurrentStep(currentCompletedStep);
          setBackendStatusMessage('Debate Adjudication Complete!');
          const compMs = resolveDebateCompleteMs(session) || Date.now();
          setDebateCompletedTimeMs(compMs);
          if (typeof session.elapsedSeconds === 'number') {
            setElapsedSeconds(session.elapsedSeconds);
          } else if (debateStartTimeMs) {
            setElapsedSeconds(Math.max(0, Math.floor((compMs - debateStartTimeMs) / 1000)));
          }
          if (session.synthesis) {
            setLiveSynthesis(session.synthesis);
          } else {
            try {
              const syn = await debateApi.getDebateResult(activeDebateId);
              if (isMounted) setLiveSynthesis(syn);
            } catch (_) {}
          }
          clearInterval(interval);
        } else if (session.status === 'cancelled') {
          setStreamingSpeaker(null);
          setBackendStatusMessage('Debate was cancelled.');
          if (typeof session.elapsedSeconds === 'number') {
            setElapsedSeconds(session.elapsedSeconds);
          }
          clearInterval(interval);
        } else if (session.status === 'failed') {
          setStreamingSpeaker(null);
          setBackendStatusMessage(`Debate Failed: ${session.error_message || session.errorMessage || 'Execution error'}`);
          if (typeof session.elapsedSeconds === 'number') {
            setElapsedSeconds(session.elapsedSeconds);
          }
          clearInterval(interval);
        } else if (totalTurns >= expectedTurns) {
          setCurrentStep(currentJudgeStep);
          const activeJudge = session.config?.judgeProvider === 'nvidia' ? 'NVIDIA NIM' : 'Google Gemini';
          setBackendStatusMessage(`All ${expectedTurns} turns complete. ${activeJudge} (JUDGE) is evaluating transcript...`);
        } else {
          setCurrentStep(totalTurns);
          const latestRound = session.rounds[session.rounds.length - 1];
          const latestTurn = latestRound?.turns[latestRound.turns.length - 1];
          if (latestTurn) {
            setBackendStatusMessage(`Round ${latestRound.roundNumber}: ${latestTurn.speaker} (${latestTurn.role}) completed`);
          }
        }
      } catch (err) {
        console.warn('Error polling debate status:', err);
      }
    }, 2500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeDebateId, activeRounds, debateStartTimeMs]);

  // Real-time authoritative stopwatch timer (wall-clock synchronized to backend start)
  useEffect(() => {
    if (!hasStarted || !activeDebateId || !debateStartTimeMs) return;

    const isFinished = liveSession?.status === 'completed' || liveSession?.status === 'failed' || liveSession?.status === 'cancelled';
    if (isFinished) {
      if (debateCompletedTimeMs && debateStartTimeMs) {
        setElapsedSeconds(Math.max(0, Math.floor((debateCompletedTimeMs - debateStartTimeMs) / 1000)));
      } else if (typeof liveSession?.elapsedSeconds === 'number') {
        setElapsedSeconds(liveSession.elapsedSeconds);
      }
      return;
    }

    // Authoritative wall-clock sync: Date.now() - debateStartTimeMs
    const tick = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - debateStartTimeMs) / 1000)));
    };

    tick();
    const timer = setInterval(tick, 1000);

    return () => {
      clearInterval(timer);
    };
  }, [hasStarted, activeDebateId, debateStartTimeMs, debateCompletedTimeMs, liveSession?.status, liveSession?.elapsedSeconds]);

  // Server-Sent Events (SSE) live token streaming
  useEffect(() => {
    if (!activeDebateId) return;

    const streamUrl = `http://localhost:8000/api/debates/${activeDebateId}/stream`;
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'phase') {
            setBackendStatusMessage(data.message || 'Processing turn...');
          } else if (data.type === 'speaker_start') {
            setStreamingSpeaker(data.speaker);
            setStreamingRound(data.round || 1);
            setStreamingModel(data.model || '');
            setStreamingText('');
            setTokenCount(0);
            setBackendStatusMessage(data.message || `${data.speaker} generating response...`);
          } else if (data.type === 'token') {
            setStreamingText((prev) => prev + (data.delta || ''));
            setTokenCount((prev) => prev + 1);
          } else if (data.type === 'speaker_done') {
            setStreamingSpeaker(null);
            setStreamingText('');
            setBackendStatusMessage(`Round ${data.round} ${data.speaker} complete`);
          } else if (data.type === 'judge_start') {
            setStreamingSpeaker(null);
            setCurrentStep(judgeStep);
            setBackendStatusMessage(data.message || `${judgeProvider === 'nvidia' ? 'NVIDIA NIM' : 'Google Gemini'} (JUDGE) analyzing transcript...`);
          } else if (data.type === 'completed' && data.status === 'failed') {
            setStreamingSpeaker(null);
            setStreamingText('');
            setBackendStatusMessage(data.message || data.error || 'Debate execution failed');
            if (eventSource) eventSource.close();
          } else if (data.type === 'cancelled' || (data.type === 'completed' && data.status === 'cancelled')) {
            setStreamingSpeaker(null);
            setStreamingText('');
            setBackendStatusMessage('Debate was cancelled.');
            if (eventSource) eventSource.close();
          } else if (data.type === 'judge_done' || data.type === 'completed') {
            setStreamingSpeaker(null);
            setCurrentStep(completedStep);
            setBackendStatusMessage('Debate Adjudication Complete!');
            if (eventSource) eventSource.close();
          } else if (data.type === 'error' || data.type === 'failed') {
            setStreamingSpeaker(null);
            setStreamingText('');
            setBackendStatusMessage(data.message || data.error || 'Debate execution error');
            if (eventSource) eventSource.close();
          }
        } catch (_) {}
      };

      eventSource.onerror = () => {
        debateApi.getDebate(activeDebateId).then((deb) => {
          if (deb.status === 'completed' || deb.status === 'failed' || deb.status === 'cancelled') {
            setStreamingSpeaker(null);
            setLiveSession(deb);
          }
        }).catch(() => {});
        if (eventSource) eventSource.close();
      };
    } catch (_) {}

    return () => {
      if (eventSource) eventSource.close();
    };
  }, [activeDebateId, judgeStep, completedStep]);


  // Progressive judge criteria evaluation animation (Requirement 14 labels)
  useEffect(() => {
    if (currentStep === judgeStep) {
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
  }, [currentStep, judgeStep]);

  // Web Research Execution Handler
  const handleStartWebResearch = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setValidationError('Please enter a debate proposition before starting web research.');
      return;
    }

    setValidationError(null);
    setIsResearching(true);
    setResearchError(null);

    const initialStages: ResearchStage[] = [
      { id: 'query_gen', name: 'Generating search queries', status: 'in_progress', detail: 'Formulating dialectical query angles...' },
      { id: 'web_search', name: 'Searching sources', status: 'pending', detail: 'Querying live web search provider...' },
      { id: 'collect_articles', name: 'Collecting articles', status: 'pending', detail: 'Awaiting search results...' },
      { id: 'check_relevance', name: 'Checking source relevance', status: 'pending', detail: 'Evaluating source authority and domain reputation...' },
      { id: 'extract_evidence', name: 'Extracting evidence', status: 'pending', detail: 'Extracting factual claims and data points...' },
      { id: 'prepare_evidence', name: 'Preparing debate evidence', status: 'pending', detail: 'Vectorizing and indexing shared evidence pool...' },
    ];
    setResearchStages(initialStages);

    const fallbackPost = async () => {
      try {
        const res = await debateApi.conductResearch(trimmedQuestion, 4);
        if (res.stages && res.stages.length > 0) {
          setResearchStages(res.stages);
        } else {
          setResearchStages(initialStages.map((s) => ({ ...s, status: 'completed' })));
        }

        if (res.sources && res.sources.length > 0) {
          setResearchResponse(res);
          setResearchError(null);
        } else {
          setResearchResponse(null);
          setResearchError(res.message || 'Live research is unavailable or yielded no verified sources. Please check your internet connection or refine your proposition.');
        }
      } catch (err: any) {
        console.error('Web research fallback error:', err);
        setResearchResponse(null);
        setResearchError(err?.response?.data?.detail || err?.message || 'Failed to conduct web research. Live web provider was unreachable.');
        setResearchStages((prev) =>
          prev.map((s) => (s.status === 'in_progress' ? { ...s, status: 'failed', detail: 'Error during execution' } : s))
        );
      } finally {
        setIsResearching(false);
      }
    };

    // Fast-path: Real-time Server-Sent Events (SSE) streaming with live progressive updates
    if (typeof window !== 'undefined' && 'EventSource' in window) {
      try {
        const streamUrl = debateApi.getResearchStreamUrl(trimmedQuestion, 4);
        const es = new EventSource(streamUrl);
        let completed = false;

        const timeoutId = setTimeout(() => {
          if (!completed) {
            es.close();
            fallbackPost();
          }
        }, 35000);

        const stageEvents = ['stage_update', 'query_gen', 'web_search', 'collect_articles', 'check_relevance', 'extract_evidence', 'prepare_evidence'];
        stageEvents.forEach((evtName) => {
          es.addEventListener(evtName, (e: MessageEvent) => {
            try {
              const payload = JSON.parse(e.data);
              const stageId = payload.data?.stage || payload.eventType || payload.stage || (evtName !== 'stage_update' ? evtName : null);
              if (stageId) {
                setResearchStages((prev) =>
                  prev.map((s) => (s.id === stageId ? { ...s, status: payload.status, detail: payload.detail } : s))
                );
              }
            } catch (_) {}
          });
        });

        es.addEventListener('source_found', (e: MessageEvent) => {
          try {
            const payload = JSON.parse(e.data);
            const src = payload.data?.source;
            if (src) {
              setResearchResponse((prev) => {
                const currentSources = prev?.sources || [];
                if (currentSources.some((s) => s.url === src.url)) return prev;
                return {
                  topic: trimmedQuestion,
                  query: trimmedQuestion,
                  sources: [...currentSources, src],
                  evidenceItems: prev?.evidenceItems || [],
                  stages: initialStages,
                  indexedChunks: prev?.indexedChunks || 0,
                  status: 'completed',
                  message: 'Collecting real-time verified sources...'
                };
              });
            }
          } catch (_) {}
        });

        es.addEventListener('complete', (e: MessageEvent) => {
          completed = true;
          clearTimeout(timeoutId);
          es.close();
          try {
            const payload = JSON.parse(e.data);
            const res = payload.data || payload;
            if (res.stages && res.stages.length > 0) {
              setResearchStages(res.stages);
            } else {
              setResearchStages(initialStages.map((s) => ({ ...s, status: 'completed' })));
            }
            if (res.sources && res.sources.length > 0) {
              setResearchResponse(res);
              setResearchError(null);
            } else {
              setResearchResponse(null);
              setResearchError(res.message || 'Live research is unavailable or yielded no verified sources.');
            }
          } catch (err: any) {
            fallbackPost();
          } finally {
            setIsResearching(false);
          }
        });

        es.addEventListener('error', () => {
          clearTimeout(timeoutId);
          es.close();
          if (!completed) {
            fallbackPost();
          }
        });

        return;
      } catch (err) {
        console.warn('SSE connection failed to initialize, falling back to POST:', err);
        fallbackPost();
        return;
      }
    }

    // Direct POST fallback for non-SSE environments
    fallbackPost();
  };

  // Transition from State A to State B
  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setValidationError('Please enter a debate proposition to start the deliberation.');
      return;
    }

    if (!sourceMode) {
      setValidationError('Please choose an evidence source: "Use My Document" or "Research From The Web".');
      return;
    }

    if (sourceMode === 'document') {
      if (!activeDocument) {
        setValidationError('Please select or upload a source document before starting a document-grounded debate, or switch to Web Research mode.');
        return;
      }
      if (activeDocument.status === 'error') {
        setValidationError('Selected document encountered a processing error. Please choose or upload another document.');
        return;
      }
      if (isProcessing) {
        setValidationError('Document is still processing and building knowledge representation. Please wait until ready.');
        return;
      }
    }

    if (sourceMode === 'web') {
      if (!researchResponse || !researchResponse.sources || researchResponse.sources.length === 0) {
        setValidationError('Please conduct web research and verify online sources before starting the debate.');
        return;
      }
    }

    if (![1, 3, 5].includes(rounds)) {
      setValidationError('Please select either 1, 3, or 5 debate rounds.');
      return;
    }

    setIsSubmitting(true);
    setDebateDocument(sourceMode === 'document' ? activeDocument : null);
    setHasStarted(true);
    setCurrentStep(1);
    const localStartMs = Date.now();
    setDebateStartTimeMs(localStartMs);
    setDebateCompletedTimeMs(null);
    setElapsedSeconds(0);
    setTokenCount(0);
    setStreamingSpeaker(null);
    setStreamingText('');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    try {
      const activeJudgeLabel = judgeProvider === 'nvidia' ? 'NVIDIA NIM' : 'Google Gemini';
      setBackendStatusMessage(`Dispatching LangGraph workflow to Gemma, Qwen, and ${activeJudgeLabel}...`);
      const isImg = activeDocument && ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((activeDocument.fileType || '').toLowerCase());
      const effectiveScope = sourceMode === 'web' ? 'web' : (isImg ? 'image' : 'document');

      const response = await debateApi.startDebate({
        topic: trimmedQuestion,
        debaterAModel: 'gemma-4-E4B-Q4_0',
        debaterBModel: 'Qwen2.5-VL-7B-Instruct',
        judgeModel: judgeModel,
        judgeProvider: judgeProvider,
        rounds: rounds,
        evidenceMode: true,
        strictFactChecking: strictFactChecking,
        documentId: sourceMode === 'document' && activeDocument && !activeDocument.id.startsWith('doc-sample') ? activeDocument.id : undefined,
        sourceScope: effectiveScope,
      });
      if (response && response.debateId) {
        if (response.startedAtEpochMs) {
          setDebateStartTimeMs(response.startedAtEpochMs);
        }
        setActiveDebateId(response.debateId);
        sessionStorage.setItem('activeDebateId', response.debateId);
        localStorage.setItem('activeDebateId', response.debateId);
        window.history.replaceState(null, '', `/debate?id=${response.debateId}`);
        setIsLiveBackendConnected(true);
        setBackendStatusMessage(`Debate dispatched (ID: ${response.debateId.slice(0, 8)}). Polling turns...`);
      }
    } catch (err) {
      console.warn('Backend startDebate call failed, operating in simulated preview mode:', err);
      setIsLiveBackendConnected(false);
      setBackendStatusMessage('Backend server offline · Previewing dialectical simulation');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Upload handler for Upload New button
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validation = validateDocumentFile(file);
      if (!validation.valid) {
        setValidationError(validation.error || 'Invalid file format.');
        return;
      }
      setValidationError(null);
      try {
        const newDoc = await uploadDocument(file);
        const newSuggestions = getDocumentSuggestedPropositions(newDoc, null);
        if (newSuggestions.length > 0) {
          setQuestion(newSuggestions[0]);
        }
      } catch (err: any) {
        setValidationError(err?.message || 'Failed to upload and index document.');
      }
    }
  };

  // Return to State A (Setup)
  const handleReturnToSetup = () => {
    setIsDebateEnded(false);
    setHasStarted(false);
    setCurrentStep(0);
    setActiveDebateId(null);
    setLiveSession(null);
    setLiveSynthesis(null);
    setExpandedArgId(null);
    setQuestion('');
    setSourceMode(null);
    setDebateStartTimeMs(null);
    setDebateCompletedTimeMs(null);
    setElapsedSeconds(0);
    setTokenCount(0);
    setResearchResponse(null);
    setResearchStages([]);
    setValidationError(null);
    sessionStorage.removeItem('activeDebateId');
    localStorage.removeItem('activeDebateId');
    window.history.replaceState(null, '', '/debate');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Dedicated confirmation handler for ending debate safely (Part 7 Clean Cancellation Experience)
  const handleConfirmEndDebate = async () => {
    if (!activeDebateId) return;
    setIsCancelling(true);
    setCancellationError(null);
    try {
      await debateApi.cancelDebate(activeDebateId);

      // Stop streaming & clear active telemetry
      setStreamingSpeaker(null);
      setStreamingText('');
      setIsLiveBackendConnected(false);

      // Clean persistent browser state
      sessionStorage.removeItem('activeDebateId');
      localStorage.removeItem('activeDebateId');
      window.history.replaceState(null, '', '/debate');

      // Clear chamber references
      setActiveDebateId(null);
      setLiveSession(null);
      setLiveSynthesis(null);
      setDebateStartTimeMs(null);
      setDebateCompletedTimeMs(null);
      setElapsedSeconds(0);
      setShowEndDebateModal(false);

      // Transition to dedicated "Debate Ended" screen
      setHasStarted(false);
      setIsDebateEnded(true);
    } catch (err: any) {
      console.error('Error cancelling debate:', err);
      setCancellationError(err?.response?.data?.detail || err?.message || 'Failed to stop debate. Please try again.');
    } finally {
      setIsCancelling(false);
    }
  };

  // Reset and restart debate
  const handleRestartDebate = () => {
    setCurrentStep(1);
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

  // Dynamic document-grounded suggested propositions
  const suggestedPropositions = useMemo(() => {
    return getDocumentSuggestedPropositions(activeDocument, activeKnowledge);
  }, [activeDocument, activeKnowledge]);

  // Derived single-selection states for Document Mode suggestions
  const selectedDocSuggestion = useMemo(() => {
    const trimmed = question.trim();
    if (!trimmed) return null;
    return suggestedPropositions.find((sq) => sq.trim() === trimmed) || null;
  }, [question, suggestedPropositions]);
  const hasSelectedDocSuggestion = selectedDocSuggestion !== null;

  // Derived single-selection states for Web Mode example suggestions
  const selectedWebSuggestion = useMemo(() => {
    const trimmed = question.trim();
    if (!trimmed) return null;
    return EXAMPLE_PROPOSITIONS.find((ex) => ex.trim() === trimmed) || null;
  }, [question]);
  const hasSelectedWebSuggestion = selectedWebSuggestion !== null;

  const prevDocIdRef = useRef<string | null>(activeDocument?.id || null);

  const handleSelectDocument = (docId: string) => {
    selectDocument(docId);
    prevDocIdRef.current = docId;
    // Reset proposition selection when switching documents so all new suggestions are selectable
    setQuestion('');
    if (validationError) setValidationError(null);
  };

  // Synchronize document switching with suggested propositions
  useEffect(() => {
    if (sourceMode !== 'document') return;
    if (!activeDocument) return;

    if (prevDocIdRef.current && prevDocIdRef.current !== activeDocument.id) {
      prevDocIdRef.current = activeDocument.id;
      // Changing document clears proposition so new document's suggestions start fresh and selectable
      setQuestion('');
      if (validationError) setValidationError(null);
    } else {
      prevDocIdRef.current = activeDocument.id;
    }
  }, [activeDocument?.id, sourceMode]);

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
      {/* STATE A — DEBATE SETUP (Redesigned Modern AI Workspace) */}
      {/* ========================================================================= */}
      {isDebateEnded ? (
        <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6 space-y-6 animate-fadeIn max-w-lg mx-auto">
          <div className="w-20 h-20 rounded-3xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-500 dark:text-slate-400 shadow-inner">
            <XCircle className="w-10 h-10 text-rose-500" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-black font-mono text-slate-900 dark:text-white tracking-tight">
              Debate Ended
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 font-normal">
              Your debate has been stopped.
            </p>
          </div>

          <button
            type="button"
            onClick={handleReturnToSetup}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-bold text-sm shadow-lg shadow-indigo-600/25 transition-all cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Start New Debate</span>
          </button>
        </div>
      ) : !hasStarted ? (
        <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
          {/* Hidden File Input for PDF & Multimodal Image Upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.docx,.txt"
            className="hidden"
            onChange={handleFileUpload}
          />

          {/* PART 1: TOPIC-FIRST HERO HEADER */}
          <div className="text-center space-y-3 pt-2 pb-1">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase tracking-wider bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20">
              <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
              <span>Multi-Agent Dialectical Reasoning</span>
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 dark:text-white tracking-tight">
              What should we debate today?
            </h1>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 max-w-2xl mx-auto font-normal leading-relaxed">
              Bring a question. Let two AI agents challenge each other. Let an independent Judge decide.
            </p>
          </div>

          {/* SECTION 1: EVIDENCE SOURCE SELECTION (FIRST) */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-lg sm:text-xl font-black font-mono text-slate-900 dark:text-white tracking-tight">
                  Where should your debate evidence come from?
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-0.5">
                  Choose how your AI agents should gather evidence to support their arguments.
                </p>
              </div>

              {sourceMode !== null && (
                <button
                  type="button"
                  onClick={() => setSourceMode(null)}
                  className="self-start sm:self-center text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50/60 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors cursor-pointer shadow-2xs"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Change Source</span>
                </button>
              )}
            </div>

            {/* Exactly Two Source Cards (Mutually Exclusive) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* OPTION 1: USE MY DOCUMENT */}
              <div
                onClick={() => {
                  setSourceMode('document');
                  if (EXAMPLE_PROPOSITIONS.some((ex) => ex.trim() === question.trim())) {
                    setQuestion('');
                  }
                }}
                className={`p-5 rounded-3xl border-2 transition-all cursor-pointer relative space-y-3 ${
                  sourceMode === 'document'
                    ? 'border-indigo-600 dark:border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/25 ring-2 ring-indigo-500/20 shadow-lg'
                    : 'border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#0E1424] hover:border-indigo-300 dark:hover:border-indigo-500/40'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-base font-bold font-mono text-slate-900 dark:text-white tracking-tight">
                        USE MY DOCUMENT
                      </h4>
                      <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 font-semibold block">
                        PDF, Research Paper or Image
                      </span>
                    </div>
                  </div>
                  {sourceMode === 'document' && (
                    <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  Debate using an existing PDF, research paper or image.
                </p>
              </div>

              {/* OPTION 2: RESEARCH FROM THE WEB */}
              <div
                onClick={() => {
                  setSourceMode('web');
                  if (suggestedPropositions.some((sq) => sq.trim() === question.trim())) {
                    setQuestion('');
                  }
                }}
                className={`p-5 rounded-3xl border-2 transition-all cursor-pointer relative space-y-3 ${
                  sourceMode === 'web'
                    ? 'border-cyan-600 dark:border-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/25 ring-2 ring-cyan-500/20 shadow-lg'
                    : 'border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#0E1424] hover:border-cyan-300 dark:hover:border-cyan-500/40'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-600 dark:text-cyan-400 shrink-0">
                      <Globe className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-base font-bold font-mono text-slate-900 dark:text-white tracking-tight">
                        RESEARCH FROM THE WEB
                      </h4>
                      <span className="text-[11px] font-mono text-cyan-600 dark:text-cyan-400 font-semibold block">
                        Live Online Sources & Articles
                      </span>
                    </div>
                  </div>
                  {sourceMode === 'web' && (
                    <div className="w-6 h-6 rounded-full bg-cyan-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  Find relevant online articles, research papers and sources for your topic.
                </p>
              </div>
            </div>
          </div>

          {/* CONDITIONAL SECTIONS: REVEALED ONLY AFTER EVIDENCE SOURCE IS CHOSEN */}
          {sourceMode !== null ? (
            <div className="space-y-6 animate-fadeIn">
              {sourceMode === 'document' ? (
                <>
                  {/* ========================================================================= */}
                  {/* DOCUMENT MODE: FIRST — Document Grounding Source                          */}
                  {/* ========================================================================= */}
                  <div className="p-5 sm:p-6 rounded-3xl border border-indigo-200 dark:border-indigo-500/30 bg-white dark:bg-[#0E1424] space-y-4 shadow-sm animate-fadeIn">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
                      <div>
                        <h4 className="text-sm font-mono font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <FileText className="w-4 h-4 text-indigo-500" />
                          <span>Document Grounding Source</span>
                        </h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          Select an existing document from your repository or upload a new research asset.
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-bold shadow-xs transition-colors cursor-pointer flex items-center gap-1.5"
                        >
                          <span>Upload New</span>
                        </button>
                      </div>
                    </div>

                    {/* Available Documents List */}
                    <div className="space-y-2">
                      <span className="text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 block">
                        Available Documents & Images:
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {documents.map((doc) => {
                          const isSelected = activeDocument?.id === doc.id;
                          const isImg = ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((doc.fileType || '').toLowerCase());
                          return (
                            <div
                              key={doc.id}
                              onClick={() => handleSelectDocument(doc.id)}
                              className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                                isSelected
                                  ? 'border-indigo-500 bg-indigo-50/80 dark:bg-indigo-950/40 ring-1 ring-indigo-500/40 shadow-xs'
                                  : 'border-slate-200/80 dark:border-white/[0.08] bg-slate-50/50 dark:bg-[#0A0F1C] hover:border-indigo-300 dark:hover:border-indigo-500/30 hover:bg-white dark:hover:bg-[#0c1224]'
                              }`}
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500 shrink-0">
                                  {isImg ? <FileImage className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                                </div>
                                <div className="min-w-0">
                                  <h5 className="text-xs font-mono font-bold text-slate-900 dark:text-white truncate">
                                    {doc.name}
                                  </h5>
                                  <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mt-0.5">
                                    <span>{doc.pageCount} {doc.pageCount === 1 ? 'Page' : 'Pages'}</span>
                                    <span>•</span>
                                    <span className="uppercase">{doc.fileType}</span>
                                    <span>•</span>
                                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Ready</span>
                                  </div>
                                </div>
                              </div>

                              <div className="shrink-0">
                                {isSelected ? (
                                  <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center">
                                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                                  </div>
                                ) : (
                                  <div className="w-5 h-5 rounded-full border border-slate-300 dark:border-slate-700" />
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Selected Document Metadata Box */}
                    {activeDocument ? (
                      <div className="p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-500/30 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5 min-w-0">
                            {['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((activeDocument.fileType || '').toLowerCase()) ? (
                              <FileImage className="w-5 h-5 text-indigo-500 shrink-0" />
                            ) : (
                              <FileText className="w-5 h-5 text-indigo-500 shrink-0" />
                            )}
                            <div className="min-w-0">
                              <span className="text-xs font-mono font-bold text-slate-900 dark:text-white truncate block">
                                {activeDocument.name}
                              </span>
                              <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">
                                <span>{activeDocument.pageCount} Pages</span>
                                <span>•</span>
                                <span>{activeKnowledge?.sections?.length || activeDocument.evidencePointsCount || 13} Extracted Sections</span>
                                <span>•</span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Knowledge Graph Ready</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => setIsKnowledgeModalOpen(true)}
                              className="px-3 py-1.5 rounded-xl border border-indigo-300 dark:border-indigo-500/40 bg-white dark:bg-[#070a16] text-indigo-700 dark:text-indigo-300 text-xs font-mono font-bold hover:bg-indigo-50 dark:hover:bg-indigo-900/40 transition-colors cursor-pointer flex items-center gap-1.5 shadow-2xs"
                            >
                              <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                              <span>View Knowledge</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 rounded-2xl border border-dashed border-indigo-300 dark:border-indigo-500/40 text-center space-y-2">
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                          No document selected. Please choose a document from the list above or upload a new file.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* ========================================================================= */}
                  {/* DOCUMENT MODE: SECOND — Debate Proposition / Question                     */}
                  {/* ========================================================================= */}
                  <div className="rounded-3xl border-2 border-indigo-500/40 dark:border-indigo-500/50 bg-white dark:bg-[#0E1424] p-5 sm:p-7 shadow-xl space-y-4 backdrop-blur-xl relative overflow-hidden">
                    {/* Ambient Accent Glow */}
                    <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/[0.05] dark:bg-indigo-500/[0.08] rounded-full blur-3xl pointer-events-none" />

                    <div className="flex items-center justify-between relative z-10">
                      <label
                        htmlFor="debate-proposition-input-doc"
                        className="text-xs sm:text-sm font-mono font-bold tracking-wider uppercase text-slate-900 dark:text-white flex items-center gap-2"
                      >
                        <span>Debate Proposition / Question</span>
                      </label>
                      <span
                        className={`text-xs font-mono font-semibold ${
                          question.length > 480
                            ? 'text-rose-500 font-bold'
                            : question.length > 400
                            ? 'text-amber-500'
                            : 'text-slate-400 dark:text-slate-500'
                        }`}
                      >
                        {question.length} / 500 characters
                      </span>
                    </div>

                    {/* Proposition Input Field */}
                    <div className="relative z-10 space-y-2">
                      <textarea
                        id="debate-proposition-input-doc"
                        rows={3}
                        maxLength={500}
                        value={question}
                        onChange={(e) => {
                          setQuestion(e.target.value);
                          if (validationError) setValidationError(null);
                        }}
                        placeholder="Enter your debate proposition (or choose a suggested proposition below)..."
                        className="w-full rounded-2xl border border-slate-200 dark:border-white/[0.12] bg-slate-50 dark:bg-[#0A0F1C] p-4 text-base sm:text-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 resize-none transition-all shadow-inner leading-relaxed"
                        required
                      />

                      {/* Validation Error Banner */}
                      {validationError && (
                        <div className="flex items-center gap-2 p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs font-mono animate-fadeIn">
                          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                          <span>{validationError}</span>
                        </div>
                      )}
                    </div>

                    {/* Suggested propositions from document (Directly underneath textarea) */}
                    <div className="relative z-10 pt-3 border-t border-slate-100 dark:border-white/[0.06] space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-semibold text-slate-500 dark:text-slate-400">
                          Suggested propositions from document:
                        </span>
                        {hasSelectedDocSuggestion && (
                          <button
                            type="button"
                            onClick={() => setQuestion('')}
                            className="text-[11px] font-mono font-semibold text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1 cursor-pointer"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Clear selection</span>
                          </button>
                        )}
                      </div>
                      {suggestedPropositions.length > 0 ? (
                        <div className="space-y-2">
                          {suggestedPropositions.map((sq, idx) => {
                            const isSelected = selectedDocSuggestion === sq || question.trim() === sq.trim();
                            const isDisabled = hasSelectedDocSuggestion && !isSelected;

                            return (
                              <button
                                key={idx}
                                type="button"
                                disabled={isDisabled}
                                onClick={() => {
                                  if (isDisabled) return;
                                  if (isSelected) {
                                    setQuestion('');
                                  } else {
                                    setQuestion(sq.slice(0, 500));
                                  }
                                  if (validationError) setValidationError(null);
                                }}
                                className={`w-full text-left p-3 sm:p-3.5 rounded-2xl border text-xs sm:text-[13px] transition-all flex items-center justify-between gap-3 ${
                                  isSelected
                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/20 text-indigo-950 dark:text-indigo-100 ring-2 ring-indigo-500/30 shadow-xs cursor-default'
                                    : isDisabled
                                    ? 'opacity-40 cursor-not-allowed pointer-events-none border-slate-200/50 dark:border-white/[0.04] bg-slate-100/50 dark:bg-[#070b14]/50 text-slate-400 dark:text-slate-600'
                                    : 'border-slate-200/80 dark:border-white/[0.06] bg-slate-50/60 dark:bg-[#0A0F1C] hover:border-indigo-400 dark:hover:border-indigo-500/50 hover:bg-white dark:hover:bg-[#0E1424] text-slate-800 dark:text-slate-200 cursor-pointer group'
                                }`}
                              >
                                <span className="leading-relaxed font-sans">{sq}</span>
                                {isSelected ? (
                                  <span className="inline-flex items-center gap-1 shrink-0 px-2 py-0.5 rounded-full bg-indigo-600 text-white text-[11px] font-mono font-medium shadow-xs">
                                    <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                                    <span>Selected</span>
                                  </span>
                                ) : isDisabled ? null : (
                                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#0A0F1C] border border-dashed border-slate-200 dark:border-white/10 text-xs font-mono text-slate-500 dark:text-slate-400">
                          No suggested propositions available for this document yet.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {/* ========================================================================= */}
                  {/* WEB RESEARCH MODE: FIRST — Debate Proposition / Question                  */}
                  {/* ========================================================================= */}
                  <div className="rounded-3xl border-2 border-cyan-500/40 dark:border-cyan-500/50 bg-white dark:bg-[#0E1424] p-5 sm:p-7 shadow-xl space-y-4 backdrop-blur-xl relative overflow-hidden">
                    {/* Ambient Accent Glow */}
                    <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/[0.05] dark:bg-cyan-500/[0.08] rounded-full blur-3xl pointer-events-none" />

                    <div className="flex items-center justify-between relative z-10">
                      <label
                        htmlFor="debate-proposition-input-web"
                        className="text-xs sm:text-sm font-mono font-bold tracking-wider uppercase text-slate-900 dark:text-white flex items-center gap-2"
                      >
                        <span>Debate Proposition / Question</span>
                      </label>
                      <span
                        className={`text-xs font-mono font-semibold ${
                          question.length > 480
                            ? 'text-rose-500 font-bold'
                            : question.length > 400
                            ? 'text-amber-500'
                            : 'text-slate-400 dark:text-slate-500'
                        }`}
                      >
                        {question.length} / 500 characters
                      </span>
                    </div>

                    {/* Proposition Input Field */}
                    <div className="relative z-10 space-y-2">
                      <textarea
                        id="debate-proposition-input-web"
                        rows={3}
                        maxLength={500}
                        value={question}
                        onChange={(e) => {
                          setQuestion(e.target.value);
                          if (validationError) setValidationError(null);
                        }}
                        placeholder="Enter your debate proposition to research live across online sources..."
                        className="w-full rounded-2xl border border-slate-200 dark:border-white/[0.12] bg-slate-50 dark:bg-[#0A0F1C] p-4 text-base sm:text-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 resize-none transition-all shadow-inner leading-relaxed"
                        required
                      />

                      {/* Validation Error Banner */}
                      {validationError && (
                        <div className="flex items-center gap-2 p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs font-mono animate-fadeIn">
                          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                          <span>{validationError}</span>
                        </div>
                      )}
                    </div>

                    {/* 6 Illustrative Example Cards (WEB RESEARCH MODE ONLY) */}
                    <div className="relative z-10 pt-3 border-t border-slate-100 dark:border-white/[0.06] space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-semibold text-slate-500 dark:text-slate-400">
                          Or click an illustrative example to explore:
                        </span>
                        {hasSelectedWebSuggestion && (
                          <button
                            type="button"
                            onClick={() => setQuestion('')}
                            className="text-[11px] font-mono font-semibold text-cyan-600 dark:text-cyan-400 hover:underline inline-flex items-center gap-1 cursor-pointer"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Clear selection</span>
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {EXAMPLE_PROPOSITIONS.map((ex, idx) => {
                          const isSelected = selectedWebSuggestion === ex || question.trim() === ex.trim();
                          const isDisabled = hasSelectedWebSuggestion && !isSelected;

                          return (
                            <button
                              key={idx}
                              type="button"
                              disabled={isDisabled}
                              onClick={() => {
                                if (isDisabled) return;
                                if (isSelected) {
                                  setQuestion('');
                                } else {
                                  setQuestion(ex);
                                }
                                if (validationError) setValidationError(null);
                              }}
                              className={`text-left p-3 rounded-2xl border text-xs transition-all flex items-center justify-between gap-2.5 ${
                                isSelected
                                  ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-500/20 text-cyan-950 dark:text-cyan-100 ring-2 ring-cyan-500/30 shadow-xs cursor-default'
                                  : isDisabled
                                  ? 'opacity-40 cursor-not-allowed pointer-events-none border-slate-200/50 dark:border-white/[0.04] bg-slate-100/50 dark:bg-[#070b14]/50 text-slate-400 dark:text-slate-600'
                                  : 'border-slate-200/80 dark:border-white/[0.06] bg-slate-50/60 dark:bg-[#0A0F1C] hover:border-cyan-400 dark:hover:border-cyan-500/50 hover:bg-white dark:hover:bg-[#0E1424] text-slate-800 dark:text-slate-200 cursor-pointer group'
                              }`}
                            >
                              <span className="leading-snug line-clamp-2">{ex}</span>
                              {isSelected ? (
                                <Check className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0 stroke-[2.5]" />
                              ) : isDisabled ? null : (
                                <ArrowRight className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* ========================================================================= */}
                  {/* WEB RESEARCH MODE: SECOND — Web Research Engine                           */}
                  {/* ========================================================================= */}
                  <div className="p-5 sm:p-6 rounded-3xl border border-cyan-200 dark:border-cyan-500/30 bg-white dark:bg-[#0E1424] space-y-4 shadow-sm animate-fadeIn">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
                  <div>
                    <h4 className="text-sm font-mono font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <Globe className="w-4 h-4 text-cyan-500" />
                      <span>Web Research Engine</span>
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Query live web sources, extract factual claims, and build a shared research evidence pool.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleStartWebResearch}
                    disabled={isResearching || !question.trim()}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono font-bold shadow-md shadow-cyan-600/20 transition-all cursor-pointer flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                  >
                    {isResearching ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Researching...</span>
                      </>
                    ) : (
                      <>
                        <Globe className="w-3.5 h-3.5" />
                        <span>Conduct Web Research</span>
                      </>
                    )}
                  </button>
                </div>

                {!question.trim() && (
                  <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-xs font-mono flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-amber-500" />
                    <span>Please enter your debate proposition in the input box above to conduct targeted web research.</span>
                  </div>
                )}

                {/* 6 Research Stages Progress */}
                {isResearching && (
                  <div className="p-4 rounded-2xl bg-slate-50/70 dark:bg-[#070a16] border border-cyan-300 dark:border-cyan-500/40 space-y-3 animate-fadeIn">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-bold text-cyan-700 dark:text-cyan-400 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>CONDUCTING WEB RESEARCH ACROSS ACADEMIC & WEB INDEXES...</span>
                      </span>
                    </div>

                    <div className="space-y-2 text-xs font-mono">
                      {researchStages.map((stage) => (
                        <div
                          key={stage.id}
                          className="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-[#0a0e1c] border border-slate-200/60 dark:border-white/5"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            {stage.status === 'completed' ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                            ) : stage.status === 'in_progress' ? (
                              <Loader2 className="w-4 h-4 text-cyan-500 animate-spin shrink-0" />
                            ) : (
                              <div className="w-4 h-4 rounded-full border border-slate-300 dark:border-slate-700 shrink-0" />
                            )}
                            <span className={`truncate ${stage.status === 'in_progress' ? 'font-bold text-cyan-700 dark:text-cyan-300' : 'text-slate-600 dark:text-slate-400'}`}>
                              {stage.name}
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider shrink-0">
                            {stage.status.replace('_', ' ')}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Completed Research Sources Summary */}
                {researchResponse && !isResearching && (
                  <div className="p-4 rounded-2xl bg-slate-50/80 dark:bg-[#070a16] border border-cyan-300 dark:border-cyan-500/40 space-y-3 animate-fadeIn">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>{researchResponse.sources.length} Verified Sources Ready</span>
                        </span>
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          <span>Evidence Pool Active</span>
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={handleStartWebResearch}
                        className="text-[11px] font-mono text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Re-run Research</span>
                      </button>
                    </div>

                    {/* Sources preview list */}
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {researchResponse.sources.map((s, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded-xl bg-white dark:bg-[#0a0e1c] text-xs font-mono flex items-center justify-between gap-3 border border-slate-200/60 dark:border-white/5"
                        >
                          <div className="min-w-0">
                            <span className="truncate text-slate-800 dark:text-slate-200 font-medium block">
                              {s.title}
                            </span>
                            <span className="text-[10px] text-slate-400 block truncate">
                              {s.url}
                            </span>
                          </div>
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-500 hover:text-cyan-400 shrink-0 p-1 rounded-lg hover:bg-cyan-500/10 transition-colors"
                            title="Open external source"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      ))}
                    </div>

                    {/* Expandable Claims Drawer */}
                    {researchResponse.evidenceItems && researchResponse.evidenceItems.length > 0 && (
                      <div className="pt-2 border-t border-slate-200/60 dark:border-white/[0.06]">
                        <button
                          type="button"
                          onClick={() => setIsEvidenceDrawerOpen(!isEvidenceDrawerOpen)}
                          className="text-xs font-mono text-cyan-600 dark:text-cyan-400 hover:underline flex items-center justify-between w-full cursor-pointer py-1"
                        >
                          <span>Inspect {researchResponse.evidenceItems.length} Extracted Factual Claims</span>
                          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isEvidenceDrawerOpen ? 'rotate-180' : ''}`} />
                        </button>
                        {isEvidenceDrawerOpen && (
                          <div className="mt-2 space-y-2 max-h-48 overflow-y-auto pr-1 animate-fadeIn">
                            {researchResponse.evidenceItems.map((ev, i) => (
                              <div
                                key={ev.id || i}
                                className="p-2.5 rounded-xl bg-white dark:bg-[#060a16] text-[11px] font-mono space-y-1 border border-slate-200/50 dark:border-white/5"
                              >
                                <span className="text-slate-500 dark:text-slate-400 block font-semibold truncate">
                                  Claim #{i + 1} ({ev.source})
                                </span>
                                <p className="text-slate-700 dark:text-slate-300 italic">
                                  "{ev.claim}"
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Research Error Banner */}
                {researchError && !isResearching && (
                  <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs font-mono space-y-2.5">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                      <span className="font-bold">Web Research Failed</span>
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      {researchError}
                    </p>
                    <button
                      type="button"
                      onClick={handleStartWebResearch}
                      className="px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-bold cursor-pointer"
                    >
                      Retry Research
                    </button>
                  </div>
                )}
              </div>
                </>
              )}

              {/* SECTIONS 4 & 5: DEBATE PROTOCOL & ENGINE SETTINGS + ACTION BAR */}
          <form onSubmit={handleStart} className="space-y-6">
            {/* Debate Protocol & Engine Settings */}
            <div className="rounded-3xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#0E1424] p-5 sm:p-6 shadow-sm dark:shadow-xl space-y-6 backdrop-blur-xl">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/[0.06]">
                <div>
                  <h3 className="text-sm sm:text-base font-mono font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-indigo-500" />
                    <span>Debate Protocol & Engine Settings</span>
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                    Configure deliberation rounds, independent judge, and local multi-agent parameters.
                  </p>
                </div>
                <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30">
                  {rounds} Rounds · {rounds * 2} Speeches
                </span>
              </div>

              {/* A. Debate Rounds (Exactly 3 Selectable Options: 1, 3, or 5) */}
              <div className="rounded-2xl p-4 border border-slate-200/80 dark:border-white/[0.06] bg-slate-50/70 dark:bg-[#0A0F1C] space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-slate-200 block">
                      Deliberation Rounds
                    </span>
                    <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
                      {rounds} Round{rounds > 1 ? 's' : ''} Selected · {rounds * 2} Alternating Speeches ({rounds} Affirmative, {rounds} Opposition)
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                    Each round = 1 PRO speech + 1 CON speech
                  </span>
                </div>

                {/* Segmented Button Selector: Strictly 1, 3, or 5 */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                  {[
                    {
                      count: 1,
                      label: '1 Round',
                      speeches: 2,
                      speechDesc: '2 Speeches (1 PRO, 1 CON)',
                      description: 'Rapid dialectical test',
                      badge: null,
                    },
                    {
                      count: 3,
                      label: '3 Rounds',
                      speeches: 6,
                      speechDesc: '6 Speeches (3 PRO, 3 CON)',
                      description: 'Deep clash & examination',
                      badge: 'Recommended',
                    },
                    {
                      count: 5,
                      label: '5 Rounds',
                      speeches: 10,
                      speechDesc: '10 Speeches (5 PRO, 5 CON)',
                      description: 'Exhaustive thesis stress-test',
                      badge: 'Comprehensive',
                    },
                  ].map((option) => {
                    const isSelected = rounds === option.count;
                    return (
                      <button
                        key={option.count}
                        type="button"
                        onClick={() => setRounds(option.count)}
                        className={`p-3 rounded-2xl border text-left transition-all cursor-pointer relative ${
                          isSelected
                            ? 'border-indigo-600 dark:border-indigo-500 bg-indigo-50/80 dark:bg-indigo-600/20 text-slate-900 dark:text-white shadow-md shadow-indigo-600/10 ring-2 ring-indigo-600/30'
                            : 'border-slate-200 dark:border-white/[0.06] bg-white dark:bg-[#0E1424] hover:border-slate-300 dark:hover:border-white/10 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {option.badge && (
                          <span className="absolute top-2.5 right-2.5 text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-500/30">
                            {option.badge}
                          </span>
                        )}
                        <div className="space-y-1">
                          <span className={`text-sm font-mono font-bold block ${isSelected ? 'text-indigo-600 dark:text-indigo-300' : 'text-slate-800 dark:text-slate-200'}`}>
                            {option.label}
                          </span>
                          <span className="text-xs font-medium text-slate-600 dark:text-slate-300 block">
                            {option.speechDesc}
                          </span>
                          <span className="text-[11px] text-slate-500 dark:text-slate-400 block">
                            {option.description}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* B. Agents Lineup Showcase (Local CPU Models) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* PRO Agent Showcase */}
                <div className="rounded-2xl p-3.5 border border-sky-500/20 bg-sky-50/50 dark:bg-sky-950/[0.12] space-y-2">
                  <div className="flex items-center justify-between pb-1.5 border-b border-sky-500/20">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-600 dark:text-sky-400">
                        <Bot className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-mono font-bold uppercase text-slate-900 dark:text-white">PRO</span>
                          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-700 dark:text-sky-300">Affirmative Case</span>
                        </div>
                        <span className="text-xs font-mono text-sky-600 dark:text-sky-400 font-semibold block">Gemma 4 E4B (Q4_0)</span>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono text-slate-500 dark:text-slate-400 bg-white dark:bg-black/40 px-2 py-0.5 rounded border border-slate-200 dark:border-white/[0.06]">
                      Port 8081 · Local
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed font-mono">
                    Constructs affirmative thesis grounded in citations, facts, and verified empirical evidence.
                  </p>
                </div>

                {/* CON Agent Showcase */}
                <div className="rounded-2xl p-3.5 border border-violet-500/20 bg-violet-50/50 dark:bg-violet-950/[0.12] space-y-2">
                  <div className="flex items-center justify-between pb-1.5 border-b border-violet-500/20">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-600 dark:text-violet-400">
                        <Bot className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-mono font-bold uppercase text-slate-900 dark:text-white">CON</span>
                          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-violet-500/20 text-violet-700 dark:text-violet-300">Opposition Rebuttal</span>
                        </div>
                        <span className="text-xs font-mono text-violet-600 dark:text-violet-400 font-semibold block">Qwen2.5-VL-7B (Q4_K_M)</span>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono text-slate-500 dark:text-slate-400 bg-white dark:bg-black/40 px-2 py-0.5 rounded border border-slate-200 dark:border-white/[0.06]">
                      Port 8083 · Local
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed font-mono">
                    Direct counter-examination exposing unverified claims, structural limits, and logical fallacies.
                  </p>
                </div>
              </div>

              {/* Independent AI Judge Selection */}
              <div className="rounded-2xl p-4 border border-slate-200/80 dark:border-white/[0.06] bg-slate-50/70 dark:bg-[#0A0F1C] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Gavel className="w-4 h-4 text-indigo-500" />
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-slate-200">
                      Independent AI Judge Provider
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                    5-Criterion Rubric (100 pts max)
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => {
                      setJudgeProvider('nvidia');
                      setJudgeModel('nvidia/nemotron-3.5-super-vl-120b-a12b');
                    }}
                    className={`p-3 rounded-2xl border text-left transition-all cursor-pointer flex items-center justify-between ${
                      judgeProvider === 'nvidia'
                        ? 'bg-emerald-50 dark:bg-emerald-600/20 border-emerald-500 text-emerald-900 dark:text-emerald-200 shadow-sm ring-1 ring-emerald-500/30'
                        : 'bg-white dark:bg-[#0E1424] border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${judgeProvider === 'nvidia' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                        <span className="text-xs font-mono font-bold">NVIDIA Nemotron (Primary)</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 block pl-4">nemotron-3.5-super-vl-120b</span>
                    </div>
                    {judgeProvider === 'nvidia' && <Check className="w-4 h-4 text-emerald-500 shrink-0" />}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setJudgeProvider('gemini');
                      setJudgeModel('gemini-3.5-flash');
                    }}
                    className={`p-3 rounded-2xl border text-left transition-all cursor-pointer flex items-center justify-between ${
                      judgeProvider === 'gemini'
                        ? 'bg-indigo-50 dark:bg-indigo-600/20 border-indigo-500 text-indigo-900 dark:text-indigo-200 shadow-sm ring-1 ring-indigo-500/30'
                        : 'bg-white dark:bg-[#0E1424] border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${judgeProvider === 'gemini' ? 'bg-indigo-500 animate-pulse' : 'bg-slate-400'}`} />
                        <span className="text-xs font-mono font-bold">Google Gemini Flash</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 block pl-4">gemini-3.5-flash</span>
                    </div>
                    {judgeProvider === 'gemini' && <Check className="w-4 h-4 text-indigo-500 shrink-0" />}
                  </button>
                </div>

                {/* Collapsible Advanced Settings (Examination Style & Grounding Strictness) */}
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                    className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer py-1 transition-colors"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>{showAdvancedSettings ? 'Hide Advanced Settings' : 'Advanced Settings (Debate Style & Strictness)'}</span>
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showAdvancedSettings ? 'rotate-180' : ''}`} />
                  </button>

                  {showAdvancedSettings && (
                    <div className="mt-2.5 p-3.5 rounded-2xl bg-white dark:bg-[#0E1424] border border-slate-200 dark:border-white/[0.08] space-y-3 animate-fadeIn">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1">
                            Examination Style
                          </label>
                          <select
                            value={selectedMode}
                            onChange={(e) => setSelectedMode(e.target.value as DebateMode)}
                            className="w-full h-8.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-[#0A0F1C] px-2.5 text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500"
                          >
                            <option value="claim-challenge">1. Claim Challenge (Assertive clash)</option>
                            <option value="critical-review">2. Critical Review (Methodological limits)</option>
                            <option value="balanced-analysis">3. Balanced Analysis (Multi-faceted)</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1">
                            Adjudication Model Identifier
                          </label>
                          <select
                            value={judgeModel}
                            onChange={(e) => setJudgeModel(e.target.value)}
                            className="w-full h-8.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-[#0A0F1C] px-2.5 text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500"
                          >
                            {judgeProvider === 'nvidia' ? (
                              <>
                                <option value="nvidia/nemotron-3.5-super-vl-120b-a12b">
                                  nvidia/nemotron-3.5-super-vl-120b-a12b (Official NIM Reasoning Judge)
                                </option>
                                <option value="nvidia/llama-3.1-nemotron-70b-instruct">
                                  nvidia/llama-3.1-nemotron-70b-instruct
                                </option>
                                <option value="meta/llama-3.3-70b-instruct">
                                  meta/llama-3.3-70b-instruct (via NVIDIA NIM)
                                </option>
                              </>
                            ) : (
                              <>
                                <option value="gemini-3.5-flash">Google Gemini 3.5 Flash (Official Remote Judge)</option>
                                <option value="gemini-3.8-flash">Google Gemini 3.8 Flash</option>
                              </>
                            )}
                          </select>
                        </div>
                      </div>

                      {/* Fact-Checking Strictness Toggle */}
                      <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/[0.06] text-xs font-mono">
                        <span className="text-slate-600 dark:text-slate-300">Enforce Strict Grounding (Zero Fabrication)</span>
                        <button
                          type="button"
                          onClick={() => setStrictFactChecking(!strictFactChecking)}
                          className={`w-10 h-5 flex items-center rounded-full p-1 cursor-pointer transition-colors ${
                            strictFactChecking ? 'bg-indigo-600 justify-end' : 'bg-slate-300 dark:bg-slate-700 justify-start'
                          }`}
                        >
                          <span className="w-3.5 h-3.5 rounded-full bg-white shadow-sm" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ACTION BAR: SINGLE PROMINENT START BUTTON */}
            <div className="p-4 sm:p-5 rounded-3xl border border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#0A0F1C] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-0.5 text-xs font-mono">
                <span className="text-slate-500 dark:text-slate-400 block font-semibold uppercase tracking-wider">
                  DELIBERATION READY
                </span>
                <span className="font-bold text-slate-800 dark:text-slate-200 block">
                  {!sourceMode
                    ? 'No Evidence Source Selected'
                    : sourceMode === 'document'
                    ? (activeDocument ? activeDocument.name : 'No Document Selected')
                    : `${researchResponse?.sources?.length || 0} Web Sources Indexed`} · {rounds} Round{rounds > 1 ? 's' : ''} ({rounds * 2} Speeches) · {judgeProvider === 'nvidia' ? 'NVIDIA NIM' : 'Google Gemini'}
                </span>
              </div>

              <Button
                type="submit"
                size="lg"
                disabled={
                  isSubmitting ||
                  isProcessing ||
                  !question.trim() ||
                  !sourceMode ||
                  (sourceMode === 'document' && !activeDocument) ||
                  (sourceMode === 'web' && (!researchResponse || !researchResponse.sources || researchResponse.sources.length === 0 || isResearching))
                }
                className="w-full sm:w-auto px-8 py-3.5 font-bold shadow-lg shadow-indigo-600/25 bg-gradient-to-r from-indigo-600 via-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white gap-2 text-sm uppercase tracking-wider font-mono cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Initializing Chamber...</span>
                  </>
                ) : !question.trim() ? (
                  <span>Enter Proposition to Start</span>
                ) : !sourceMode ? (
                  <span>Select Evidence Source to Start</span>
                ) : sourceMode === 'document' && !activeDocument ? (
                  <span>Select Document to Start</span>
                ) : sourceMode === 'web' && isResearching ? (
                  <span>Researching Web...</span>
                ) : sourceMode === 'web' && (!researchResponse || !researchResponse.sources || researchResponse.sources.length === 0) ? (
                  <span>Conduct Web Research First</span>
                ) : (
                  <>
                    <span>Start AI Debate</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </div>

          </form>
            </div>
          ) : (
            <div className="p-6 rounded-3xl border border-dashed border-slate-300 dark:border-white/10 bg-slate-50/50 dark:bg-[#0A0F1C]/40 text-center animate-fadeIn space-y-1">
              <p className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                Select an evidence source to begin
              </p>
              <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
                Choose "Use My Document" to ground in a research paper or image, or "Research From The Web" for live online retrieval.
              </p>
            </div>
          )}

          {/* Document Picker Modal */}
          <ExistingDocumentPicker
            isOpen={isDocumentPickerOpen}
            onClose={() => setIsDocumentPickerOpen(false)}
            onSelect={(doc) => {
              handleSelectDocument(doc.id);
              setIsDocumentPickerOpen(false);
            }}
          />

          {/* Document Knowledge Modal */}
          {activeDocument && (
            <DocumentKnowledgeModal
              isOpen={isKnowledgeModalOpen}
              onClose={() => setIsKnowledgeModalOpen(false)}
              document={activeDocument}
              knowledge={activeKnowledge}
            />
          )}
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
                {isCurrentDebateWeb ? (
                  <span className="font-bold text-cyan-600 dark:text-cyan-400 flex items-center gap-1.5 uppercase">
                    <Globe className="w-3.5 h-3.5 text-cyan-500" />
                    <span>WEB RESEARCH GROUNDED: {(liveSession?.researchSources || researchResponse?.sources || []).length} Sources</span>
                  </span>
                ) : (
                  <span className="font-bold text-indigo-700 dark:text-indigo-400 flex items-center gap-1.5 uppercase">
                    <FileText className="w-3.5 h-3.5 text-indigo-500" />
                    <span>GROUNDED IN: {debateDocument?.name || 'Document'}</span>
                  </span>
                )}
                <span className="text-slate-400">•</span>
                {!isCurrentDebateWeb && debateDocument && !debateDocument.isMissing && (
                  <>
                    <span className="text-slate-500 dark:text-slate-400">{debateDocument?.pageCount || 0} pages</span>
                    <span className="text-slate-400">•</span>
                  </>
                )}
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Evidence Pool Active</span>
              </div>
              <h2 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white leading-snug line-clamp-2">
                "{question}"
              </h2>
            </div>

            {/* Workspace Action Triggers */}
            <div className="flex flex-wrap items-center gap-2 shrink-0 self-end md:self-center">
              {/* Live Elapsed Stopwatch */}
              <div className="px-3 py-1.5 rounded-xl border border-white/10 bg-slate-900/90 text-xs font-mono font-bold flex items-center gap-2 text-indigo-400 shadow-sm">
                <span className={`w-2 h-2 rounded-full ${liveSession?.status === 'completed' ? 'bg-emerald-400' : 'bg-indigo-400 animate-pulse'}`} />
                <span>⏱ {formatElapsedTime(elapsedSeconds)}</span>
              </div>

              {/* DEDICATED RED END DEBATE BUTTON (Requirement 3: Only normal user-facing cancellation control) */}
              {liveSession?.status !== 'completed' && liveSession?.status !== 'cancelled' && liveSession?.status !== 'failed' && (
                <button
                  type="button"
                  onClick={() => setShowEndDebateModal(true)}
                  disabled={isCancelling}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-rose-500 bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-bold shadow-md shadow-rose-600/30 transition-all cursor-pointer disabled:opacity-50"
                  title="Stop active debate"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>{isCancelling ? 'Ending...' : 'End Debate'}</span>
                </button>
              )}

              {liveSession?.status === 'cancelled' && (
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-xl bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60 flex items-center gap-1">
                  <StopCircle className="w-3.5 h-3.5" />
                  <span>CANCELLED</span>
                </span>
              )}

              {/* Start New Debate Button (available when debate reaches a terminal state) */}
              {(liveSession?.status === 'completed' || liveSession?.status === 'cancelled' || liveSession?.status === 'failed') && (
                <button
                  type="button"
                  onClick={handleReturnToSetup}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-bold hover:bg-indigo-100 transition-colors shadow-sm cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Start New Debate</span>
                </button>
              )}
            </div>
          </div>

          {/* End Debate Confirmation Modal Dialog (Part 7: Clean Cancellation Experience) */}
          {showEndDebateModal && (
            <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
              <div className="max-w-md w-full bg-white dark:bg-[#0E1424] border border-slate-200 dark:border-white/10 rounded-3xl p-6 shadow-2xl space-y-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 flex items-center justify-center text-rose-600 dark:text-rose-400 shrink-0">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold font-mono text-slate-900 dark:text-white">
                      End this debate?
                    </h3>
                  </div>
                </div>

                <div className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                  <p>
                    Are you sure you want to stop the ongoing debate?
                  </p>
                </div>

                {cancellationError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs font-mono">
                    <span>{cancellationError}</span>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100 dark:border-white/5 font-mono text-xs">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setShowEndDebateModal(false);
                      setCancellationError(null);
                    }}
                    disabled={isCancelling}
                    className="px-4 uppercase tracking-wider"
                  >
                    Keep Debating
                  </Button>

                  <button
                    type="button"
                    onClick={handleConfirmEndDebate}
                    disabled={isCancelling}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold uppercase tracking-wider transition-all cursor-pointer shadow-md shadow-rose-600/20 disabled:opacity-50"
                  >
                    {isCancelling ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Ending...</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3.5 h-3.5" />
                        <span>End Debate</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

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
              {isCurrentDebateWeb
                ? 'Web Evidence Sources'
                : `Document Source (p. ${viewerTargetPage})`}
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
              {isCurrentDebateWeb ? (
                /* WEB RESEARCH EVIDENCE SOURCES */
                <div className="rounded-3xl border border-cyan-500/30 bg-white/95 dark:bg-[#070b18]/95 p-5 shadow-xl space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
                        <Globe className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-mono font-bold uppercase text-slate-900 dark:text-white">
                          Verified Web Sources
                        </h4>
                        <span className="text-[10px] font-mono text-cyan-600 dark:text-cyan-400 font-semibold">
                          Shared Debate Evidence Pool
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-700">
                      {(liveSession?.researchSources || researchResponse?.sources || []).length} Sources Indexed
                    </span>
                  </div>

                  <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
                    {(liveSession?.researchSources || researchResponse?.sources || []).length > 0 ? (
                      (liveSession?.researchSources || researchResponse?.sources || []).map((source: any, idx: number) => {
                        let hostname = '';
                        try {
                          hostname = new URL(source.url).hostname.replace('www.', '');
                        } catch (_) {
                          hostname = source.source || 'Web Source';
                        }

                        return (
                          <div
                            key={source.id || idx}
                            className="p-3.5 rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0A0F1E] space-y-2 hover:border-cyan-400/40 transition-colors font-mono"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/20">
                                {hostname}
                              </span>
                              {(source.publishedDate || source.published_date) && (
                                <span className="text-[10px] text-slate-400">
                                  {source.publishedDate || source.published_date}
                                </span>
                              )}
                            </div>

                            <h5 className="text-xs font-bold text-slate-900 dark:text-white leading-snug">
                              {source.title}
                            </h5>

                            {(source.snippet || source.claim) && (
                              <p className="text-[11px] text-slate-600 dark:text-slate-300 italic leading-relaxed line-clamp-3">
                                "{source.snippet || source.claim}"
                              </p>
                            )}

                            {source.url && (
                              <div className="pt-1 flex items-center justify-between">
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-[11px] text-cyan-600 dark:text-cyan-400 hover:underline"
                                >
                                  <span>Inspect Source Article</span>
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <div className="p-4 rounded-2xl border border-dashed border-cyan-300 dark:border-cyan-500/30 text-center text-xs font-mono text-slate-500">
                        Gathering online research evidence for active debate...
                      </div>
                    )}
                  </div>
                </div>
              ) : debateDocument ? (
                debateDocument.isMissing ? (
                  /* CLEAR MISSING DOCUMENT STATE - REQUIREMENT 3 */
                  <div className="rounded-3xl border border-rose-300 dark:border-rose-500/30 bg-rose-50/60 dark:bg-rose-950/20 p-6 text-center space-y-3 shadow-xl">
                    <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 mx-auto">
                      <AlertTriangle className="w-6 h-6" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="text-sm font-mono font-bold text-slate-900 dark:text-white">
                        Associated Document Not Found
                      </h4>
                      <p className="text-xs text-slate-600 dark:text-slate-400 max-w-sm mx-auto">
                        The original document associated with this debate could not be found in the repository. Unrelated documents have not been substituted.
                      </p>
                    </div>
                    <div className="pt-2 text-[11px] font-mono text-slate-400">
                      Document ID: {debateDocument.id}
                    </div>
                  </div>
                ) : (
                  <DocumentViewer
                    document={debateDocument}
                    evidenceItems={evidenceItems}
                    activeEvidenceId={activeEvidenceHighlight}
                    targetPage={viewerTargetPage}
                    className="border-indigo-500/20 shadow-xl"
                  />
                )
              ) : (
                <div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-white/95 dark:bg-[#070b18]/95 p-6 text-center space-y-2 shadow-xl">
                  <p className="text-xs font-mono text-slate-500">
                    No document associated with this debate session.
                  </p>
                </div>
              )}
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
                        currentStep >= judgeStep
                          ? 'CONVERGENCE'
                          : streamingSpeaker === 'PRO' || (currentStep > 0 && currentStep % 2 === 1 && currentStep < judgeStep)
                          ? 'PRO_THINKING'
                          : streamingSpeaker === 'CON' || (currentStep > 0 && currentStep % 2 === 0 && currentStep < judgeStep)
                          ? 'CON_THINKING'
                          : 'EXCHANGE'
                      }
                      showSynthesisLine={currentStep >= judgeStep}
                      synthesisLineLength={currentStep >= judgeStep ? 1.0 : 0.0}
                    />
                  </div>

                  <div className="relative z-20 w-full flex items-start justify-between px-2 sm:px-6">
                    {/* Left: AI PRO Brain */}
                    <div className="flex flex-col items-center">
                      <AINeuralBrain
                        type="PRO"
                        size="sm"
                        state={
                          streamingSpeaker === 'PRO' || (currentStep > 0 && currentStep % 2 === 1 && currentStep < judgeStep)
                            ? 'thinking'
                            : currentStep >= judgeStep
                            ? 'converging'
                            : 'idle'
                        }
                        showLabel={true}
                        subLabel={proModel}
                      />
                    </div>

                    {/* Center: Independent Judge Neural Core */}
                    <div className="flex flex-col items-center pt-12">
                      <NeuralCoreView
                        size="sm"
                        state={currentStep >= completedStep ? 'synthesizing' : currentStep === judgeStep ? 'analyzing' : 'idle'}
                        glowColor={currentStep >= completedStep ? 'amber' : currentStep === judgeStep ? 'indigo' : 'neutral'}
                      />
                      <span className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 mt-2 uppercase">
                        INDEPENDENT JUDGE
                      </span>
                      <span className="text-[10px] font-mono text-indigo-500 font-semibold">
                        {currentStep >= completedStep
                          ? 'SYNTHESIS COMPLETE'
                          : currentStep === judgeStep
                          ? 'ARBITRATING FIDELITY'
                          : 'OBSERVING TURNS'}
                      </span>
                    </div>

                    {/* Right: AI CON Brain */}
                    <div className="flex flex-col items-center">
                      <AINeuralBrain
                        type="CON"
                        size="sm"
                        state={
                          streamingSpeaker === 'CON' || (currentStep > 0 && currentStep % 2 === 0 && currentStep < judgeStep)
                            ? 'thinking'
                            : currentStep >= judgeStep
                            ? 'converging'
                            : 'idle'
                        }
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
                      {Array.from({ length: totalSteps }, (_, i) => i + 1).map((st) => (
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
                      Round {currentDisplayRound} of {activeRounds}
                    </span>
                  </div>

                  {/* Arguments list revealed progressively */}
                  <div className="space-y-4">
                    {debateTimeline.slice(0, currentStep >= judgeStep ? debateTimeline.length : Math.max(currentStep, debateTimeline.length)).map((arg) => {
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
                                <span>
                                  {arg.evidenceId?.startsWith('img-') || arg.sectionTitle?.includes('Visual Evidence')
                                    ? `VIEW EVIDENCE (${arg.evidenceId})`
                                    : `VIEW SOURCE (p. ${arg.pageNumber})`}
                                </span>
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
                                <span>Verified against {debateDocument?.name || 'Document'}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* Live Streaming Speech Bubble */}
                    {streamingSpeaker && (
                      <div
                        className={`rounded-2xl p-5 border transition-all duration-300 animate-fadeIn ${
                          streamingSpeaker === 'PRO'
                            ? 'border-sky-300 dark:border-sky-500/50 bg-sky-50/60 dark:bg-sky-950/30'
                            : 'border-purple-300 dark:border-purple-500/50 bg-purple-50/60 dark:bg-purple-950/30'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-200/60 dark:border-white/5">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full flex items-center gap-1.5 ${
                                streamingSpeaker === 'PRO'
                                  ? 'bg-sky-100 dark:bg-sky-900/60 text-sky-700 dark:text-sky-300'
                                  : 'bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300'
                              }`}
                            >
                              <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
                              <span>GENERATING • ROUND {streamingRound} • AI {streamingSpeaker}</span>
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {streamingModel || (streamingSpeaker === 'PRO' ? 'Gemma 4 E4B' : 'Qwen2.5-VL-7B')}
                            </span>
                          </div>

                          <div className="flex items-center gap-2.5 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                            <span>{tokenCount} tokens</span>
                            <span>•</span>
                            <span className="font-semibold text-indigo-400">
                              {(tokenCount / Math.max(1, elapsedSeconds)).toFixed(1)} tok/s
                            </span>
                            <span>•</span>
                            <span>⏱ {formatElapsedTime(elapsedSeconds)}</span>
                          </div>
                        </div>

                        <div className="mt-3 text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-mono whitespace-pre-wrap bg-black/20 p-3 rounded-xl border border-white/5">
                          {streamingText ? (
                            <span>{streamingText}</span>
                          ) : (
                            <span className="text-slate-400 italic">Evaluating context and generating dialectical arguments...</span>
                          )}
                          <span className="inline-block w-1.5 h-3.5 bg-indigo-500 animate-pulse ml-0.5 align-middle" />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 5. Independent Judge Evaluation (Requirement 14) */}
                {currentStep >= judgeStep && (
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
                            JUDGE: {judgeProvider === 'nvidia' ? 'NVIDIA NIM' : 'Google Gemini'} ({judgeModel}) · Neutral Arbitration
                          </span>
                        </div>
                      </div>

                      <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-700 font-bold">
                        {currentStep >= completedStep ? 'Deliberation Complete' : 'Deliberating'}
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
                          currentStep >= completedStep;

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
                {currentStep >= completedStep && (
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
                              {liveSynthesis?.executionStatus === 'REAL_REMOTE_API' && !liveSynthesis?.isFallback
                                ? `Arbitrated by ${
                                    liveSynthesis.judgeProvider === 'nvidia' ||
                                    (liveSynthesis.judgeModelUsed && (liveSynthesis.judgeModelUsed.includes('nvidia') || liveSynthesis.judgeModelUsed.includes('nemotron')))
                                      ? 'NVIDIA NIM'
                                      : 'Google Gemini'
                                  } (${liveSynthesis.judgeModelUsed || judgeModel})`
                                : `Adjudication: ${liveSynthesis?.judgeModelUsed === 'failed' ? 'Evaluation Failed (No Certified Verdict)' : 'Offline / Fallback Evaluation'}`}
                            </span>
                            <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full ${
                              liveSynthesis?.executionStatus === 'REAL_REMOTE_API' && !liveSynthesis?.isFallback
                                ? 'bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-600/40'
                                : liveSynthesis?.judgeModelUsed === 'failed'
                                ? 'bg-rose-100 dark:bg-rose-950/80 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-600/40'
                                : 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-600/40'
                            }`}>
                              {liveSynthesis?.executionStatus === 'REAL_REMOTE_API' && !liveSynthesis?.isFallback
                                ? 'REAL REMOTE API'
                                : liveSynthesis?.judgeModelUsed === 'failed'
                                ? 'EVALUATION FAILED'
                                : 'FALLBACK / SIMULATED'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700/60">
                        Document Grounding: {liveSynthesis?.evidenceReliabilityScore !== undefined && liveSynthesis?.evidenceReliabilityScore !== null ? `${Math.round(liveSynthesis.evidenceReliabilityScore)}%` : 'Pending'}
                      </span>
                    </div>

                    {/* Impartial Adjudication Verdict & Score Showcase */}
                    {liveSynthesis && (liveSynthesis.proScore !== undefined || liveSynthesis.winner) && (
                      <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-[#070a16] border border-amber-300 dark:border-amber-500/40 shadow-md space-y-4">
                        {/* Winner Banner */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/[0.08]">
                          <div className="flex items-center gap-2.5">
                            <span className="text-xs font-mono font-bold uppercase text-slate-500 dark:text-slate-400">Official Ruling:</span>
                            <span className={`px-3 py-1 rounded-xl text-xs sm:text-sm font-mono font-black uppercase tracking-wider ${
                              liveSynthesis.winner === 'PRO'
                                ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/30'
                                : liveSynthesis.winner === 'CON'
                                ? 'bg-violet-500/15 text-violet-700 dark:text-violet-300 border border-violet-500/30'
                                : liveSynthesis.winner === 'INCONCLUSIVE'
                                ? 'bg-amber-500/15 text-amber-800 dark:text-amber-300 border border-amber-500/30'
                                : 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30'
                            }`}>
                              {liveSynthesis.winner === 'PRO'
                                ? '🏆 PRO VICTORY'
                                : liveSynthesis.winner === 'CON'
                                ? '🏆 CON VICTORY'
                                : liveSynthesis.winner === 'INCONCLUSIVE'
                                ? '⚖️ DIALECTICAL DRAW (INCONCLUSIVE)'
                                : '❌ EVALUATION INCONCLUSIVE / FAILED'}
                            </span>
                            {liveSynthesis.verdictType && (
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                                {liveSynthesis.verdictType.replace('_', ' ')}
                              </span>
                            )}
                          </div>

                          <div className="text-xs font-mono text-slate-600 dark:text-slate-400">
                            {liveSynthesis.proScore !== undefined && liveSynthesis.conScore !== undefined && (
                              <span>
                                Score Margin: <strong className="text-slate-900 dark:text-white">|{liveSynthesis.proScore.toFixed(1)} - {liveSynthesis.conScore.toFixed(1)}| = {Math.abs(liveSynthesis.proScore - liveSynthesis.conScore).toFixed(1)} pts</strong>
                                {Math.abs(liveSynthesis.proScore - liveSynthesis.conScore) <= 2.0 && ' (Draw threshold <= 2.0)'}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* PRO vs CON Score Cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono">
                          {/* PRO Score Card */}
                          <div className={`p-4 rounded-xl border ${
                            liveSynthesis.winner === 'PRO'
                              ? 'bg-sky-500/10 border-sky-500/40 ring-1 ring-sky-500/30'
                              : 'bg-slate-50 dark:bg-[#0A0F1C] border-slate-200 dark:border-white/[0.06]'
                          }`}>
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-sky-600 dark:text-sky-400 uppercase">PRO · Gemma 4 E4B</span>
                              {liveSynthesis.winner === 'PRO' && <span className="text-[10px] uppercase font-bold text-sky-600 dark:text-sky-400">Winner</span>}
                            </div>
                            <div className="mt-2 flex items-baseline gap-1.5">
                              <span className="text-3xl font-black text-slate-900 dark:text-white">
                                {liveSynthesis.proScore !== undefined ? liveSynthesis.proScore.toFixed(1) : '--'}
                              </span>
                              <span className="text-xs text-slate-400">/ 100 pts</span>
                            </div>
                          </div>

                          {/* CON Score Card */}
                          <div className={`p-4 rounded-xl border ${
                            liveSynthesis.winner === 'CON'
                              ? 'bg-violet-500/10 border-violet-500/40 ring-1 ring-violet-500/30'
                              : 'bg-slate-50 dark:bg-[#0A0F1C] border-slate-200 dark:border-white/[0.06]'
                          }`}>
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-violet-600 dark:text-violet-400 uppercase">CON · Qwen2.5-VL-7B</span>
                              {liveSynthesis.winner === 'CON' && <span className="text-[10px] uppercase font-bold text-violet-600 dark:text-violet-400">Winner</span>}
                            </div>
                            <div className="mt-2 flex items-baseline gap-1.5">
                              <span className="text-3xl font-black text-slate-900 dark:text-white">
                                {liveSynthesis.conScore !== undefined ? liveSynthesis.conScore.toFixed(1) : '--'}
                              </span>
                              <span className="text-xs text-slate-400">/ 100 pts</span>
                            </div>
                          </div>
                        </div>

                        {/* 6-Criterion Rubric Comparison */}
                        {liveSynthesis.proCriteriaScores && liveSynthesis.conCriteriaScores && Object.keys(liveSynthesis.proCriteriaScores).length > 0 && (
                          <div className="pt-2 border-t border-slate-100 dark:border-white/[0.08] space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                                6-Criterion Explainable Rubric (100 pts max)
                              </span>
                              <button
                                type="button"
                                onClick={() => setShowCriteriaBreakdown(!showCriteriaBreakdown)}
                                className="text-[11px] font-mono text-amber-600 dark:text-amber-400 hover:underline cursor-pointer flex items-center gap-1"
                              >
                                <span>{showCriteriaBreakdown ? 'Hide Breakdown' : 'Show Detailed Criteria'}</span>
                                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showCriteriaBreakdown ? 'rotate-180' : ''}`} />
                              </button>
                            </div>

                            {showCriteriaBreakdown && (
                              <div className="space-y-2 animate-fadeIn text-xs font-mono">
                                {[
                                  { key: 'evidence_quality', label: '1. Evidence Quality & Grounding', max: 25 },
                                  { key: 'logical_reasoning', label: '2. Logical Reasoning & Soundness', max: 20 },
                                  { key: 'relevance', label: '3. Relevance to Proposition', max: 15 },
                                  { key: 'rebuttal_effectiveness', label: '4. Rebuttal Effectiveness & Clash', max: 15 },
                                  { key: 'argument_strength', label: '5. Argument Strength & Depth', max: 15 },
                                  { key: 'consistency', label: '6. Consistency Across Rounds', max: 10 },
                                ].map((crit) => {
                                  const proCrit = liveSynthesis.proCriteriaScores?.[crit.key];
                                  const conCrit = liveSynthesis.conCriteriaScores?.[crit.key];
                                  const pScore = proCrit?.score ?? 0;
                                  const cScore = conCrit?.score ?? 0;
                                  return (
                                    <div key={crit.key} className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#0A0F1C] border border-slate-200/60 dark:border-white/[0.04] space-y-1.5">
                                      <div className="flex items-center justify-between">
                                        <span className="font-bold text-slate-800 dark:text-slate-200">{crit.label} (/{crit.max})</span>
                                        <div className="flex items-center gap-3">
                                          <span className="text-sky-600 dark:text-sky-400 font-bold">PRO: {pScore.toFixed(1)}</span>
                                          <span className="text-slate-300 dark:text-slate-600">|</span>
                                          <span className="text-violet-600 dark:text-violet-400 font-bold">CON: {cScore.toFixed(1)}</span>
                                        </div>
                                      </div>
                                      {(proCrit?.deductions_explanation || conCrit?.deductions_explanation) && (
                                        <div className="text-[10px] text-slate-500 dark:text-slate-400 space-y-0.5 pt-1 border-t border-slate-200/40 dark:border-white/[0.04]">
                                          {proCrit?.deductions_explanation && (
                                            <div><strong className="text-sky-600 dark:text-sky-400">PRO deduction:</strong> {proCrit.deductions_explanation}</div>
                                          )}
                                          {conCrit?.deductions_explanation && (
                                            <div><strong className="text-violet-600 dark:text-violet-400">CON deduction:</strong> {conCrit.deductions_explanation}</div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Decisive Clashes Callout */}
                        {liveSynthesis.decisiveArguments && liveSynthesis.decisiveArguments.length > 0 && (
                          <div className="p-3 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-500/20 text-xs font-mono space-y-1">
                            <span className="font-bold text-amber-800 dark:text-amber-300 uppercase block">Decisive Turning Points:</span>
                            <ul className="list-disc list-inside space-y-0.5 text-slate-700 dark:text-slate-300">
                              {liveSynthesis.decisiveArguments.map((da, idx) => (
                                <li key={idx}>{da}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Balanced Conclusion (Requirement 14) */}
                    <div className="p-4 sm:p-5 rounded-2xl bg-white/90 dark:bg-[#070a16]/90 border border-amber-200 dark:border-amber-500/30 shadow-sm space-y-2">
                      <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                        Balanced Conclusion
                      </span>
                      <p className="text-sm sm:text-base text-slate-900 dark:text-slate-100 leading-relaxed font-semibold italic">
                        "{liveSynthesis?.balancedVerdict || 'Adjudication completed. See dialectical transcript and evidence citations below.'}"
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
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          {liveSynthesis?.keyConsensus?.[0] || 'Affirmative position grounded in verified documentary empirical evidence.'}
                        </p>
                      </div>

                      {/* Strongest Counterargument */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <Scale className="w-3.5 h-3.5 text-purple-500" />
                            Strongest Counterargument
                          </span>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          {liveSynthesis?.keyContentions?.[0] || 'Opposition mounted rigorous challenge regarding complexity and scaling limits.'}
                        </p>
                      </div>

                      {/* Main Limitation */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-sky-500" />
                            Main Limitation
                          </span>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          {liveSynthesis?.keyContentions?.[1] || liveSynthesis?.summary || 'Empirical findings are subject to operational boundary conditions and computational constraints.'}
                        </p>
                      </div>

                      {/* Important Uncertainty */}
                      <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 space-y-1.5">
                        <span className="font-mono font-bold uppercase text-slate-900 dark:text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
                            Important Uncertainty
                          </span>
                        </span>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                          {liveSynthesis?.keyConsensus?.[1] || 'Generalizability of performance metrics beyond benchmark experimental conditions.'}
                        </p>
                      </div>
                    </div>

                    {/* Source References List (Requirement 14) */}
                    <div className="p-4 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-500/30 text-xs space-y-2">
                      <span className="font-mono font-bold uppercase text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        {isCurrentDebateWeb
                          ? 'Web Research Evidence Citations:'
                          : debateDocument && ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((debateDocument.fileType || '').toLowerCase())
                          ? 'Visual Evidence Citations (Click to inspect):'
                          : 'Document Source References (Click to inspect page):'}
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                        {isCurrentDebateWeb ? (
                          (liveSession?.researchSources || researchResponse?.sources || []).length > 0 ? (
                            (liveSession?.researchSources || researchResponse?.sources || []).map((s: any, idx: number) => (
                              <a
                                key={s.id || idx}
                                href={s.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-between p-2 rounded-lg bg-white/70 dark:bg-black/30 border border-slate-200 dark:border-white/10 hover:border-cyan-400 text-left transition-all"
                              >
                                <span className="text-slate-700 dark:text-slate-300 truncate font-mono text-[11px]">
                                  [Source {idx + 1}]: {s.title}
                                </span>
                                <ExternalLink className="w-3 h-3 text-cyan-500 shrink-0 ml-1.5" />
                              </a>
                            ))
                          ) : (
                            <div className="col-span-2 text-slate-400 italic">
                              Web research citations will appear here once debater turns are rendered.
                            </div>
                          )
                        ) : debateTimeline.length > 0 ? (
                          debateTimeline
                            .map((t, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => handleJumpToCitation(t.pageNumber!, t.evidenceId)}
                                className="flex items-center justify-between p-2 rounded-lg bg-white/70 dark:bg-black/30 border border-slate-200 dark:border-white/10 hover:border-indigo-400 text-left transition-all cursor-pointer"
                              >
                                <span className="text-slate-700 dark:text-slate-300 truncate">
                                  {t.evidenceId?.startsWith('img-') || t.sectionTitle?.includes('Visual')
                                    ? `Evidence [${t.evidenceId}]: ${t.sectionTitle} (${t.speaker})`
                                    : `Page ${t.pageNumber}: ${t.sectionTitle} (${t.speaker})`}
                                </span>
                                <ExternalLink className="w-3 h-3 text-indigo-400 shrink-0 ml-1.5" />
                              </button>
                            ))
                        ) : (
                          <div className="col-span-2 text-slate-400 italic">
                            Evidence citations will appear here once debater turns are rendered.
                          </div>
                        )}
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

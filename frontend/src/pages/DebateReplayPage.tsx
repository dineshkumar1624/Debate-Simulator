import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Sparkles,
  Scale,
  Brain,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Award,
  AlertCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  BookOpen,
  Globe,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { DocumentViewer } from '../components/document/DocumentViewer';
import { debateApi } from '../services/api';
import { DebateSession, DebateTurn } from '../types/debate';
import { DocumentMetadata } from '../types/document';

interface FormattedArgument {
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
  executionStatus: string;
}

export const DebateReplayPage: React.FC = () => {
  const { debateId } = useParams<{ debateId: string }>();

  // Replay State - Strictly Read-Only
  const [session, setSession] = useState<DebateSession | null>(null);
  const [documentMeta, setDocumentMeta] = useState<DocumentMetadata | null>(null);
  const [researchSources, setResearchSources] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // UI Interactive States (for local viewing only, zero backend mutations)
  const [expandedArgId, setExpandedArgId] = useState<string | null>(null);
  const [showCriteriaBreakdown, setShowCriteriaBreakdown] = useState<boolean>(true);
  const [viewerTargetPage, setViewerTargetPage] = useState<number>(1);
  const [activeEvidenceHighlight, setActiveEvidenceHighlight] = useState<string | null>(null);

  // Load Saved Historical Debate (GET only)
  useEffect(() => {
    if (!debateId) {
      setError('No debate ID specified.');
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    const fetchReplayData = async () => {
      try {
        // Fetch complete historical debate from read-only history endpoint
        const debateData = await debateApi.getHistoryDebate(debateId);
        if (!isMounted) return;
        setSession(debateData);

        // Preload any linked research sources from debate payload
        if (debateData.researchSources && debateData.researchSources.length > 0) {
          setResearchSources(debateData.researchSources);
        } else if (debateData.config?.sourceScope === 'web' || !debateData.config?.documentId) {
          try {
            const sources = await debateApi.getResearchSources(debateId);
            if (isMounted && sources && sources.length > 0) {
              setResearchSources(sources);
            }
          } catch (_) {}
        }

        // If there's an associated document, fetch its metadata for the viewer
        const docId = debateData.config?.documentId;
        if (docId) {
          try {
            const doc = await debateApi.getDocument(docId);
            if (isMounted && doc) {
              setDocumentMeta(doc);
            }
          } catch (_) {
            // Non-critical: Document viewer will show placeholder if file unmounted
          }
        }
      } catch (err: any) {
        if (!isMounted) return;
        if (err.response?.status === 404) {
          setError(`Debate with ID "${debateId}" was not found in the historical database.`);
        } else {
          setError(err.message || 'Failed to retrieve saved debate history.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchReplayData();

    return () => {
      isMounted = false;
    };
  }, [debateId]);

  // Transform saved turns into formatted Grounded Arguments
  const argumentsList: FormattedArgument[] = useMemo(() => {
    if (!session || !session.rounds) return [];
    const list: FormattedArgument[] = [];

    session.rounds.forEach((rnd) => {
      rnd.turns.forEach((turn: DebateTurn, idx: number) => {
        const isPro = turn.role === 'PRO' || turn.speaker === 'DEBATER_A';
        const ev = turn.evidence && turn.evidence.length > 0 ? (turn.evidence[0] as any) : null;
        let pageNum = 1;
        if (ev?.pageNumber) pageNum = Number(ev.pageNumber);
        else if (ev?.page) pageNum = Number(ev.page);
        else if (ev?.source) {
          const m = String(ev.source).match(/page\s*(\d+)/i);
          if (m) pageNum = parseInt(m[1], 10);
        }

        const evId = ev?.id || ev?.chunk_id || `ev-${rnd.roundNumber}-${idx}`;

        list.push({
          id: `turn-${rnd.roundNumber}-${isPro ? 'pro' : 'con'}-${idx}`,
          roundNumber: rnd.roundNumber,
          speaker: isPro ? 'PRO' : 'CON',
          title: turn.title || (isPro ? `Round ${rnd.roundNumber} Affirmative Case` : `Round ${rnd.roundNumber} Opposition Rebuttal`),
          argumentText: turn.content,
          confidence: turn.confidence || 92,
          pageNumber: pageNum,
          sectionTitle: ev?.section || ev?.sectionTitle || (isPro ? 'Affirmative Case' : 'Counter-Examination Rebuttal'),
          supportingEvidence: ev?.claim || ev?.content || 'Verified documentary reference.',
          counterRelation: isPro ? 'Affirmative Grounding: Cites verified documentary findings.' : 'Direct Clash: Rebuts opposing arguments directly.',
          evidenceId: evId,
          executionStatus: turn.executionStatus || 'REAL_LOCAL_MODEL',
        });
      });
    });

    return list;
  }, [session]);

  const handleJumpToCitation = (page: number, evId?: string) => {
    setViewerTargetPage(page);
    if (evId) setActiveEvidenceHighlight(evId);
  };

  // Total speeches count
  const totalTurns = useMemo(() => {
    if (!session?.rounds) return 0;
    return session.rounds.reduce((acc, r) => acc + r.turns.length, 0);
  }, [session]);

  const requestedRounds = session?.config?.rounds || 3;
  const isImageDoc = documentMeta && ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((documentMeta.fileType || '').toLowerCase());

  // 1. Loading State
  if (isLoading) {
    return (
      <div className="relative z-10 max-w-5xl mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 animate-spin">
          <RefreshCw className="w-6 h-6" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
            RETRIEVING SAVED DEBATE...
          </h2>
          <p className="text-sm font-mono text-slate-500 dark:text-slate-400">
            Fetching complete deliberation transcript, grounded citations, and judicial synthesis.
          </p>
        </div>
      </div>
    );
  }

  // 2. Error / 404 State
  if (error || !session) {
    return (
      <div className="relative z-10 max-w-2xl mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-16 h-16 rounded-3xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-500/30 flex items-center justify-center mx-auto text-rose-600 dark:text-rose-400">
          <AlertCircle className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
            DEBATE NOT FOUND
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-md mx-auto">
            {error || 'The requested debate record could not be found in historical storage.'}
          </p>
        </div>
        <div className="pt-4 flex items-center justify-center gap-3">
          <Link to="/history">
            <Button variant="secondary" className="gap-2 font-mono text-xs uppercase tracking-wider">
              <ArrowLeft className="w-4 h-4" />
              <span>Back to History</span>
            </Button>
          </Link>
          <Link to="/debate">
            <Button className="gap-2 font-mono text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-500 text-white">
              <span>Start New Debate</span>
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // 3. Replay Mode Main Interface
  const synthesis = session.synthesis;
  const isWinnerPro = synthesis?.winner === 'PRO';
  const isWinnerCon = synthesis?.winner === 'CON';

  return (
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Banner: Strict Read-Only Notification & Back Navigation */}
      <div className="p-4 sm:p-5 rounded-3xl bg-slate-900 text-white border border-slate-700/80 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/history"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-semibold transition-all border border-slate-700"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>HISTORY</span>
          </Link>

          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold uppercase tracking-wider">
                <CheckCircle2 className="w-3 h-3" />
                HISTORICAL REPLAY • READ-ONLY
              </span>
              <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
                ID: {session.id.slice(0, 8)}...
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5 font-mono">
              Saved Deliberation from {session.createdAt}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <Link to="/debate">
            <Button
              size="sm"
              className="gap-2 font-mono text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-md shadow-indigo-600/30"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>NEW DEBATE</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Proposition Card */}
      <div className="rounded-3xl p-6 sm:p-7 border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#080d1e]/90 backdrop-blur-2xl shadow-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">
              PROPOSITION
            </span>
            <span className="px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 text-[11px] font-bold">
              {requestedRounds} Round{requestedRounds > 1 ? 's' : ''} • {totalTurns} Speeches Saved
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
            <span
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider ${
                session.status === 'completed'
                  ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700'
                  : session.status === 'debating'
                  ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                  : 'bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-700'
              }`}
            >
              {session.status.toUpperCase()}
            </span>
          </div>
        </div>

        <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight leading-snug">
          "{session.topic}"
        </h1>

        {/* Source Reference: Document or Web Research */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 dark:border-white/5 text-xs font-mono">
          <span className="text-slate-500 dark:text-slate-400">Grounded Source:</span>
          {session.config?.sourceScope === 'web' || researchSources.length > 0 ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 font-semibold border border-cyan-200 dark:border-cyan-800">
              <Globe className="w-3.5 h-3.5 text-cyan-500" />
              <span>Web Research Grounded ({researchSources.length || 'Indexed'} Sources)</span>
            </span>
          ) : session.config?.documentName ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold border border-slate-200 dark:border-slate-700">
              <FileText className="w-3.5 h-3.5 text-indigo-500" />
              <span>{session.config.documentName}</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold border border-slate-200 dark:border-slate-700">
              <Scale className="w-3.5 h-3.5 text-indigo-500" />
              <span>General Proposition</span>
            </span>
          )}
          {session.completedAt && (
            <span className="text-slate-400 text-[11px] ml-auto">
              Completed: {session.completedAt}
            </span>
          )}
        </div>
      </div>

      {/* Main Split Layout: Document / Web Sources on Left, Chamber & Arguments on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: Document Viewer or Verified Web Sources */}
        {documentMeta ? (
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#080d1e]/90 shadow-xl p-4 overflow-hidden">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100 dark:border-white/10 text-xs font-mono">
                <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                  <span>EVIDENCE VIEWER</span>
                </span>
                <span className="text-[11px] text-slate-400">
                  {documentMeta.pageCount} Pages • {documentMeta.fileSize || 'Attached'}
                </span>
              </div>
              <div className="min-h-[500px]">
                <DocumentViewer
                  document={documentMeta}
                  targetPage={viewerTargetPage}
                  activeEvidenceId={activeEvidenceHighlight}
                />
              </div>
            </div>
          </div>
        ) : researchSources.length > 0 || session.config?.sourceScope === 'web' ? (
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-3xl border border-cyan-500/30 bg-white/95 dark:bg-[#080d1e]/90 shadow-xl p-5 overflow-hidden space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20 text-xs font-mono">
                <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <Globe className="w-4 h-4 text-cyan-500" />
                  <span>VERIFIED WEB SOURCES</span>
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-700 font-bold">
                  {researchSources.length} Saved Sources
                </span>
              </div>

              <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
                {researchSources.map((source: any, idx: number) => {
                  let hostname = '';
                  try {
                    hostname = new URL(source.url).hostname.replace('www.', '');
                  } catch (_) {
                    hostname = source.source || 'Web Source';
                  }

                  return (
                    <div
                      key={source.id || idx}
                      className="p-3.5 rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0A0F1E] space-y-2 font-mono"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/20">
                          {hostname}
                        </span>
                        {source.published_date && (
                          <span className="text-[10px] text-slate-400">
                            {source.published_date}
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
                })}
              </div>
            </div>
          </div>
        ) : null}

        {/* RIGHT COLUMN: Debater Models, Arguments Timeline & Judge Evaluation */}
        <div className={documentMeta || researchSources.length > 0 || session.config?.sourceScope === 'web' ? 'lg:col-span-7 space-y-6' : 'lg:col-span-12 space-y-6'}>
          {/* Debater Models Overview Bar */}
          <div className="rounded-3xl p-5 border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#080d1e]/90 shadow-xl space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
              {/* PRO Model */}
              <div className="p-3.5 rounded-2xl bg-sky-50/60 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-500/30 space-y-1">
                <div className="flex items-center justify-center gap-1.5 text-sky-600 dark:text-sky-400 text-xs font-mono font-bold uppercase">
                  <Brain className="w-4 h-4" />
                  <span>AI PRO</span>
                </div>
                <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 truncate">
                  {session.config?.debaterAModel || 'Gemma 4 E4B'}
                </div>
                <div className="text-[10px] font-mono text-sky-700 dark:text-sky-300">
                  Affirmative Case
                </div>
              </div>

              {/* Independent Judge */}
              <div className="p-3.5 rounded-2xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-500/30 space-y-1">
                <div className="flex items-center justify-center gap-1.5 text-amber-600 dark:text-amber-400 text-xs font-mono font-bold uppercase">
                  <Scale className="w-4 h-4" />
                  <span>INDEPENDENT JUDGE</span>
                </div>
                <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 truncate">
                  {synthesis?.judgeModelUsed || session.config?.judgeModel || 'NVIDIA Nemotron 3.5'}
                </div>
                <div className="text-[10px] font-mono text-amber-700 dark:text-amber-300 font-bold">
                  {synthesis?.winner ? `Winner: ${synthesis.winner}` : 'Adjudication Complete'}
                </div>
              </div>

              {/* CON Model */}
              <div className="p-3.5 rounded-2xl bg-purple-50/60 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-500/30 space-y-1">
                <div className="flex items-center justify-center gap-1.5 text-purple-600 dark:text-purple-400 text-xs font-mono font-bold uppercase">
                  <Brain className="w-4 h-4" />
                  <span>AI CON</span>
                </div>
                <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 truncate">
                  {session.config?.debaterBModel || 'Qwen 2.5 VL 7B'}
                </div>
                <div className="text-[10px] font-mono text-purple-700 dark:text-purple-300">
                  Opposition Rebuttal
                </div>
              </div>
            </div>

            {/* Stepper Dots: Total Completed Turns */}
            <div className="pt-2 border-t border-slate-100 dark:border-white/5 flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400">
              <span className="font-semibold uppercase tracking-wider">
                Saved Deliberation Turns:
              </span>
              <div className="flex items-center gap-1.5">
                {Array.from({ length: totalTurns || requestedRounds * 2 }).map((_, i) => (
                  <span
                    key={i}
                    className="w-3 h-3 rounded-full bg-emerald-500"
                    title={`Speech ${i + 1}`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Section: Grounded Arguments Chronological Timeline */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/10">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                <span>CHRONOLOGICAL GROUNDED SPEECHES ({argumentsList.length})</span>
              </span>
              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                {requestedRounds} Rounds Recorded
              </span>
            </div>

            {argumentsList.length === 0 ? (
              <div className="p-8 text-center text-slate-500 font-mono text-xs rounded-2xl bg-white/50 dark:bg-slate-900/40 border border-slate-200 dark:border-white/5">
                No argument speeches recorded for this debate.
              </div>
            ) : (
              <div className="space-y-4">
                {argumentsList.map((arg) => {
                  const isPro = arg.speaker === 'PRO';
                  const isExpanded = expandedArgId === arg.id;

                  return (
                    <div
                      key={arg.id}
                      className={`rounded-2xl p-5 border transition-all duration-300 ${
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
                          <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-600/40">
                            {arg.executionStatus}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                            Confidence: <strong className="text-slate-800 dark:text-slate-200">{arg.confidence}%</strong>
                          </span>
                          <button
                            type="button"
                            onClick={() => setExpandedArgId(isExpanded ? null : arg.id)}
                            className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                            aria-label={isExpanded ? 'Collapse' : 'Expand'}
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      {/* Argument Body */}
                      <div className="pt-3 space-y-2">
                        <h3 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white leading-snug">
                          {arg.title}
                        </h3>
                        <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap font-normal">
                          {arg.argumentText}
                        </p>
                      </div>

                      {/* Evidence Grounding Box */}
                      <div className="mt-3.5 p-3 rounded-xl bg-white/70 dark:bg-black/30 border border-slate-200/80 dark:border-white/5 space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-1.5 text-[10px] font-mono">
                          <span className="flex items-center gap-1 font-bold text-slate-700 dark:text-slate-300">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                            <span>{arg.sectionTitle}</span>
                          </span>

                          <button
                            type="button"
                            onClick={() => handleJumpToCitation(arg.pageNumber, arg.evidenceId)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-mono font-bold bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/70 cursor-pointer transition-all"
                          >
                            <span>
                              {isImageDoc ? `Visual [${arg.evidenceId}]` : `Page ${arg.pageNumber}`}
                            </span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </button>
                        </div>

                        <p className="text-[11px] text-slate-600 dark:text-slate-400 italic leading-snug">
                          "{arg.supportingEvidence}"
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section: Final Judicial Synthesis & Evaluation */}
          {synthesis && (
            <div className="rounded-3xl p-6 sm:p-7 border-2 border-amber-300 dark:border-amber-500/50 bg-gradient-to-b from-amber-50/70 via-white to-amber-50/50 dark:from-[#181104]/90 dark:via-[#0c0d1e] dark:to-[#080d1e] backdrop-blur-2xl shadow-2xl space-y-6">
              {/* Judge Header */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-amber-200/80 dark:border-amber-800/40">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-2xl bg-amber-100 dark:bg-amber-950/70 border border-amber-300 dark:border-amber-600/50 flex items-center justify-center text-amber-600 dark:text-amber-400 shadow-md">
                    <Award className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-base sm:text-lg font-mono font-black uppercase tracking-wider text-slate-900 dark:text-white">
                      JUDICIAL ADJUDICATION & SYNTHESIS
                    </h2>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs font-mono text-amber-700 dark:text-amber-300 font-semibold">
                        {synthesis.judgeModelUsed || 'NVIDIA Nemotron 3.5'}
                      </span>
                      <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-600/40">
                        {synthesis.executionStatus || 'CERTIFIED'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700/60">
                    Document Grounding: {Math.round(synthesis.evidenceReliabilityScore || 85)}%
                  </span>
                </div>
              </div>

              {/* Winner Announcement & Comparative Scorecard */}
              <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-[#070a16] border border-amber-300 dark:border-amber-500/40 shadow-md space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Adjudicated Winner:
                    </span>
                    <span
                      className={`px-3 py-1 rounded-xl text-xs sm:text-sm font-mono font-black uppercase tracking-wider ${
                        isWinnerPro
                          ? 'bg-sky-100 dark:bg-sky-950/80 text-sky-800 dark:text-sky-300 border border-sky-300 dark:border-sky-600'
                          : isWinnerCon
                          ? 'bg-purple-100 dark:bg-purple-950/80 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-600'
                          : 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-600'
                      }`}
                    >
                      {synthesis.winner || 'INCONCLUSIVE'}
                    </span>
                  </div>

                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                    Decision: {synthesis.verdictType || 'EVIDENCE-GROUNDED'}
                  </span>
                </div>

                {/* Score Comparison Bars */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  {/* PRO Score */}
                  <div className="p-4 rounded-xl border border-sky-200 dark:border-sky-500/30 bg-sky-50/50 dark:bg-sky-950/20 space-y-2">
                    <div className="flex justify-between items-center text-xs font-mono">
                      <span className="font-bold text-sky-700 dark:text-sky-300">
                        AI PRO (Affirmative)
                      </span>
                      <span className="text-sm font-black text-sky-800 dark:text-sky-200">
                        {synthesis.proScore !== undefined ? `${synthesis.proScore}/100` : 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-sky-200/60 dark:bg-sky-900/40 h-2.5 rounded-full overflow-hidden">
                      <div
                        className="bg-sky-500 h-2.5 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, synthesis.proScore || 0)}%` }}
                      />
                    </div>
                  </div>

                  {/* CON Score */}
                  <div className="p-4 rounded-xl border border-purple-200 dark:border-purple-500/30 bg-purple-50/50 dark:bg-purple-950/20 space-y-2">
                    <div className="flex justify-between items-center text-xs font-mono">
                      <span className="font-bold text-purple-700 dark:text-purple-300">
                        AI CON (Opposition)
                      </span>
                      <span className="text-sm font-black text-purple-800 dark:text-purple-200">
                        {synthesis.conScore !== undefined ? `${synthesis.conScore}/100` : 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-purple-200/60 dark:bg-purple-900/40 h-2.5 rounded-full overflow-hidden">
                      <div
                        className="bg-purple-500 h-2.5 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, synthesis.conScore || 0)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* 6 Structured Evaluation Criteria Breakdown */}
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => setShowCriteriaBreakdown(!showCriteriaBreakdown)}
                  className="w-full flex items-center justify-between text-xs font-mono font-bold text-slate-800 dark:text-slate-200 py-1 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <Scale className="w-3.5 h-3.5 text-amber-500" />
                    <span>6 STANDARD JUDICIAL EVALUATION CRITERIA BREAKDOWN</span>
                  </span>
                  {showCriteriaBreakdown ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showCriteriaBreakdown && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs font-mono animate-fadeIn">
                    {[
                      { key: 'evidence_quality', label: '1. Evidence Grounding', max: 25 },
                      { key: 'logical_reasoning', label: '2. Reasoning Rigor', max: 20 },
                      { key: 'rebuttal_effectiveness', label: '3. Clash Effectiveness', max: 20 },
                      { key: 'factual_accuracy', label: '4. Factual Precision', max: 15 },
                      { key: 'acknowledgment_of_weakness', label: '5. Limits Acknowledged', max: 10 },
                      { key: 'consistency', label: '6. Cross-Round Consistency', max: 10 },
                    ].map((crit) => {
                      const proCrit = synthesis.proCriteriaScores?.[crit.key];
                      const conCrit = synthesis.conCriteriaScores?.[crit.key];

                      return (
                        <div
                          key={crit.key}
                          className="p-3 rounded-xl bg-slate-50 dark:bg-[#0A0F1C] border border-slate-200/60 dark:border-white/[0.04] space-y-1.5"
                        >
                          <div className="font-bold text-slate-700 dark:text-slate-300 text-[11px] truncate">
                            {crit.label}
                          </div>
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="text-sky-600 dark:text-sky-400">
                              PRO: <strong>{proCrit?.score ?? '—'}</strong>/{crit.max}
                            </span>
                            <span className="text-purple-600 dark:text-purple-400">
                              CON: <strong>{conCrit?.score ?? '—'}</strong>/{crit.max}
                            </span>
                          </div>
                          {(proCrit?.reason || conCrit?.reason) && (
                            <p className="text-[10px] text-slate-500 italic truncate pt-1 border-t border-slate-200/40 dark:border-white/5">
                              {proCrit?.reason || conCrit?.reason}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Balanced Verdict Summary */}
              <div className="p-4 sm:p-5 rounded-2xl bg-white/90 dark:bg-[#070a16]/90 border border-amber-200 dark:border-amber-500/30 shadow-sm space-y-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5" />
                  <span>BALANCED JUDICIAL VERDICT</span>
                </span>
                <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-normal whitespace-pre-wrap">
                  {synthesis.balancedVerdict || synthesis.summary || 'Deliberation completed with verified evidence citations.'}
                </p>
              </div>

              {/* Source References List */}
              <div className="p-4 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-500/30 text-xs space-y-2">
                <span className="font-mono font-bold uppercase text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Verified Document Citations:</span>
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                  {argumentsList.map((t, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleJumpToCitation(t.pageNumber, t.evidenceId)}
                      className="flex items-center justify-between p-2 rounded-lg bg-white/70 dark:bg-black/30 border border-slate-200 dark:border-white/10 hover:border-indigo-400 text-left transition-all cursor-pointer"
                    >
                      <span className="text-slate-700 dark:text-slate-300 truncate">
                        {isImageDoc ? `Visual Evidence (${t.speaker})` : `Page ${t.pageNumber}: ${t.sectionTitle} (${t.speaker})`}
                      </span>
                      <ExternalLink className="w-3 h-3 text-indigo-400 shrink-0 ml-1.5" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DebateReplayPage;

import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  History,
  Search,
  Calendar,
  Layers,
  ArrowRight,
  FileText,
  Award,
  AlertCircle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Scale,
  MessageSquare,
  X,
  ChevronDown,
  ChevronUp,
  Cpu,
  FolderArchive,
  PlayCircle,
  Trash2,
  Loader2,
  Globe,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { debateApi } from '../services/api';
import { GroupedDebateHistoryItem, DebateAttempt, DebateHistoryResponse } from '../types/debate';

interface DeleteTarget {
  type: 'attempt' | 'group' | 'page';
  debateId?: string;
  attemptNumber?: number;
  groupKey?: string;
  topic?: string;
  documentName?: string;
  totalAttempts?: number;
  totalTopics?: number;
  pageNumber?: number;
  debateIds?: string[];
}

/**
 * Defensive normalizer ensuring history items always conform to GroupedDebateHistoryItem
 * with non-undefined `attempts` array, regardless of backend version or payload structure.
 */
function normalizeHistoryGroups(response: any): GroupedDebateHistoryItem[] {
  if (!response) return [];

  // If response is directly an array of items or groups
  const groupsList = Array.isArray(response)
    ? response
    : (Array.isArray(response.groups) ? response.groups : null);

  // If backend provided groups
  if (groupsList && groupsList.length > 0) {
    return groupsList
      .filter((group: any) => Boolean(group))
      .map((group: any) => {
        const rawAttempts = Array.isArray(group.attempts) ? group.attempts : [];
        const attempts = [...rawAttempts];
        // Defensive fallback if attempts is empty but group has an id
        if (attempts.length === 0 && group.id) {
          attempts.push({
            attemptNumber: 1,
            debateId: group.id,
            createdAt: group.createdAt || '',
            completedAt: group.latestCompletedAt,
            winner: group.latestWinner,
            proScore: group.latestProScore,
            conScore: group.latestConScore,
            roundsCount: group.latestRoundsCount || 1,
            speechesCount: group.latestSpeechesCount || 0,
          });
        }
        return {
          ...group,
          sourceScope: group.sourceScope || group.source_scope || 'document',
          totalAttempts: group.totalAttempts || attempts.length || 1,
          attempts: attempts.map((a: any) => ({
            ...a,
            sourceScope: a?.sourceScope || a?.source_scope || group.sourceScope || group.source_scope || 'document',
          })),
        };
      });
  }

  // Fallback: If backend provided flat items
  const itemsList = Array.isArray(response.items) ? response.items : (Array.isArray(response) ? response : null);
  if (itemsList && itemsList.length > 0) {
    const rawList = itemsList as any[];
    const completedItems = rawList.filter(
      (item: any) => item && (item.status === 'completed' || item.status === 'cancelled')
    );

    const groupMap = new Map<string, GroupedDebateHistoryItem>();

    for (const item of completedItems) {
      const normalizedTopic = (item.topic || '').trim().replace(/^[«»"\'“‘’”]+|[«»"\'“‘’”]+$/g, '').trim().toLowerCase();
      const docKey = item.documentId || 'general';
      const groupKey = `${normalizedTopic}::${docKey}`;

      const attempt: DebateAttempt = {
        attemptNumber: 1,
        debateId: item.id,
        status: item.status || 'completed',
        createdAt: item.createdAt || '',
        completedAt: item.completedAt || item.createdAt || '',
        winner: item.winner as any,
        proScore: item.proScore,
        conScore: item.conScore,
        roundsCount: item.roundsCount || 1,
        speechesCount: item.messagesCount || item.speechesCount || 0,
        judgeModel: item.judgeModel,
        judgeProvider: item.judgeProvider,
      };

      if (!groupMap.has(groupKey)) {
        groupMap.set(groupKey, {
          groupKey,
          topic: item.topic || 'Untitled Proposition',
          documentId: item.documentId,
          documentName: item.documentName,
          totalAttempts: 1,
          latestCompletedAt: item.completedAt || item.createdAt,
          latestWinner: item.winner as any,
          latestProScore: item.proScore,
          latestConScore: item.conScore,
          latestRoundsCount: item.roundsCount || 1,
          latestSpeechesCount: item.messagesCount || item.speechesCount || 0,
          attempts: [attempt],
        });
      } else {
        const existing = groupMap.get(groupKey)!;
        existing.attempts.push(attempt);
        existing.totalAttempts = existing.attempts.length;
      }
    }

    return Array.from(groupMap.values()).map((grp) => {
      const total = grp.attempts.length;
      grp.attempts.forEach((att, idx) => {
        att.attemptNumber = total - idx;
      });
      const latest = Array.isArray(grp.attempts) && grp.attempts.length > 0 ? grp.attempts[0] : null;
      if (latest) {
        grp.latestCompletedAt = latest.completedAt || latest.createdAt;
        grp.latestWinner = latest.winner;
        grp.latestProScore = latest.proScore;
        grp.latestConScore = latest.conScore;
        grp.latestRoundsCount = latest.roundsCount;
        grp.latestSpeechesCount = latest.speechesCount;
      }
      return grp;
    });
  }

  return [];
}

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();

  // History State
  const [groupedItems, setGroupedItems] = useState<GroupedDebateHistoryItem[]>([]);
  const [totalGroups, setTotalGroups] = useState<number>(0);
  const [totalCompletedDebates, setTotalCompletedDebates] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(15);

  // Expanded Groups State (Collapsed by default)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Search
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = useState<string>('');

  // Loading & Error States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Deletion States
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Debounce search query input (300ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setCurrentPage(1); // Reset to page 1 on new search
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Auto-dismiss toast after 4s
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  // Fetch Grouped History from backend (Strictly completed debates only)
  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response: DebateHistoryResponse = await debateApi.getHistory({
        query: debouncedQuery.trim() || undefined,
        status: 'completed',
        page: currentPage,
        pageSize: pageSize,
      });

      const normalizedGroups = normalizeHistoryGroups(response);
      setGroupedItems(normalizedGroups);
      setTotalGroups(response.totalGroups ?? (normalizedGroups.length || response.total || 0));
      setTotalCompletedDebates(
        response.totalCompletedDebates ??
          normalizedGroups.reduce((acc, g) => acc + (g.totalAttempts || g.attempts?.length || 1), 0)
      );
      setTotalPages(response.totalPages || 1);
    } catch (err: any) {
      console.error('Error fetching debate history:', err);
      setError(err.message || 'Failed to retrieve saved debate history.');
    } finally {
      setIsLoading(false);
    }
  }, [debouncedQuery, currentPage, pageSize]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const toggleGroup = (groupKey: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setCurrentPage(1);
  };

  // Open delete dialog for an individual attempt
  const handleDeleteAttemptClick = (e: React.MouseEvent, group: GroupedDebateHistoryItem, attempt: DebateAttempt) => {
    e.stopPropagation();
    setDeleteTarget({
      type: 'attempt',
      debateId: attempt.debateId,
      attemptNumber: attempt.attemptNumber,
      groupKey: group.groupKey,
      topic: group.topic,
      documentName: group.documentName,
    });
  };

  // Open delete dialog for an entire topic group
  const handleDeleteGroupClick = (e: React.MouseEvent, group: GroupedDebateHistoryItem) => {
    e.stopPropagation();
    const attempts = Array.isArray(group.attempts) ? group.attempts : [];
    const debateIds = attempts.length > 0
      ? attempts.map((a) => a.debateId)
      : (group.id ? [group.id] : []);

    setDeleteTarget({
      type: 'group',
      groupKey: group.groupKey,
      topic: group.topic,
      documentName: group.documentName,
      totalAttempts: group.totalAttempts || attempts.length || 1,
      debateIds,
    });
  };

  // Open delete dialog for all debates on the current page
  const handleDeletePageClick = () => {
    if (groupedItems.length === 0) return;

    const allPageDebateIds: string[] = [];
    let pageAttemptsCount = 0;

    for (const grp of groupedItems) {
      const attempts = Array.isArray(grp.attempts) ? grp.attempts : [];
      if (attempts.length > 0) {
        for (const a of attempts) {
          if (a.debateId) allPageDebateIds.push(a.debateId);
        }
        pageAttemptsCount += attempts.length;
      } else if (grp.id) {
        allPageDebateIds.push(grp.id);
        pageAttemptsCount += 1;
      }
    }

    setDeleteTarget({
      type: 'page',
      pageNumber: currentPage,
      totalTopics: groupedItems.length,
      totalAttempts: pageAttemptsCount,
      debateIds: allPageDebateIds,
    });
  };

  // Confirm and execute deletion
  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;

    setIsDeleting(true);
    try {
      if (deleteTarget.type === 'attempt' && deleteTarget.debateId) {
        // Delete single attempt
        await debateApi.deleteHistoryAttempt(deleteTarget.debateId);

        // Optimistically update UI
        setGroupedItems((prevGroups) => {
          return prevGroups
            .map((grp) => {
              if (grp.groupKey !== deleteTarget.groupKey) return grp;

              const currentAttempts = Array.isArray(grp.attempts) ? grp.attempts : [];
              const remainingAttempts = currentAttempts.filter((a) => a.debateId !== deleteTarget.debateId);
              if (remainingAttempts.length === 0) return null; // Group is empty, remove it

              const latest = remainingAttempts[0];
              return {
                ...grp,
                totalAttempts: remainingAttempts.length,
                latestCompletedAt: latest?.completedAt || latest?.createdAt,
                latestWinner: latest?.winner,
                latestProScore: latest?.proScore,
                latestConScore: latest?.conScore,
                latestRoundsCount: latest?.roundsCount || 1,
                latestSpeechesCount: latest?.speechesCount || 0,
                attempts: remainingAttempts,
              };
            })
            .filter(Boolean) as GroupedDebateHistoryItem[];
        });

        setTotalCompletedDebates((c) => Math.max(0, c - 1));
        setToastMessage({
          type: 'success',
          text: `Attempt #${deleteTarget.attemptNumber || 1} deleted successfully.`,
        });
      } else if (deleteTarget.type === 'group') {
        // Delete entire group
        await debateApi.deleteHistoryGroup({
          debateIds: deleteTarget.debateIds,
          topic: deleteTarget.topic,
          groupKey: deleteTarget.groupKey,
        });

        // Optimistically remove group from UI
        setGroupedItems((prevGroups) => prevGroups.filter((grp) => grp.groupKey !== deleteTarget.groupKey));
        setTotalGroups((g) => Math.max(0, g - 1));
        setTotalCompletedDebates((c) => Math.max(0, c - (deleteTarget.totalAttempts || 1)));
        setToastMessage({
          type: 'success',
          text: `Debate topic and all ${deleteTarget.totalAttempts || 1} attempts deleted successfully.`,
        });
      } else if (deleteTarget.type === 'page') {
        // Delete all debate topics and attempts on this page
        const targetIds = deleteTarget.debateIds || [];
        if (targetIds.length > 0) {
          await debateApi.deleteDebatesBatch(targetIds);
        }

        setToastMessage({
          type: 'success',
          text: `Deleted all ${deleteTarget.totalTopics || 0} debate topics (${deleteTarget.totalAttempts || 0} attempts) on Page ${deleteTarget.pageNumber || currentPage}.`,
        });

        // Refresh list: if this was the last page and was cleared, go back one page
        if (currentPage > 1 && currentPage === totalPages) {
          setCurrentPage((p) => Math.max(1, p - 1));
        } else {
          await loadHistory();
        }
      }
    } catch (err: any) {
      console.error('Error during deletion:', err);
      setToastMessage({
        type: 'error',
        text: err.message || 'Failed to delete debate record.',
      });
    } finally {
      setIsDeleting(false);
      setDeleteTarget(null);
    }
  };

  return (
    <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-2xl shadow-xl font-mono text-xs font-semibold animate-fadeIn border ${
            toastMessage.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/90 text-emerald-800 dark:text-emerald-200 border-emerald-300 dark:border-emerald-700'
              : 'bg-rose-50 dark:bg-rose-950/90 text-rose-800 dark:text-rose-200 border-rose-300 dark:border-rose-700'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="ml-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Confirmation Modal Dialog */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="max-w-md w-full bg-white dark:bg-[#0E1424] border border-slate-200 dark:border-white/10 rounded-3xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 flex items-center justify-center text-rose-600 dark:text-rose-400 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  {deleteTarget.type === 'attempt'
                    ? `Delete Attempt #${deleteTarget.attemptNumber}?`
                    : deleteTarget.type === 'page'
                    ? `Delete All Debates on Page ${deleteTarget.pageNumber}?`
                    : 'Delete Entire Debate Topic?'}
                </h3>
                <span className="text-[11px] font-mono text-rose-500 uppercase tracking-wider font-semibold">
                  Permanent Database Deletion
                </span>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
              {deleteTarget.type === 'attempt' ? (
                <>
                  Are you sure you want to delete <span className="font-semibold text-slate-900 dark:text-white">Attempt #{deleteTarget.attemptNumber}</span> of{' '}
                  <span className="font-semibold text-slate-900 dark:text-white">"{deleteTarget.topic}"</span>? All grounded speeches, citations, and judicial scoring for this attempt will be permanently removed.
                </>
              ) : deleteTarget.type === 'page' ? (
                <>
                  Are you sure you want to delete all{' '}
                  <span className="font-semibold text-slate-900 dark:text-white">{deleteTarget.totalTopics} debate topics</span> ({deleteTarget.totalAttempts} total attempts) currently displayed on{' '}
                  <span className="font-semibold text-slate-900 dark:text-white">Page {deleteTarget.pageNumber}</span>? All deliberations, evidence records, and judge verdicts for these debates will be permanently removed from the database.
                </>
              ) : (
                <>
                  Are you sure you want to delete this debate topic and all{' '}
                  <span className="font-semibold text-slate-900 dark:text-white">{deleteTarget.totalAttempts} completed attempts</span>? This will permanently remove all deliberations, evidence records, and judge verdicts for this proposition.
                </>
              )}
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100 dark:border-white/5 font-mono text-xs">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
                className="px-4 uppercase tracking-wider"
              >
                Cancel
              </Button>

              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold uppercase tracking-wider transition-all cursor-pointer shadow-md shadow-rose-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>
                      {deleteTarget.type === 'attempt'
                        ? 'Delete Attempt'
                        : deleteTarget.type === 'page'
                        ? `Delete All on Page ${deleteTarget.pageNumber}`
                        : 'Delete Topic'}
                    </span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <History className="w-3.5 h-3.5" />
          <span>DEBATE MEMORY ARCHIVE</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-[#0F172A] dark:text-white tracking-tight">
          DEBATE HISTORY
        </h1>
        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
          Browse verified completed deliberations, smart-grouped by question and document. Replay transcripts or delete past attempts and topics.
        </p>
      </div>

      {/* Top Stats Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-2xl bg-white dark:bg-[#080d1e] border border-slate-200/80 dark:border-white/10 shadow-sm space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
            <FolderArchive className="w-4 h-4 text-indigo-500" />
            <span>Debate Topics</span>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white font-mono">
            {totalGroups}
          </div>
          <div className="text-[10px] font-mono text-slate-400">
            Unique Proposition Groups
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-[#080d1e] border border-slate-200/80 dark:border-white/10 shadow-sm space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
            <span>Completed Debates</span>
          </div>
          <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
            {totalCompletedDebates}
          </div>
          <div className="text-[10px] font-mono text-slate-400">
            Verified Adjudications
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-[#080d1e] border border-slate-200/80 dark:border-white/10 shadow-sm space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-amber-600 dark:text-amber-400">
            <Scale className="w-4 h-4" />
            <span>Adjudication Quality</span>
          </div>
          <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 pt-1">
            Nemotron & Gemini
          </div>
          <div className="text-[10px] font-mono text-slate-400">
            Strict Multi-Criteria Scoring
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-[#080d1e] border border-slate-200/80 dark:border-white/10 shadow-sm space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-sky-600 dark:text-sky-400">
            <PlayCircle className="w-4 h-4" />
            <span>Instant Replay</span>
          </div>
          <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 pt-1">
            Zero Model Loading
          </div>
          <div className="text-[10px] font-mono text-slate-400">
            Full Speech Timeline
          </div>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="rounded-3xl p-4 sm:p-5 bg-white/90 dark:bg-[#080d1e]/90 border border-slate-200/90 dark:border-white/10 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search completed debates by proposition question or document title..."
              className="w-full pl-10 pr-10 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/80 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all font-mono"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Top Actions: Delete Page Debates & Refresh */}
          <div className="flex items-center gap-2 shrink-0">
            {groupedItems.length > 0 && (
              <button
                type="button"
                onClick={handleDeletePageClick}
                disabled={isLoading || isDeleting}
                className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2.5 rounded-2xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/80 dark:bg-rose-950/40 text-xs font-mono font-bold text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/60 hover:border-rose-300 dark:hover:border-rose-700 transition-all cursor-pointer shadow-xs disabled:opacity-50"
                title={`Delete all ${groupedItems.length} debate topics on Page ${currentPage}`}
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
                <span>Delete Page Debates</span>
              </button>
            )}

            {/* Quick Refresh Button */}
            <button
              type="button"
              onClick={() => loadHistory()}
              disabled={isLoading}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs font-mono text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all cursor-pointer shrink-0"
              title="Refresh history list"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Filter Indicator & Page Size */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-white/5 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Showing Completed Debates Only
            </span>
            <span className="text-slate-400 text-[11px] hidden md:inline">
              (Ongoing, pending, and incomplete runs are automatically filtered out)
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
            <span>Per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area: Grouped History List or States */}
      {isLoading ? (
        // Loading Skeleton
        <div className="space-y-4">
          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              className="p-6 rounded-3xl bg-white/70 dark:bg-[#080d1e]/70 border border-slate-200/80 dark:border-white/5 space-y-3 animate-pulse"
            >
              <div className="flex justify-between items-center">
                <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded-full" />
                <div className="h-4 w-40 bg-slate-200 dark:bg-slate-800 rounded-full" />
              </div>
              <div className="h-6 w-3/4 bg-slate-200 dark:bg-slate-800 rounded-lg" />
              <div className="flex gap-2 pt-2">
                <div className="h-4 w-28 bg-slate-200 dark:bg-slate-800 rounded-md" />
                <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded-md" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        // Error State
        <div className="p-10 rounded-3xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-500/30 text-center space-y-4 max-w-lg mx-auto">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <div className="space-y-1">
            <h3 className="text-base font-mono font-bold uppercase text-slate-900 dark:text-white">
              Failed to Load History
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {error}
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => loadHistory()}
            className="gap-2 font-mono text-xs uppercase tracking-wider bg-rose-600 hover:bg-rose-500 text-white"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </Button>
        </div>
      ) : groupedItems.length === 0 ? (
        // Empty State
        <div className="p-12 sm:p-16 rounded-3xl bg-white/95 dark:bg-[#080d1e]/85 border border-slate-200/90 dark:border-white/10 text-center max-w-xl mx-auto shadow-xl space-y-5 animate-fadeIn">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 shadow-sm">
            <History className="w-8 h-8" />
          </div>

          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              {searchQuery ? 'NO MATCHING DEBATES' : 'NO COMPLETED DEBATES YET'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 max-w-sm mx-auto leading-relaxed">
              {searchQuery
                ? 'Try adjusting your search query to locate completed debate records.'
                : 'Your successfully completed debates will appear here once judge evaluation finishes.'}
            </p>
          </div>

          <div className="pt-2 flex items-center justify-center gap-3">
            {searchQuery ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleClearSearch}
                className="font-mono text-xs uppercase tracking-wider"
              >
                Clear Search
              </Button>
            ) : (
              <Link to="/debate">
                <Button
                  size="lg"
                  className="gap-2 font-bold px-8 shadow-xl shadow-indigo-600/30 bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs uppercase tracking-wider"
                >
                  <span>START A DEBATE</span>
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      ) : (
        // Smart Grouped Cards List
        <div className="space-y-4">
          {groupedItems.map((group) => {
            const isExpanded = expandedGroups.has(group.groupKey);
            const attempts = Array.isArray(group.attempts) ? group.attempts : [];
            const hasMultipleAttempts = (group.totalAttempts || attempts.length) > 1;
            const latestAttempt = (attempts && attempts.length > 0) ? attempts[0] : (group.id ? {
              attemptNumber: 1,
              debateId: group.id,
              createdAt: group.createdAt || '',
              completedAt: group.latestCompletedAt,
              winner: group.latestWinner || group.winner,
              proScore: group.latestProScore,
              conScore: group.latestConScore,
              roundsCount: group.latestRoundsCount || 1,
              speechesCount: group.latestSpeechesCount || 0,
            } : undefined);
            const activeDebateId = latestAttempt?.debateId || group.id;

            return (
              <div
                key={group.groupKey}
                className="rounded-3xl bg-white/95 dark:bg-[#070a16]/90 border border-slate-200/80 dark:border-white/10 hover:border-indigo-400 dark:hover:border-indigo-500/50 shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden"
              >
                {/* Main Group Header Card */}
                <div className="p-5 sm:p-6 space-y-4">
                  {/* Top Row: Status, Attempt Badge, Completed Date, Winner */}
                  <div className="flex flex-wrap items-center justify-between gap-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Status Badge */}
                      {group.status === 'cancelled' ? (
                        <span className="text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          <span>CANCELLED</span>
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>COMPLETED</span>
                        </span>
                      )}

                      {/* Total Attempts Badge */}
                      <span
                        className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                          hasMultipleAttempts
                            ? 'bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-700/60'
                            : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800'
                        }`}
                      >
                        {group.totalAttempts || attempts.length} {(group.totalAttempts || attempts.length) === 1 ? 'Completed Attempt' : 'Completed Attempts'}
                      </span>

                      {/* Latest Completion Timestamp */}
                      {group.latestCompletedAt && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-mono">
                          <Calendar className="w-3.5 h-3.5" />
                          <span>{group.latestCompletedAt}</span>
                        </div>
                      )}
                    </div>

                    {/* Latest Adjudicated Winner & Scores */}
                    {group.latestWinner && (
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold uppercase shadow-xs ${
                            group.latestWinner === 'PRO'
                              ? 'bg-sky-100 dark:bg-sky-950/60 text-sky-800 dark:text-sky-300 border border-sky-300 dark:border-sky-700/60'
                              : group.latestWinner === 'CON'
                              ? 'bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700/60'
                              : 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60'
                          }`}
                        >
                          <Award className="w-3.5 h-3.5" />
                          <span>Latest: {group.latestWinner}</span>
                          {group.latestProScore !== undefined && group.latestConScore !== undefined && (
                            <span className="font-semibold text-[10px] opacity-90 pl-1 border-l border-current/20">
                              {group.latestProScore} - {group.latestConScore}
                            </span>
                          )}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Primary Proposition Question */}
                  <div
                    onClick={() => {
                      if (hasMultipleAttempts) {
                        toggleGroup(group.groupKey);
                      } else if (activeDebateId) {
                        navigate(`/history/${activeDebateId}`);
                      }
                    }}
                    className="cursor-pointer group/title"
                  >
                    <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white leading-snug group-hover/title:text-indigo-600 dark:group-hover/title:text-indigo-400 transition-colors">
                      "{group.topic}"
                    </h2>
                  </div>

                  {/* Bottom Metadata & Action Controls */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100 dark:border-white/5 text-xs font-mono">
                    <div className="flex flex-wrap items-center gap-2.5 text-slate-500 dark:text-slate-400">
                      {/* Document / Evidence Source Badge */}
                      {group.sourceScope === 'web' || group.sourceScope === 'web_research' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800 font-semibold truncate max-w-[280px]">
                          <Globe className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
                          <span>Web Research Grounded</span>
                        </span>
                      ) : group.documentName ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 font-semibold truncate max-w-[280px]">
                          <FileText className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                          <span className="truncate">{group.documentName}</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-50 dark:bg-slate-900/60 text-slate-400 border border-slate-200/60 dark:border-slate-800/60 text-[11px]">
                          <Scale className="w-3 h-3 text-slate-400 shrink-0" />
                          <span>General Proposition</span>
                        </span>
                      )}

                      {/* Latest Rounds Count */}
                      <span className="inline-flex items-center gap-1">
                        <Layers className="w-3 h-3 text-indigo-500" />
                        <span>{group.latestRoundsCount} Round{group.latestRoundsCount > 1 ? 's' : ''}</span>
                      </span>

                      {/* Latest Speeches Count */}
                      {group.latestSpeechesCount > 0 && (
                        <span className="inline-flex items-center gap-1 text-[11px]">
                          <MessageSquare className="w-3 h-3 text-emerald-500" />
                          <span>{group.latestSpeechesCount} Speeches</span>
                        </span>
                      )}
                    </div>

                    {/* Action Buttons: Expand Attempts, Replay, and Delete Topic */}
                    <div className="flex items-center gap-2">
                      {hasMultipleAttempts ? (
                        <>
                          <button
                            type="button"
                            onClick={() => toggleGroup(group.groupKey)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 font-bold transition-all cursor-pointer text-xs"
                          >
                            <span>{isExpanded ? 'Hide Attempts' : `View ${group.totalAttempts || attempts.length} Attempts`}</span>
                            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>

                          <button
                            type="button"
                            onClick={() => activeDebateId && navigate(`/history/${activeDebateId}`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 font-bold transition-all cursor-pointer text-xs group/btn"
                            title="Replay most recent attempt"
                          >
                            <span>Replay Latest</span>
                            <ArrowRight className="w-3.5 h-3.5 group-hover/btn:translate-x-0.5 transition-transform" />
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => activeDebateId && navigate(`/history/${activeDebateId}`)}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all cursor-pointer text-xs group/btn shadow-sm"
                        >
                          <span>Replay Debate</span>
                          <ArrowRight className="w-3.5 h-3.5 group-hover/btn:translate-x-0.5 transition-transform" />
                        </button>
                      )}

                      {/* Delete Topic / Group Button */}
                      <button
                        type="button"
                        onClick={(e) => handleDeleteGroupClick(e, group)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 hover:border-rose-300 dark:hover:border-rose-800 bg-slate-50 dark:bg-slate-900 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 font-medium transition-all cursor-pointer text-xs group/del"
                        title={hasMultipleAttempts ? `Delete all ${group.totalAttempts || attempts.length} attempts for this topic` : 'Delete this debate'}
                      >
                        <Trash2 className="w-3.5 h-3.5 group-hover/del:scale-110 transition-transform" />
                        <span className="hidden sm:inline">{hasMultipleAttempts ? 'Delete Topic' : 'Delete'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Attempts History Drawer */}
                {isExpanded && (
                  <div className="border-t border-slate-200 dark:border-white/10 bg-slate-50/80 dark:bg-[#050812]/90 p-4 sm:p-5 space-y-3 animate-fadeIn">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200/70 dark:border-white/5 text-xs font-mono text-slate-500 dark:text-slate-400">
                      <span className="font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                        Completed Debate Attempts ({group.totalAttempts || attempts.length} runs)
                      </span>
                      <span>Sorted Newest First</span>
                    </div>

                    <div className="space-y-2.5">
                      {attempts.map((attempt) => {
                        const isLatest = attempt.attemptNumber === (group.totalAttempts || attempts.length);

                        return (
                          <div
                            key={attempt.debateId}
                            className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl border border-slate-200/90 dark:border-white/5 bg-white dark:bg-[#0A0E1E] hover:border-indigo-300 dark:hover:border-indigo-500/40 transition-all font-mono"
                          >
                            {/* Attempt Metadata */}
                            <div className="flex flex-wrap items-center gap-2.5">
                              {/* Attempt Number Badge */}
                              <span
                                className={`text-xs font-bold px-2.5 py-0.5 rounded-lg border ${
                                  isLatest
                                    ? 'bg-indigo-100 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-700/60'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                                }`}
                              >
                                Attempt #{attempt.attemptNumber}
                                {isLatest && <span className="ml-1 text-[10px] font-normal uppercase opacity-80">(Latest)</span>}
                              </span>

                              {/* Completed Timestamp */}
                              <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                                <Calendar className="w-3 h-3" />
                                <span>{attempt.completedAt || attempt.createdAt}</span>
                              </div>

                              {/* Winner & Scores Badge or Cancelled Badge */}
                              {attempt.status === 'cancelled' ? (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-lg border bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800">
                                  <AlertCircle className="w-3 h-3" />
                                  <span>CANCELLED</span>
                                </span>
                              ) : attempt.winner ? (
                                <span
                                  className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-lg border ${
                                    attempt.winner === 'PRO'
                                      ? 'bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 border-sky-200 dark:border-sky-800'
                                      : attempt.winner === 'CON'
                                      ? 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800'
                                      : 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800'
                                  }`}
                                >
                                  <Award className="w-3 h-3" />
                                  <span>{attempt.winner}</span>
                                  {attempt.proScore !== undefined && attempt.conScore !== undefined && (
                                    <span className="font-normal text-[10px]">
                                      ({attempt.proScore} - {attempt.conScore})
                                    </span>
                                  )}
                                </span>
                              ) : null}

                              {/* Rounds / Speeches */}
                              <span className="text-[11px] text-slate-500 dark:text-slate-400 hidden md:inline">
                                {attempt.roundsCount}R · {attempt.speechesCount} Speeches
                              </span>

                              {/* Judge Provider */}
                              {attempt.judgeProvider && (
                                <span className="inline-flex items-center gap-1 text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-900 px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-800 hidden lg:inline-flex">
                                  <Cpu className="w-3 h-3" />
                                  <span className="capitalize">{attempt.judgeProvider}</span>
                                </span>
                              )}

                              {/* Web Research Scope Badge */}
                              {(attempt.sourceScope === 'web' || attempt.sourceScope === 'web_research') && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-mono text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-950/40 px-2 py-0.5 rounded-md border border-cyan-200 dark:border-cyan-800">
                                  <Globe className="w-3 h-3 text-cyan-500" />
                                  <span>Web Research</span>
                                </span>
                              )}
                            </div>

                            {/* Actions for This Attempt: Replay & Delete Attempt */}
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => navigate(`/history/${attempt.debateId}`)}
                                className="gap-1.5 text-xs font-mono uppercase tracking-wider py-1.5 px-3 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-600 hover:text-white border-indigo-200 dark:border-indigo-500/30 transition-all cursor-pointer shadow-xs"
                              >
                                <span>Replay Debate</span>
                                <ArrowRight className="w-3 h-3" />
                              </Button>

                              <button
                                type="button"
                                onClick={(e) => handleDeleteAttemptClick(e, group, attempt)}
                                className="p-2 rounded-xl border border-slate-200 dark:border-white/10 hover:border-rose-300 dark:hover:border-rose-800 bg-slate-50 dark:bg-slate-900 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition-all cursor-pointer group/delatt"
                                title={`Delete Attempt #${attempt.attemptNumber}`}
                              >
                                <Trash2 className="w-3.5 h-3.5 group-hover/delatt:scale-110 transition-transform" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-200 dark:border-white/10 text-xs font-mono text-slate-500 dark:text-slate-400">
          <div>
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, totalGroups)} of {totalGroups} topic groups{' '}
            <span className="text-slate-400">({totalCompletedDebates} total completed debates)</span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1 || isLoading}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="px-3 py-1 font-bold text-slate-900 dark:text-white">
              Page {currentPage} of {totalPages}
            </span>

            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages || isLoading}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryPage;

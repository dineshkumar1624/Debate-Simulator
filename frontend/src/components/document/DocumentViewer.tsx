import React, { useState } from 'react';
import {
  FileText,
  ChevronLeft,
  ChevronRight,
  Search,
  Bookmark,
  Sparkles,
} from 'lucide-react';
import { DocumentMetadata, EvidenceReference } from '../../types/document';

interface DocumentViewerProps {
  document: DocumentMetadata;
  evidenceItems?: EvidenceReference[];
  activeEvidenceId?: string | null;
  onSelectEvidence?: (id: string) => void;
  className?: string;
  targetPage?: number;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  document,
  evidenceItems: _evidenceItems = [],
  activeEvidenceId,
  onSelectEvidence: _onSelectEvidence,
  className = '',
  targetPage,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(targetPage || 8);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSectionId, setSelectedSectionId] = useState<string>('sec-3');

  // Sync when targetPage changes from external trigger
  React.useEffect(() => {
    if (targetPage && targetPage > 0) {
      setCurrentPage(targetPage);
    }
  }, [targetPage]);

  // Jump to page when clicking a section
  const handleSectionClick = (sectionId: string, pageNum: number) => {
    setSelectedSectionId(sectionId);
    setCurrentPage(pageNum);
  };

  return (
    <div
      className={`rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#070b18]/90 backdrop-blur-2xl shadow-xl flex flex-col overflow-hidden ${className}`}
    >
      {/* Top Document Header Bar */}
      <div className="p-4 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center shrink-0 text-indigo-400">
            <FileText className="w-4 h-4 text-indigo-300" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs sm:text-sm font-mono font-bold text-slate-900 dark:text-white truncate">
              {document.name}
            </h3>
            <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <span>{document.pageCount} pages</span>
              <span>•</span>
              <span className="text-emerald-500 dark:text-emerald-400 font-semibold">Source of Truth</span>
            </div>
          </div>
        </div>

        {/* Page Nav controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30 text-slate-600 dark:text-slate-300 transition-colors"
            title="Previous page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-black/40 border border-slate-200 dark:border-white/10 text-[11px] font-mono font-bold text-slate-800 dark:text-slate-200">
            Page {currentPage} / {document.pageCount}
          </span>
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.min(document.pageCount, p + 1))}
            disabled={currentPage >= document.pageCount}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30 text-slate-600 dark:text-slate-300 transition-colors"
            title="Next page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Sections Quick Tabs */}
      <div className="px-4 py-2 border-b border-slate-200/60 dark:border-white/5 bg-slate-100/50 dark:bg-black/20 flex items-center gap-2 overflow-x-auto text-xs font-mono scrollbar-none">
        <span className="text-[10px] uppercase font-bold text-slate-400 shrink-0">
          <Bookmark className="w-3 h-3 inline mr-1" />
          SECTIONS:
        </span>
        {document.sections.map((sec) => (
          <button
            key={sec.id}
            type="button"
            onClick={() => handleSectionClick(sec.id, sec.pageNumber)}
            className={`px-2.5 py-1 rounded-lg text-[10px] shrink-0 transition-all cursor-pointer ${
              selectedSectionId === sec.id || currentPage === sec.pageNumber
                ? 'bg-indigo-600 text-white font-bold shadow-sm'
                : 'bg-white/60 dark:bg-white/5 border border-slate-200 dark:border-white/5 text-slate-600 dark:text-slate-300 hover:text-white hover:bg-indigo-900/30'
            }`}
          >
            {sec.title} (p. {sec.pageNumber})
          </button>
        ))}
      </div>

      {/* Search Input Bar */}
      <div className="px-4 py-2 border-b border-slate-200/60 dark:border-white/5 bg-white dark:bg-transparent flex items-center gap-2">
        <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter document claims or keywords..."
          className="w-full bg-transparent text-xs font-mono text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="text-[10px] font-mono text-slate-400 hover:text-white"
          >
            Clear
          </button>
        )}
      </div>

      {/* Document Page Reader Surface */}
      <div className="p-5 sm:p-6 overflow-y-auto max-h-[460px] space-y-4 font-mono text-xs leading-relaxed text-slate-700 dark:text-slate-300">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200/60 dark:border-white/10 text-[10px] text-slate-400">
          <span>DOCUMENT PAGE {currentPage} OF {document.pageCount}</span>
          <span className="uppercase text-amber-500/90 dark:text-amber-400 font-semibold">
            Illustrative Document Excerpt (Frontend Preview)
          </span>
        </div>

        {/* Dynamic Page Content matching active document sections */}
        {currentPage === 8 ? (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-sky-500">
              § 3.1 Empirical Results & Bayesian Sentencing Benchmark
            </h4>
            <p>
              The central hypothesis evaluates whether automated Bayesian inference bounds reduce inter-circuit variance in complex tort and liability rulings without increasing catastrophic misclassifications.
            </p>

            {/* Highlighted Evidence Passage (Cited by PRO) */}
            <div
              className={`p-3.5 rounded-xl border transition-all ${
                activeEvidenceId === 'ev-1'
                  ? 'border-sky-400 bg-sky-500/20 shadow-[0_0_20px_rgba(56,189,248,0.3)] ring-1 ring-sky-400'
                  : 'border-sky-500/40 bg-sky-500/10 hover:border-sky-400'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-sky-500/30 text-sky-800 dark:text-sky-200 border border-sky-400/50">
                  CITED BY PRO • AFFIRMATIVE EVIDENCE
                </span>
                <span className="text-[10px] text-sky-600 dark:text-sky-300 font-bold">p. 8, ¶ 4</span>
              </div>
              <p className="text-slate-900 dark:text-slate-100 font-semibold italic text-xs">
                "Across 12,000 simulated appellate rulings, autonomous Bayesian priors achieved a 32% reduction in inter-circuit sentencing variance compared to historical judicial panels (p &lt; 0.001)."
              </p>
            </div>

            <p>
              Statistical regression confirms that human judges demonstrated a 28% variance surge on Friday afternoon hearings (the empirical "fatigue coefficient"), whereas autonomous verification models remained strictly invariant across temporal cycles.
            </p>
          </div>
        ) : currentPage === 11 ? (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-sky-500">
              § 3.2 Formal Invariant Verification Envelopes
            </h4>
            <p>
              To prevent unbounded drift, generative proposals are coupled with deterministic satisfiability modulo theories (SMT) constraint solvers.
            </p>

            {/* Highlighted Evidence Passage (Cited by PRO Round 2) */}
            <div
              className={`p-3.5 rounded-xl border transition-all ${
                activeEvidenceId === 'ev-3'
                  ? 'border-sky-400 bg-sky-500/20 shadow-[0_0_20px_rgba(56,189,248,0.3)] ring-1 ring-sky-400'
                  : 'border-sky-500/40 bg-sky-500/10 hover:border-sky-400'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-sky-500/30 text-sky-800 dark:text-sky-200 border border-sky-400/50">
                  CITED BY PRO • INVARIANT PROOF
                </span>
                <span className="text-[10px] text-sky-600 dark:text-sky-300 font-bold">p. 11, ¶ 2</span>
              </div>
              <p className="text-slate-900 dark:text-slate-100 font-semibold italic text-xs">
                "Coupling generative deliberation with SMT constraint solvers guaranteed zero violation of codified statutory floor penalties across the affirmative test corpus."
              </p>
            </div>

            <p>
              Statutory floors function as hard mathematical bounds, proving algorithmic verification enforces compliance that human tribunals intermittently overlook.
            </p>
          </div>
        ) : currentPage === 14 ? (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-purple-500">
              § 4.2 Out-of-Distribution Catastrophe & Moral Blind Spots
            </h4>
            <p>
              Notwithstanding mathematical consistency in routine precedent, severe failure modes emerge when foundational facts stray outside the historical training corpus.
            </p>

            {/* Highlighted Evidence Passage (Cited by CON) */}
            <div
              className={`p-3.5 rounded-xl border transition-all ${
                activeEvidenceId === 'ev-2'
                  ? 'border-purple-400 bg-purple-500/20 shadow-[0_0_20px_rgba(192,132,252,0.3)] ring-1 ring-purple-400'
                  : 'border-purple-500/40 bg-purple-500/10 hover:border-purple-400'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-purple-500/30 text-purple-800 dark:text-purple-200 border border-purple-400/50">
                  CITED BY CON • CRITICAL LIMITATION
                </span>
                <span className="text-[10px] text-purple-600 dark:text-purple-300 font-bold">p. 14, ¶ 2</span>
              </div>
              <p className="text-slate-900 dark:text-slate-100 font-semibold italic text-xs">
                "When presented with non-precedential novel fact patterns (black-swan socio-legal dilemmas), the neural classifier produced confidence scores exceeding 91% on objectively erroneous statutory interpretations."
              </p>
            </div>

            <p>
              Unlike human adjudicators who flag novel ethical dilemmas for constitutional en banc review, the probabilistic engine optimizes expected probability over training distribution, creating invisible yet catastrophic blind spots in moral trade-offs.
            </p>
          </div>
        ) : currentPage === 19 ? (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-purple-500">
              § 5.1 Constitutional Recourse & Democratic Legitimacy
            </h4>
            <p>
              Procedural justice requires an affected individual to comprehend the normative reasoning underpinning state deprivation of liberty or property.
            </p>

            {/* Highlighted Evidence Passage (Cited by CON Round 2) */}
            <div
              className={`p-3.5 rounded-xl border transition-all ${
                activeEvidenceId === 'ev-4'
                  ? 'border-purple-400 bg-purple-500/20 shadow-[0_0_20px_rgba(192,132,252,0.3)] ring-1 ring-purple-400'
                  : 'border-purple-500/40 bg-purple-500/10 hover:border-purple-400'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-purple-500/30 text-purple-800 dark:text-purple-200 border border-purple-400/50">
                  CITED BY CON • CONSTITUTIONAL BOUND
                </span>
                <span className="text-[10px] text-purple-600 dark:text-purple-300 font-bold">p. 19, ¶ 3</span>
              </div>
              <p className="text-slate-900 dark:text-slate-100 font-semibold italic text-xs">
                "Mathematical consistency cannot substitute for civic legitimacy; algorithmic recourse lacks the non-delegable moral accountability demanded by procedural due process."
              </p>
            </div>

            <p>
              Democratic accountability cannot be replaced by statistical optimization, making full judicial automation incompatible with constitutional guarantees.
            </p>
          </div>
        ) : currentPage === 23 ? (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-amber-500">
              § 6.0 Concluding Dual-Track Synthesis Framework
            </h4>
            <p>
              The synthesis of empirical gains and constitutional safeguards suggests a bifurcated administrative structure.
            </p>

            {/* Highlighted Synthesis Passage */}
            <div
              className={`p-3.5 rounded-xl border transition-all ${
                activeEvidenceId === 'ev-5'
                  ? 'border-amber-400 bg-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.3)] ring-1 ring-amber-400'
                  : 'border-amber-500/40 bg-amber-500/10 hover:border-amber-400'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-500/30 text-amber-800 dark:text-amber-200 border border-amber-400/50">
                  SYNTHESIS BASIS • EQUILIBRIUM POLICY
                </span>
                <span className="text-[10px] text-amber-600 dark:text-amber-300 font-bold">p. 23, ¶ 1</span>
              </div>
              <p className="text-slate-900 dark:text-slate-100 font-semibold italic text-xs">
                "The data indicates optimal societal outcomes emerge when autonomous calculation handles bounded formal checks, while final normative discretionary decisions remain with human tribunals."
              </p>
            </div>

            <p>
              This balanced approach prevents out-of-distribution hallucinations while preserving efficiency gains.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-indigo-500">
              § Section Excerpt • Page {currentPage}
            </h4>
            <p>
              Illustrative excerpt from "{document.name}". Extracted sections and page indices provide grounding for AI debate turns.
            </p>
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
              <span className="text-[9px] font-bold uppercase text-slate-400 block mb-1">
                PARAGRAPH CONTEXT
              </span>
              <p className="text-slate-700 dark:text-slate-300 italic">
                "The regulatory necessity of adversarial deliberation demands that prior evidence be examined from both affirming and challenging positions before a final synthesis is decreed."
              </p>
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-[11px]">
              Use the section tabs above or [View Source] links in debate arguments to jump directly to specific evidentiary pages.
            </p>
          </div>
        )}
      </div>

      {/* Footer Status Bar */}
      <div className="p-3 border-t border-slate-200/60 dark:border-white/10 bg-slate-50/50 dark:bg-black/30 flex items-center justify-between text-[10px] font-mono text-slate-400">
        <span className="flex items-center gap-1.5 text-indigo-400">
          <Sparkles className="w-3 h-3" />
          <span>EVIDENCE-GROUNDED REASONING ACTIVE</span>
        </span>
        <button
          type="button"
          onClick={() => setCurrentPage(8)}
          className="text-slate-400 hover:text-white transition-colors"
        >
          Jump to Evidence (p. 8) →
        </button>
      </div>
    </div>
  );
};

export default DocumentViewer;

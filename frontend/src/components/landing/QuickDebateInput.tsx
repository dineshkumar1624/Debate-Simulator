import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  HelpCircle,
  Sparkles,
  FileText,
  Layers,
  Scale,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { useDocument } from '../../context/DocumentContext';
import { DocumentUploader } from '../document/DocumentUploader';
import { DebateMode } from '../../types/document';

export const QuickDebateInput: React.FC = () => {
  const navigate = useNavigate();
  const {
    activeDocument,
    activeQuestion,
    setActiveQuestion,
    selectedMode,
    setSelectedMode,
    documents,
    selectDocument,
  } = useDocument();

  const [question, setQuestion] = useState(activeQuestion);
  const [showUploader, setShowUploader] = useState(false);

  // Sync local question when activeQuestion or activeDocument changes
  useEffect(() => {
    setQuestion(activeQuestion);
  }, [activeQuestion, activeDocument]);

  const handleStartDebate = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = question.trim() || activeQuestion;
    setActiveQuestion(query);
    navigate(
      `/debate?doc=${encodeURIComponent(activeDocument.id)}&question=${encodeURIComponent(
        query
      )}&mode=${selectedMode}`
    );
  };

  const handleSelectSuggestion = (suggestion: string) => {
    setQuestion(suggestion);
    setActiveQuestion(suggestion);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleStartDebate();
    }
  };

  const modes: { id: DebateMode; label: string; icon: React.ReactNode; desc: string }[] = [
    {
      id: 'claim-challenge',
      label: 'Claim vs Challenge',
      icon: <Layers className="w-3.5 h-3.5 text-sky-400" />,
      desc: 'Pro affirmative claims directly challenged by counter-evidence',
    },
    {
      id: 'critical-review',
      label: 'Critical Review',
      icon: <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />,
      desc: 'Rigorously stress-tests methodology and unstated assumptions',
    },
    {
      id: 'balanced-analysis',
      label: 'Balanced Synthesis',
      icon: <Scale className="w-3.5 h-3.5 text-amber-400" />,
      desc: 'Equilibrium analysis weighing tradeoffs and uncertainties',
    },
  ];

  return (
    <section className="relative py-10 z-20">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Glow behind input card */}
        <div className="relative">
          <div className="absolute -inset-1.5 bg-gradient-to-r from-sky-500/10 via-indigo-500/15 to-purple-500/10 rounded-3xl blur-2xl opacity-75 pointer-events-none" />

          {/* Main Floating Glass Card */}
          <div className="relative glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200/80 dark:border-white/10 shadow-[0_20px_60px_-15px_rgba(99,102,241,0.08)] dark:shadow-[0_20px_60px_-15px_rgba(0,0,0,0.6)] bg-white/85 dark:bg-[#080d1e]/85 backdrop-blur-2xl">
            {/* Header: Title & Grounded Document Selector */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200/80 dark:border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm shrink-0">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <span>GROUNDED DEBATE REASONING</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-semibold">
                      SOURCE-BOUND
                    </span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Arguments are extracted and cross-examined directly from your target document.
                  </p>
                </div>
              </div>

              {/* Upload trigger toggle */}
              <button
                type="button"
                onClick={() => setShowUploader(!showUploader)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50/80 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-all font-semibold self-start sm:self-center"
              >
                <Upload className="w-3.5 h-3.5 text-indigo-500" />
                <span>{showUploader ? 'HIDE UPLOADER' : 'UPLOAD / CHANGE DOCUMENT'}</span>
              </button>
            </div>

            {/* Document Uploader Accordion */}
            {showUploader && (
              <div className="mb-6 p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-900/80 border border-slate-200 dark:border-white/10 animate-fadeIn">
                <DocumentUploader onDocumentReady={() => setShowUploader(false)} />
              </div>
            )}

            {/* Active Document Grounding Badge */}
            <div className="mb-5 p-3.5 rounded-2xl bg-slate-100/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-white/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500 shrink-0">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-900 dark:text-white">
                      {activeDocument.name}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                      ({activeDocument.pageCount} pages • {activeDocument.keyClaimsCount} key claims)
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1">
                    {activeDocument.summary}
                  </p>
                </div>
              </div>

              {/* Quick sample switcher */}
              <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                <span className="text-[10px] font-mono text-slate-400 hidden sm:inline">Switch:</span>
                <select
                  value={activeDocument.id}
                  onChange={(e) => selectDocument(e.target.value)}
                  className="text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Mode Selector Tabs */}
            <div className="mb-4">
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 font-bold mb-2">
                DEBATE PROTOCOL MODE:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {modes.map((m) => {
                  const isSelected = selectedMode === m.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setSelectedMode(m.id)}
                      className={`p-2.5 rounded-xl text-left border transition-all ${
                        isSelected
                          ? 'border-indigo-500 bg-indigo-500/10 dark:bg-indigo-950/50 shadow-sm'
                          : 'border-slate-200/80 dark:border-white/5 bg-slate-50/50 dark:bg-slate-900/40 hover:border-slate-300 dark:hover:border-white/15'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {m.icon}
                        <span
                          className={`text-xs font-mono font-bold ${
                            isSelected
                              ? 'text-indigo-600 dark:text-indigo-300'
                              : 'text-slate-700 dark:text-slate-300'
                          }`}
                        >
                          {m.label}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">
                        {m.desc}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Question Input Form */}
            <form onSubmit={handleStartDebate} className="space-y-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="home-question-input"
                  className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white"
                >
                  What question should the AI debate?
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Ask a specific question about the claims, evidence, methods, or conclusions in your document.
                </p>
                <div className="relative pt-1">
                  <textarea
                    id="home-question-input"
                    rows={3}
                    maxLength={400}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="e.g. Does this document provide sufficient evidence to support its main conclusion?"
                    className="w-full rounded-2xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/80 p-3.5 text-sm sm:text-base text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:bg-white dark:focus:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-400 resize-none transition-all shadow-inner leading-relaxed"
                  />
                  <div className="absolute bottom-2.5 right-3 text-[10px] font-mono text-slate-400">
                    {question.length} / 400
                  </div>
                </div>
              </div>

              {/* Suggestions & Action Row */}
              <div className="space-y-3 pt-1">
                {/* Suggestions wrapping onto multiple lines without truncating */}
                <div className="space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1 font-mono">
                    <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                    Suggested questions (click to select and edit):
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Is the main conclusion supported by the evidence?',
                      'What are the strongest methodological limitations?',
                      'Which claims lack sufficient supporting evidence?',
                      'What are the strongest arguments against the author\'s conclusion?',
                      ...(activeDocument.suggestedQuestions || []),
                    ].slice(0, 5).map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={() => handleSelectSuggestion(suggestion)}
                        className="text-xs px-3 py-1.5 rounded-xl bg-slate-100/90 dark:bg-slate-800/80 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-700 dark:hover:text-indigo-300 border border-slate-200/80 dark:border-slate-700/80 hover:border-indigo-200 dark:hover:border-indigo-500/40 font-mono transition-all text-left shadow-sm hover:shadow cursor-pointer leading-snug"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Submit button */}
                <div className="flex justify-end pt-1">
                  <Button
                    type="submit"
                    size="md"
                    className="w-full sm:w-auto px-7 py-2.5 text-xs font-bold gap-2 shadow-lg shadow-indigo-600/30 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white border border-indigo-500/20"
                  >
                    <span>START DOCUMENT DEBATE</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
};

export default QuickDebateInput;

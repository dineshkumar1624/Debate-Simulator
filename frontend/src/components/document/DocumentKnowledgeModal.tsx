import React, { useState } from 'react';
import {
  X,
  BookOpen,
  Sparkles,
  Layers,
  Activity,
  ArrowRight,
  Calculator,
  CheckCircle2,
  Eye,
} from 'lucide-react';
import { DocumentMetadata } from '../../types/document';
import { DocumentViewer } from './DocumentViewer';

interface DocumentKnowledgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentMetadata;
  knowledge: any | null;
}

export const DocumentKnowledgeModal: React.FC<DocumentKnowledgeModalProps> = ({
  isOpen,
  onClose,
  document,
  knowledge,
}) => {
  const [activeTab, setActiveTab] = useState<'pdf_page' | 'sections' | 'concepts' | 'facts' | 'relations'>('pdf_page');

  if (!isOpen) return null;

  const sections = knowledge?.sections || [];
  const concepts = knowledge?.concepts || [];
  const facts = knowledge?.facts || [];
  const relations = knowledge?.cross_section_relations || [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/50 dark:bg-black/80 backdrop-blur-md animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white dark:bg-[#070a10] text-slate-900 dark:text-slate-100 shadow-[0_25px_80px_-15px_rgba(0,0,0,0.85)] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200/80 dark:border-white/[0.08] bg-slate-50/90 dark:bg-[#0b0f19]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/25 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0 shadow-xs">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-mono font-bold text-slate-900 dark:text-white truncate">
                  {document.name}
                </h3>
                <span className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold bg-emerald-500/15 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 dark:border-emerald-400/40 flex items-center gap-1.5 shadow-xs">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                  <span>Knowledge Indexed</span>
                </span>
              </div>
              <p className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate mt-0.5">
                {document.pageCount} pages • {sections.length} sections • {concepts.length} concepts • {facts.length} empirical facts
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Executive Summary Banner */}
        {knowledge?.executive_summary && (
          <div className="px-6 py-3.5 bg-slate-100/90 dark:bg-[#0e1320] border-b border-slate-200 dark:border-white/[0.06] text-xs text-slate-700 dark:text-slate-200 leading-relaxed">
            <span className="font-semibold font-mono text-indigo-600 dark:text-indigo-400">Executive Summary: </span>
            {knowledge.executive_summary}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex items-center gap-1.5 px-6 pt-2.5 border-b border-slate-200/80 dark:border-white/[0.08] bg-slate-100/80 dark:bg-[#080c14] overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('pdf_page')}
            className={`px-3.5 py-2 text-xs font-mono font-medium rounded-t-xl transition-all flex items-center gap-1.5 border-b-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'pdf_page'
                ? 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-white bg-white dark:bg-[#121829] shadow-xs font-semibold'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-white/[0.04]'
            }`}
          >
            <Eye className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Original PDF Pages ({document.pageCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('sections')}
            className={`px-3.5 py-2 text-xs font-mono font-medium rounded-t-xl transition-all flex items-center gap-1.5 border-b-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'sections'
                ? 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-white bg-white dark:bg-[#121829] shadow-xs font-semibold'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-white/[0.04]'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Sections ({sections.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('concepts')}
            className={`px-3.5 py-2 text-xs font-mono font-medium rounded-t-xl transition-all flex items-center gap-1.5 border-b-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'concepts'
                ? 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-white bg-white dark:bg-[#121829] shadow-xs font-semibold'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-white/[0.04]'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Formal Concepts ({concepts.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('facts')}
            className={`px-3.5 py-2 text-xs font-mono font-medium rounded-t-xl transition-all flex items-center gap-1.5 border-b-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'facts'
                ? 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-white bg-white dark:bg-[#121829] shadow-xs font-semibold'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-white/[0.04]'
            }`}
          >
            <Calculator className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Empirical Benchmarks ({facts.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('relations')}
            className={`px-3.5 py-2 text-xs font-mono font-medium rounded-t-xl transition-all flex items-center gap-1.5 border-b-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'relations'
                ? 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-white bg-white dark:bg-[#121829] shadow-xs font-semibold'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-white/[0.04]'
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Cross-Section Relations ({relations.length})</span>
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/70 dark:bg-[#05070d]">
          {/* ORIGINAL PDF PAGES TAB */}
          {activeTab === 'pdf_page' && (
            <div className="rounded-2xl border border-slate-200/90 dark:border-white/10 overflow-hidden bg-white dark:bg-[#070a10] shadow-xs">
              <DocumentViewer
                document={document}
                className="border-0 shadow-none rounded-none"
              />
            </div>
          )}

          {/* SECTIONS TAB */}
          {activeTab === 'sections' && (
            <div className="space-y-3">
              {sections.length === 0 ? (
                <p className="text-xs font-mono text-slate-500 py-6 text-center">No section summaries available for this document.</p>
              ) : (
                sections.map((sec: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl border border-slate-200/80 dark:border-white/[0.08] bg-white dark:bg-[#0c101b] shadow-xs space-y-2.5 transition-all"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="text-xs sm:text-sm font-semibold text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5 truncate">
                        <Layers className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                        <span className="truncate">{sec.title}</span>
                      </h4>
                      {sec.page_number && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/5 shrink-0">
                          Page {sec.page_number}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
                      {sec.summary}
                    </p>
                    {sec.key_takeaway && (
                      <div className="text-[11px] font-mono p-2.5 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/40 border border-indigo-200/70 dark:border-indigo-500/30 text-indigo-950 dark:text-indigo-200">
                        <span className="font-semibold text-indigo-700 dark:text-indigo-400">Takeaway: </span>
                        {sec.key_takeaway}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* CONCEPTS TAB */}
          {activeTab === 'concepts' && (
            <div className="space-y-3">
              {concepts.length === 0 ? (
                <p className="text-xs font-mono text-slate-500 py-6 text-center">No formal concepts extracted for this document.</p>
              ) : (
                concepts.map((con: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl border border-slate-200/80 dark:border-white/[0.08] bg-white dark:bg-[#0c101b] shadow-xs space-y-2.5 transition-all"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs sm:text-sm font-bold text-indigo-700 dark:text-indigo-300 truncate">{con.concept}</h4>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/5 shrink-0">
                          p. {con.page_number}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
                        {con.definition}
                      </p>
                    </div>
                    {con.mathematical_formulation && (
                      <div className="text-[11px] font-mono p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-amber-300 overflow-x-auto shadow-inner">
                        {con.mathematical_formulation}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* FACTS TAB */}
          {activeTab === 'facts' && (
            <div className="space-y-3">
              {facts.length === 0 ? (
                <p className="text-xs font-mono text-slate-500 py-6 text-center">No empirical benchmark facts extracted.</p>
              ) : (
                facts.map((fact: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl border border-slate-200/80 dark:border-white/[0.08] bg-white dark:bg-[#0c101b] shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all"
                  >
                    <div className="space-y-1.5 min-w-0">
                      <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-medium">{fact.fact_statement}</p>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                        <span className="truncate">{fact.section_title}</span>
                        <span>•</span>
                        <span className="shrink-0">Page {fact.page_number}</span>
                      </div>
                    </div>
                    {fact.metric_or_data && (
                      <span className="px-2.5 py-1 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-500/25 text-indigo-700 dark:text-indigo-300 font-mono text-xs font-semibold shrink-0 shadow-xs">
                        {fact.metric_or_data}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* RELATIONS TAB */}
          {activeTab === 'relations' && (
            <div className="space-y-3">
              {relations.length === 0 ? (
                <p className="text-xs font-mono text-slate-500 py-6 text-center">No cross-section relations available.</p>
              ) : (
                relations.map((rel: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl border border-slate-200/80 dark:border-white/[0.08] bg-white dark:bg-[#0c101b] shadow-xs space-y-2.5 transition-all"
                  >
                    <div className="flex items-center gap-2 text-xs font-mono font-semibold">
                      <span className="text-indigo-700 dark:text-indigo-400 truncate">{rel.source_section}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 shrink-0" />
                      <span className="text-violet-700 dark:text-violet-400 truncate">{rel.target_section}</span>
                      <span className="ml-auto text-[10px] uppercase px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/5 text-slate-700 dark:text-slate-300 shrink-0">
                        {rel.relation_type}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
                      {rel.explanation}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200/80 dark:border-white/[0.08] bg-slate-50/90 dark:bg-[#0b0f19] flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
          <span className="truncate mr-3">All facts, citations, and formulas are extracted from the original PDF text.</span>
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-bold text-xs transition-all shadow-md shadow-indigo-600/25 cursor-pointer shrink-0"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentKnowledgeModal;

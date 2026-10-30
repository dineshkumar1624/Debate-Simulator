import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { DocumentUploader } from '../components/document/DocumentUploader';
import { useDocument } from '../context/DocumentContext';

export const DocumentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { documents, selectDocument, activeDocument } = useDocument();

  const handleStartDebateWithDoc = (docId: string) => {
    selectDocument(docId);
    navigate('/debate');
  };

  return (
    <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* 1. Header Section */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <BookOpen className="w-3.5 h-3.5" />
          <span>EVIDENCE REPOSITORY</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 dark:text-white tracking-tight">
          YOUR DOCUMENTS
        </h1>
        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-2xl leading-relaxed">
          Upload research papers, legal briefs, technical specifications, or policy analyses. Each document serves as an objective source of truth for bilateral AI debate.
        </p>
      </div>

      {/* 2. Document Upload Area */}
      <div className="space-y-3">
        <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
          ADD A NEW DOCUMENT
        </h3>
        <DocumentUploader
          compact={false}
          onDocumentReady={() => {
            navigate('/debate');
          }}
        />
      </div>

      {/* 3. Document Repository List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
            LOADED DOCUMENTS ({documents.length})
          </h3>
          <span className="text-[11px] font-mono text-slate-500">
            Select any document to initiate an adversarial inquiry
          </span>
        </div>

        {documents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.map((doc) => {
              const isCurrent = doc.id === activeDocument.id;
              return (
                <div
                  key={doc.id}
                  className={`rounded-3xl border p-5 sm:p-6 backdrop-blur-2xl transition-all shadow-lg flex flex-col justify-between ${
                    isCurrent
                      ? 'border-indigo-500/50 bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-black/80 shadow-[0_0_30px_rgba(99,102,241,0.2)]'
                      : 'border-slate-200/80 dark:border-white/10 bg-white/90 dark:bg-[#070b18]/80 hover:border-indigo-400/40'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-11 h-11 rounded-2xl bg-indigo-500/15 border border-indigo-400/30 flex items-center justify-center shrink-0 text-indigo-400">
                          <FileText className="w-5 h-5 text-indigo-300" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm sm:text-base font-mono font-bold text-slate-900 dark:text-white truncate">
                            {doc.name}
                          </h4>
                          <div className="text-xs font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2 mt-0.5">
                            <span>{doc.pageCount} pages</span>
                            <span>•</span>
                            <span>{doc.fileSize}</span>
                            <span>•</span>
                            <span className="text-emerald-400">Ready</span>
                          </div>
                        </div>
                      </div>

                      {isCurrent && (
                        <span className="px-2.5 py-1 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shrink-0">
                          ACTIVE
                        </span>
                      )}
                    </div>

                    <p className="text-xs font-mono text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed">
                      {doc.summary}
                    </p>

                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/60 dark:border-white/10 text-center text-xs font-mono">
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-black/30">
                        <span className="text-[10px] text-slate-400 block">CLAIMS</span>
                        <span className="font-bold text-slate-900 dark:text-white">{doc.keyClaimsCount}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-black/30">
                        <span className="text-[10px] text-slate-400 block">EVIDENCE</span>
                        <span className="font-bold text-slate-900 dark:text-white">{doc.evidencePointsCount}</span>
                      </div>
                      <div className="p-2 rounded-xl bg-slate-50 dark:bg-black/30">
                        <span className="text-[10px] text-slate-400 block">DEBATES</span>
                        <span className="font-bold text-slate-900 dark:text-white">{doc.debatesCount}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-5">
                    <Button
                      onClick={() => handleStartDebateWithDoc(doc.id)}
                      className="w-full gap-2 font-mono text-xs font-bold bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600"
                    >
                      <span>START DOCUMENT DEBATE</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Empty state */
          <div className="rounded-3xl border border-dashed border-white/15 p-12 text-center space-y-4">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center text-indigo-400">
              <FileText className="w-7 h-7" />
            </div>
            <div>
              <h4 className="text-base font-mono font-bold text-white">NO DOCUMENTS YET</h4>
              <p className="text-xs font-mono text-slate-400 mt-1 max-w-sm mx-auto">
                Upload your first document to start an evidence-grounded debate between opposing AI agents.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentsPage;

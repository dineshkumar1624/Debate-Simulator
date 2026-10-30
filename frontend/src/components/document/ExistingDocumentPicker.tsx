import React from 'react';
import { FileText, Check, X } from 'lucide-react';
import { useDocument } from '../../context/DocumentContext';
import { DocumentMetadata } from '../../types/document';

interface ExistingDocumentPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (doc: DocumentMetadata) => void;
}

export const ExistingDocumentPicker: React.FC<ExistingDocumentPickerProps> = ({
  isOpen,
  onClose,
  onSelect,
}) => {
  const { documents, activeDocument } = useDocument();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white/95 dark:bg-[#070a16]/95 backdrop-blur-2xl shadow-2xl p-6 sm:p-7 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200/80 dark:border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                CHOOSE EXISTING DOCUMENT
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Select a document from your repository to ground the debate inquiry
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10 transition-colors"
            aria-label="Close document selector"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List of documents */}
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {documents.map((doc) => {
            const isSelected = doc.id === activeDocument.id;
            return (
              <div
                key={doc.id}
                onClick={() => {
                  onSelect(doc);
                  onClose();
                }}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-4 ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/40 shadow-sm ring-1 ring-indigo-500/30'
                    : 'border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-slate-900/40 hover:border-indigo-300 dark:hover:border-indigo-500/40 hover:bg-white dark:hover:bg-slate-900/70'
                }`}
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500 shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-mono font-bold text-slate-900 dark:text-white truncate">
                        {doc.name}
                      </h4>
                      {isSelected && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30">
                          CURRENT
                        </span>
                      )}
                    </div>
                    <div className="text-xs font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2 mt-0.5">
                      <span>{doc.pageCount} pages</span>
                      <span>•</span>
                      <span>{doc.fileType.toUpperCase()}</span>
                      <span>•</span>
                      <span>{doc.fileSize}</span>
                      <span>•</span>
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Ready</span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-1 mt-1 font-normal">
                      {doc.summary}
                    </p>
                  </div>
                </div>

                <div className="shrink-0">
                  {isSelected ? (
                    <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                      <Check className="w-4 h-4" />
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-mono font-medium hover:border-indigo-400 text-slate-700 dark:text-slate-300"
                    >
                      Select
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-200/80 dark:border-white/10 flex items-center justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-mono text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExistingDocumentPicker;

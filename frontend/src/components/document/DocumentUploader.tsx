import React, { useState, useRef } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  FileUp,
} from 'lucide-react';
import { useDocument } from '../../context/DocumentContext';

interface DocumentUploaderProps {
  onDocumentReady?: () => void;
  compact?: boolean;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  onDocumentReady,
  compact = false,
}) => {
  const {
    activeDocument,
    documents,
    uploadDocument,
    selectDocument,
    isProcessing,
    processingStage,
  } = useDocument();

  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setErrorMessage(null);
    const ext = file.name.split('.').pop()?.toLowerCase();
    const validExts = ['pdf', 'docx', 'txt'];

    if (!ext || !validExts.includes(ext)) {
      setErrorMessage('Supported formats: PDF, DOCX, and TXT. Other formats are planned soon.');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 25 MB limit for frontend processing.');
      return;
    }

    try {
      await uploadDocument(file);
      onDocumentReady?.();
    } catch {
      setErrorMessage('Failed to process document. Please try again.');
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const onDragLeave = () => {
    setIsDragOver(false);
  };

  const triggerPicker = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full space-y-3">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
          }
        }}
      />

      {/* Main Upload / Ready Surface */}
      {activeDocument && !isProcessing ? (
        <div className="relative rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-black/80 p-4 sm:p-5 backdrop-blur-xl shadow-lg transition-all">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-indigo-500/15 border border-indigo-400/30 flex items-center justify-center shrink-0 text-indigo-400 shadow-[0_0_20px_rgba(99,102,241,0.25)]">
                <FileText className="w-5 h-5 text-indigo-300" />
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm sm:text-base font-mono font-bold text-white tracking-wide truncate max-w-[240px] sm:max-w-[360px]">
                    {activeDocument.name}
                  </h4>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    <span>READY</span>
                  </span>
                </div>
                <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
                  <span>{activeDocument.pageCount} pages</span>
                  <span>•</span>
                  <span>{activeDocument.fileSize}</span>
                  <span>•</span>
                  <span className="text-indigo-300">{activeDocument.sections.length} extracted sections</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={triggerPicker}
                className="px-3 py-1.5 rounded-xl border border-white/10 hover:border-white/30 bg-white/5 hover:bg-white/10 text-xs font-mono text-slate-300 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer"
                title="Upload a different document"
              >
                <RefreshCw className="w-3 h-3 text-indigo-400" />
                <span>CHANGE DOCUMENT</span>
              </button>
            </div>
          </div>

          {/* Quick sample document switcher */}
          {!compact && documents.length > 1 && (
            <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap items-center gap-2 text-xs font-mono text-slate-400">
              <span className="text-[11px] text-slate-500">Sample Documents:</span>
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => selectDocument(doc.id)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] transition-all cursor-pointer ${
                    doc.id === activeDocument.id
                      ? 'bg-indigo-500/25 border border-indigo-400 text-indigo-200 font-bold'
                      : 'bg-black/30 border border-white/5 text-slate-400 hover:text-white hover:border-white/20'
                  }`}
                >
                  {doc.name}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Drag and Drop Zone */
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={triggerPicker}
          className={`relative rounded-3xl border-2 border-dashed p-6 sm:p-8 text-center transition-all cursor-pointer group ${
            isDragOver
              ? 'border-indigo-400 bg-indigo-950/40 scale-[1.01]'
              : 'border-slate-300 dark:border-white/15 bg-white/80 dark:bg-slate-950/60 hover:border-indigo-400/60 dark:hover:border-indigo-500/40 hover:bg-slate-50 dark:hover:bg-slate-900/60'
          } shadow-xl backdrop-blur-2xl`}
        >
          {isProcessing ? (
            <div className="py-4 space-y-3 flex flex-col items-center">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 border border-indigo-400/40 flex items-center justify-center text-indigo-400 animate-spin">
                <RefreshCw className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <span className="text-xs font-mono font-bold tracking-widest uppercase text-indigo-400 animate-pulse">
                  {processingStage}
                </span>
                <p className="text-[11px] font-mono text-slate-400">
                  Parsing sections, claims, and citation coordinates...
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="w-12 h-12 sm:w-14 sm:h-14 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-400/20 group-hover:border-indigo-400/40 group-hover:scale-105 flex items-center justify-center text-indigo-500 dark:text-indigo-400 transition-all shadow-[0_0_25px_rgba(99,102,241,0.15)]">
                <FileUp className="w-6 h-6 sm:w-7 sm:h-7" />
              </div>

              <div>
                <h3 className="text-base sm:text-lg font-black text-slate-900 dark:text-white tracking-tight">
                  DROP YOUR DOCUMENT HERE
                </h3>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                  Drag and drop a file, or click to browse. The uploaded document becomes the primary source of truth for the debate.
                </p>
              </div>

              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[11px] font-mono font-semibold text-slate-600 dark:text-slate-300">
                <span className="text-indigo-500 dark:text-indigo-400 font-bold">PDF</span>
                <span>•</span>
                <span className="text-indigo-500 dark:text-indigo-400 font-bold">DOCX</span>
                <span>•</span>
                <span className="text-indigo-500 dark:text-indigo-400 font-bold">TXT</span>
                <span className="text-slate-400 ml-1">(Up to 25 MB)</span>
              </div>
            </div>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-2 p-3 rounded-xl border border-rose-500/40 bg-rose-950/30 text-rose-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};

export default DocumentUploader;

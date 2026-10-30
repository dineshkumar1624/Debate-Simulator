import React, { useState, useRef } from 'react';
import {
  FileText,
  Upload,
  FolderOpen,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  X,
  FileUp,
} from 'lucide-react';
import { useDocument, validateDocumentFile } from '../../context/DocumentContext';
import { ExistingDocumentPicker } from './ExistingDocumentPicker';
import { DocumentMetadata } from '../../types/document';

interface DocumentSourceSectionProps {
  onDocumentChange?: (doc: DocumentMetadata) => void;
  className?: string;
}

export const DocumentSourceSection: React.FC<DocumentSourceSectionProps> = ({
  onDocumentChange,
  className = '',
}) => {
  const {
    activeDocument,
    selectDocument,
    uploadDocument,
    replaceActiveDocument,
    isProcessing,
    processingStage,
  } = useDocument();

  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [showUploader, setShowUploader] = useState(false);
  const [uploadMode, setUploadMode] = useState<'upload' | 'replace'>('upload');
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastAttemptedFile, setLastAttemptedFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleProcessFile = async (file: File) => {
    setErrorMessage(null);
    setLastAttemptedFile(file);

    const validation = validateDocumentFile(file);
    if (!validation.valid) {
      setErrorMessage(validation.error || 'Invalid file format.');
      return;
    }

    try {
      let doc: DocumentMetadata;
      if (uploadMode === 'replace') {
        doc = await replaceActiveDocument(file);
      } else {
        doc = await uploadDocument(file);
      }
      setShowUploader(false);
      setLastAttemptedFile(null);
      onDocumentChange?.(doc);
    } catch {
      setErrorMessage('Failed to process document. Please check the file and try again.');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleProcessFile(e.dataTransfer.files[0]);
    }
  };

  const openUploadTrigger = (mode: 'upload' | 'replace') => {
    setUploadMode(mode);
    setErrorMessage(null);
    setShowUploader(true);
  };

  const handleRetry = () => {
    if (lastAttemptedFile) {
      handleProcessFile(lastAttemptedFile);
    } else {
      fileInputRef.current?.click();
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleProcessFile(e.target.files[0]);
          }
        }}
      />

      {/* Main Document Source Card */}
      <div className="rounded-3xl border border-indigo-200/90 dark:border-indigo-500/30 bg-gradient-to-br from-indigo-50/90 via-white to-sky-50/60 dark:from-[#0a1026] dark:via-[#080d1e] dark:to-[#050814] p-5 sm:p-6 shadow-md backdrop-blur-2xl transition-all">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          {/* Document metadata display */}
          <div className="flex items-start sm:items-center gap-4 min-w-0">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 dark:bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0 text-indigo-600 dark:text-indigo-400 shadow-sm">
              <FileText className="w-6 h-6" />
            </div>

            <div className="min-w-0 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-bold tracking-widest uppercase text-indigo-700 dark:text-indigo-400">
                  DOCUMENT SOURCE
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Ready</span>
                </span>
              </div>

              <h2 className="text-base sm:text-lg font-mono font-black text-slate-900 dark:text-white truncate">
                {activeDocument.name}
              </h2>

              <div className="text-xs font-mono text-slate-600 dark:text-slate-400 flex flex-wrap items-center gap-2">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {activeDocument.pageCount} pages
                </span>
                <span>•</span>
                <span className="uppercase font-semibold">{activeDocument.fileType}</span>
                <span>•</span>
                <span>{activeDocument.fileSize}</span>
                <span>•</span>
                <span className="text-slate-500">{activeDocument.keyClaimsCount} verified claims</span>
              </div>
            </div>
          </div>

          {/* 3 Prominent Document Actions */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-200/70 dark:border-white/10">
            <button
              type="button"
              onClick={() => openUploadTrigger('upload')}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm shadow-indigo-600/25 transition-all cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload New Document</span>
            </button>

            <button
              type="button"
              onClick={() => setIsPickerOpen(true)}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono font-semibold bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-500 text-slate-800 dark:text-slate-200 shadow-sm transition-all cursor-pointer"
            >
              <FolderOpen className="w-3.5 h-3.5 text-indigo-500" />
              <span>Choose Existing Document</span>
            </button>

            <button
              type="button"
              onClick={() => openUploadTrigger('replace')}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono font-semibold bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:border-amber-400 dark:hover:border-amber-500 text-slate-800 dark:text-slate-200 shadow-sm transition-all cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-500" />
              <span>Replace Document</span>
            </button>
          </div>
        </div>
      </div>

      {/* Inline Document Uploader / Dropzone (Opens when clicking Upload or Replace) */}
      {showUploader && (
        <div className="rounded-3xl border border-indigo-300 dark:border-indigo-500/40 bg-white dark:bg-[#070b18] p-6 shadow-xl backdrop-blur-2xl animate-fadeIn space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-white/10">
            <div className="flex items-center gap-2">
              <FileUp className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                {uploadMode === 'replace' ? 'REPLACE CURRENT DOCUMENT' : 'UPLOAD NEW DOCUMENT'}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setShowUploader(false)}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white"
              aria-label="Close uploader"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Drag & Drop Area */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onClick={() => fileInputRef.current?.click()}
            className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all cursor-pointer ${
              isDragOver
                ? 'border-indigo-500 bg-indigo-50/80 dark:bg-indigo-950/40 scale-[1.01]'
                : 'border-slate-300 dark:border-slate-700 hover:border-indigo-400 bg-slate-50/60 dark:bg-slate-900/50 hover:bg-indigo-50/30'
            }`}
          >
            {isProcessing ? (
              <div className="py-4 space-y-3 flex flex-col items-center">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 border border-indigo-400/40 flex items-center justify-center text-indigo-500 animate-spin">
                  <RefreshCw className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <span className="text-xs font-mono font-bold tracking-widest uppercase text-indigo-600 dark:text-indigo-400 animate-pulse">
                    {processingStage}
                  </span>
                  <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                    Extracting structural claims and citation references...
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="w-12 h-12 mx-auto rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
                  <Upload className="w-6 h-6" />
                </div>

                <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white font-mono">
                  DRAG & DROP OR CLICK TO UPLOAD
                </h3>

                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                  {uploadMode === 'replace'
                    ? `Select a replacement document for "${activeDocument.name}".`
                    : 'Add a new document to the workspace repository.'}
                </p>

                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-[10px] font-mono font-semibold text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  <span className="text-indigo-600 dark:text-indigo-400 font-bold">PDF</span>
                  <span>•</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-bold">DOCX</span>
                  <span>•</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-bold">TXT</span>
                  <span className="text-slate-400 ml-1">(Up to 25 MB)</span>
                </div>
              </div>
            )}
          </div>

          {/* Error Message & Retry */}
          {errorMessage && (
            <div className="flex items-center justify-between gap-3 p-3.5 rounded-xl border border-rose-300 dark:border-rose-900/60 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 text-xs font-mono">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                <span>{errorMessage}</span>
              </div>
              <button
                type="button"
                onClick={handleRetry}
                className="px-2.5 py-1 rounded-lg bg-rose-600 text-white text-[11px] font-bold hover:bg-rose-500 transition-colors shrink-0"
              >
                Retry
              </button>
            </div>
          )}

          {/* Frontend Preview Transparent Notice */}
          <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 text-center">
            Frontend preview · Live document extraction is simulated for preview demonstration.
          </p>
        </div>
      )}

      {/* Existing Document Picker Modal */}
      <ExistingDocumentPicker
        isOpen={isPickerOpen}
        onClose={() => setIsPickerOpen(false)}
        onSelect={(doc) => {
          selectDocument(doc.id);
          onDocumentChange?.(doc);
        }}
      />
    </div>
  );
};

export default DocumentSourceSection;

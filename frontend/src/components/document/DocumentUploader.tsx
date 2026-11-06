import React, { useState, useRef, useEffect } from 'react';
import {
  FileText,
  Image as ImageIcon,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  FileUp,
  Camera,
  Sparkles,
} from 'lucide-react';
import { useDocument } from '../../context/DocumentContext';
import { debateApi } from '../../services/api';

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

  const [sourceType, setSourceType] = useState<'document' | 'image'>('document');
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync sourceType tab with active document type
  useEffect(() => {
    if (activeDocument) {
      const isImg = ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(activeDocument.fileType.toLowerCase());
      setSourceType(isImg ? 'image' : 'document');
    }
  }, [activeDocument?.id, activeDocument?.fileType]);

  const handleFile = async (file: File) => {
    setErrorMessage(null);
    const ext = file.name.split('.').pop()?.toLowerCase();
    const docExts = ['pdf', 'docx', 'txt'];
    const imgExts = ['png', 'jpg', 'jpeg', 'webp', 'bmp'];
    const validExts = sourceType === 'image' ? imgExts : docExts;

    if (!ext || !validExts.includes(ext)) {
      if (sourceType === 'image') {
        setErrorMessage(`Invalid image format. Supported: ${imgExts.map(e => e.toUpperCase()).join(', ')}.`);
      } else {
        setErrorMessage('Supported formats: PDF, DOCX, and TXT.');
      }
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 25 MB limit.');
      return;
    }

    if (sourceType === 'image' || imgExts.includes(ext)) {
      const preview = URL.createObjectURL(file);
      setLocalPreviewUrl(preview);
    }

    try {
      await uploadDocument(file);
      onDocumentReady?.();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to process file. Please try again.');
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

  const isCurrentActiveAnImage = activeDocument && ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(activeDocument.fileType.toLowerCase());
  const activeImageUrl = isCurrentActiveAnImage ? debateApi.getDocumentFileUrl(activeDocument.id) : localPreviewUrl;

  return (
    <div className="w-full space-y-3">
      {/* Source Type Selector Tabs */}
      <div className="flex items-center justify-between gap-2 p-1.5 rounded-2xl bg-slate-100/90 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 backdrop-blur-xl shadow-xs">
        <div className="flex items-center gap-1.5 w-full">
          <button
            type="button"
            onClick={() => {
              setSourceType('document');
              setErrorMessage(null);
            }}
            className={`flex-1 py-2 px-3 rounded-xl text-xs font-mono font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-2 cursor-pointer ${
              sourceType === 'document'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-white dark:hover:bg-white/5'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Document</span>
            <span className="text-[10px] opacity-80 font-normal">(PDF, DOCX, TXT)</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setSourceType('image');
              setErrorMessage(null);
            }}
            className={`flex-1 py-2 px-3 rounded-xl text-xs font-mono font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-2 cursor-pointer ${
              sourceType === 'image'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-white dark:hover:bg-white/5'
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            <span>Image</span>
            <span className="text-[10px] opacity-80 font-normal">(JPG, PNG, WEBP, BMP)</span>
          </button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={sourceType === 'image' ? 'image/jpeg,image/png,image/webp,image/bmp' : '.pdf,.docx,.txt'}
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
          }
        }}
      />

      {/* Main Upload / Ready Surface */}
      {activeDocument && !isProcessing ? (
        <div className={`relative rounded-3xl border p-4 sm:p-5 backdrop-blur-xl shadow-sm transition-all ${
          isCurrentActiveAnImage
            ? 'border-emerald-300 dark:border-emerald-500/30 bg-gradient-to-br from-emerald-50/80 via-white to-teal-50/40 dark:from-emerald-950/40 dark:via-slate-900/60 dark:to-black/80'
            : 'border-indigo-300 dark:border-indigo-500/30 bg-gradient-to-br from-indigo-50/80 via-white to-sky-50/40 dark:from-indigo-950/40 dark:via-slate-900/60 dark:to-black/80'
        }`}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              {isCurrentActiveAnImage && activeImageUrl ? (
                <div className="relative w-14 h-14 rounded-xl border border-emerald-400/40 overflow-hidden shrink-0 bg-slate-100 dark:bg-black/50 shadow-md">
                  <img
                    src={activeImageUrl}
                    alt={activeDocument.name}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-1">
                    <span className="text-[9px] font-mono font-bold text-emerald-300 uppercase">
                      {activeDocument.fileType}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="w-11 h-11 rounded-2xl bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-400/30 flex items-center justify-center shrink-0 text-indigo-600 dark:text-indigo-400 shadow-xs">
                  <FileText className="w-5 h-5 text-indigo-600 dark:text-indigo-300" />
                </div>
              )}

              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm sm:text-base font-mono font-bold text-slate-900 dark:text-white tracking-wide truncate max-w-[240px] sm:max-w-[360px]">
                    {activeDocument.name}
                  </h4>
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold flex items-center gap-1 ${
                    isCurrentActiveAnImage
                      ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30'
                      : 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30'
                  }`}>
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    <span>{isCurrentActiveAnImage ? 'IMAGE READY' : 'DOCUMENT READY'}</span>
                  </span>
                </div>
                <div className="text-xs font-mono text-slate-600 dark:text-slate-400 flex items-center gap-2 flex-wrap">
                  {isCurrentActiveAnImage ? (
                    <>
                      <span className="text-emerald-700 dark:text-emerald-300 uppercase font-semibold">{activeDocument.fileType} Image</span>
                      <span>•</span>
                      <span>{activeDocument.fileSize}</span>
                      <span>•</span>
                      <span className="text-emerald-700 dark:text-emerald-300 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        <span>{activeDocument.evidencePointsCount || 4} Visual Evidence Items</span>
                      </span>
                    </>
                  ) : (
                    <>
                      <span>{activeDocument.pageCount} pages</span>
                      <span>•</span>
                      <span>{activeDocument.fileSize}</span>
                      <span>•</span>
                      <span className="text-indigo-700 dark:text-indigo-300 font-medium">{activeDocument.sections?.length || 0} extracted sections</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={triggerPicker}
                className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/30 bg-white dark:bg-white/5 hover:bg-slate-50 dark:hover:bg-white/10 text-xs font-mono text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                title={isCurrentActiveAnImage ? "Upload a different image" : "Upload a different document"}
              >
                <RefreshCw className={`w-3 h-3 ${isCurrentActiveAnImage ? 'text-emerald-600 dark:text-emerald-400' : 'text-indigo-600 dark:text-indigo-400'}`} />
                <span>{isCurrentActiveAnImage ? 'CHANGE IMAGE' : 'CHANGE DOCUMENT'}</span>
              </button>
            </div>
          </div>

          {/* Quick sample document switcher */}
          {!compact && documents.length > 1 && (
            <div className="mt-3 pt-3 border-t border-slate-200/80 dark:border-white/10 flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">Available Sources:</span>
              {documents.map((doc) => {
                const isDocImg = ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(doc.fileType.toLowerCase());
                const isSelected = doc.id === activeDocument.id;
                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => selectDocument(doc.id)}
                    className={`px-2.5 py-1 rounded-lg text-[10px] transition-all cursor-pointer flex items-center gap-1 ${
                      isSelected
                        ? isDocImg
                          ? 'bg-emerald-100 dark:bg-emerald-500/25 border border-emerald-400 text-emerald-800 dark:text-emerald-200 font-bold shadow-xs'
                          : 'bg-indigo-100 dark:bg-indigo-500/25 border border-indigo-400 text-indigo-800 dark:text-indigo-200 font-bold shadow-xs'
                        : 'bg-white dark:bg-black/30 border border-slate-200/90 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-indigo-300 dark:hover:border-white/20 shadow-xs'
                    }`}
                  >
                    {isDocImg ? <ImageIcon className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" /> : <FileText className="w-2.5 h-2.5 text-indigo-600 dark:text-indigo-400" />}
                    <span>{doc.name}</span>
                  </button>
                );
              })}
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
          className={`relative rounded-3xl border-2 border-dashed p-6 sm:p-8 text-center transition-all cursor-pointer group shadow-sm backdrop-blur-2xl ${
            isDragOver
              ? sourceType === 'image'
                ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/40 scale-[1.01]'
                : 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 scale-[1.01]'
              : sourceType === 'image'
                ? 'border-slate-300 dark:border-white/15 bg-white/95 dark:bg-slate-950/60 hover:border-emerald-400/60 dark:hover:border-emerald-500/40 hover:bg-emerald-50/20 dark:hover:bg-slate-900/60'
                : 'border-slate-300 dark:border-white/15 bg-white/95 dark:bg-slate-950/60 hover:border-indigo-400/60 dark:hover:border-indigo-500/40 hover:bg-indigo-50/20 dark:hover:bg-slate-900/60'
          }`}
        >
          {isProcessing ? (
            <div className="py-4 space-y-3 flex flex-col items-center">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center animate-spin ${
                sourceType === 'image'
                  ? 'bg-emerald-500/20 border border-emerald-400/40 text-emerald-600 dark:text-emerald-400'
                  : 'bg-indigo-500/20 border border-indigo-400/40 text-indigo-600 dark:text-indigo-400'
              }`}>
                <RefreshCw className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <span className={`text-xs font-mono font-bold tracking-widest uppercase animate-pulse ${
                  sourceType === 'image' ? 'text-emerald-600 dark:text-emerald-400' : 'text-indigo-600 dark:text-indigo-400'
                }`}>
                  {processingStage}
                </span>
                <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  {sourceType === 'image'
                    ? 'Running RapidOCR text extraction, Qwen visual analysis, and vector indexing...'
                    : 'Parsing sections, claims, and citation coordinates...'}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className={`w-12 h-12 sm:w-14 sm:h-14 mx-auto rounded-2xl flex items-center justify-center transition-all ${
                sourceType === 'image'
                  ? 'bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-400/20 group-hover:border-emerald-400/40 group-hover:scale-105 text-emerald-600 dark:text-emerald-400 shadow-sm'
                  : 'bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-400/20 group-hover:border-indigo-400/40 group-hover:scale-105 text-indigo-600 dark:text-indigo-400 shadow-sm'
              }`}>
                {sourceType === 'image' ? <Camera className="w-6 h-6 sm:w-7 sm:h-7" /> : <FileUp className="w-6 h-6 sm:w-7 sm:h-7" />}
              </div>

              <div>
                <h3 className="text-base sm:text-lg font-black text-slate-900 dark:text-white tracking-tight">
                  {sourceType === 'image' ? 'DROP YOUR IMAGE HERE' : 'DROP YOUR DOCUMENT HERE'}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1 max-w-md mx-auto">
                  {sourceType === 'image'
                    ? 'Drag and drop an image (charts, diagrams, infographics, figures). Analyzed by Qwen2.5-VL and RapidOCR.'
                    : 'Drag and drop a file, or click to browse. The uploaded document becomes the primary source of truth for the debate.'}
                </p>
              </div>

              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[11px] font-mono font-semibold text-slate-600 dark:text-slate-300 shadow-2xs">
                {sourceType === 'image' ? (
                  <>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">JPG</span>
                    <span>•</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">PNG</span>
                    <span>•</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">WEBP</span>
                    <span>•</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">BMP</span>
                    <span className="text-slate-500 dark:text-slate-400 ml-1">(Up to 25 MB)</span>
                  </>
                ) : (
                  <>
                    <span className="text-indigo-600 dark:text-indigo-400 font-bold">PDF</span>
                    <span>•</span>
                    <span className="text-indigo-600 dark:text-indigo-400 font-bold">DOCX</span>
                    <span>•</span>
                    <span className="text-indigo-600 dark:text-indigo-400 font-bold">TXT</span>
                    <span className="text-slate-500 dark:text-slate-400 ml-1">(Up to 25 MB)</span>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-2 p-3 rounded-xl border border-rose-200 dark:border-rose-500/40 bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 text-xs font-mono shadow-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};

export default DocumentUploader;

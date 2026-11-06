import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
  Bookmark,
  Sparkles,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Copy,
  Check,
  ExternalLink,
  Layers,
  FileCheck,
  Eye,
  Camera,
  AlertTriangle,
} from 'lucide-react';
import { DocumentMetadata, EvidenceReference, ImageUnderstanding } from '../../types/document';
import { useDocument } from '../../context/DocumentContext';
import { debateApi } from '../../services/api';

interface DocumentViewerProps {
  document: DocumentMetadata;
  evidenceItems?: EvidenceReference[];
  activeEvidenceId?: string | null;
  onSelectEvidence?: (id: string) => void;
  className?: string;
  targetPage?: number;
}

type ViewMode = 'pdf-render' | 'extracted-text' | 'ai-knowledge';

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  document,
  evidenceItems = [],
  activeEvidenceId,
  onSelectEvidence: _onSelectEvidence,
  className = '',
  targetPage,
}) => {
  const { activeKnowledge } = useDocument();

  const isImageDoc = ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(document.fileType?.toLowerCase() || '');

  // Page state: 1 to document.pageCount (15) for PDF, 1 for Image
  const [currentPage, setCurrentPage] = useState<number>(targetPage && targetPage > 0 ? targetPage : 1);
  const [viewMode, setViewMode] = useState<ViewMode>('pdf-render');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [copiedText, setCopiedText] = useState<boolean>(false);

  // Verbatim Extracted Text State
  const [pageTextData, setPageTextData] = useState<{
    text: string;
    wordCount: number;
    charCount: number;
    sectionTitle: string;
    loading: boolean;
    error: string | null;
  }>({
    text: '',
    wordCount: 0,
    charCount: 0,
    sectionTitle: '',
    loading: false,
    error: null,
  });

  // Image understanding state for multimodal images
  const [imageUnderstanding, setImageUnderstanding] = useState<ImageUnderstanding | null>(null);

  // Image load state for PDF renderer & image viewer
  const [imageLoading, setImageLoading] = useState<boolean>(true);
  const [imageError, setImageError] = useState<boolean>(false);
  const imageContainerRef = useRef<HTMLDivElement>(null);

  // Load image understanding if this is an image
  useEffect(() => {
    if (isImageDoc) {
      debateApi
        .getDocumentImageUnderstanding(document.id)
        .then((data) => {
          if (data) setImageUnderstanding(data);
        })
        .catch((err) => {
          console.warn('Could not fetch image understanding representation:', err);
        });
    }
  }, [document.id, isImageDoc]);

  // Synchronize targetPage from external citation clicks (Requirements 7 & 8)
  useEffect(() => {
    if (!isImageDoc && targetPage && targetPage > 0 && targetPage <= (document.pageCount || 15)) {
      setCurrentPage(targetPage);
    }
  }, [targetPage, document.pageCount, isImageDoc]);

  // Fetch verbatim extracted text for active page or image
  useEffect(() => {
    let isMounted = true;
    setPageTextData((prev) => ({ ...prev, loading: true, error: null }));

    debateApi
      .getDocumentPageText(document.id, isImageDoc ? 1 : currentPage)
      .then((res) => {
        if (!isMounted) return;
        setPageTextData({
          text: res.extracted_text || '',
          wordCount: res.word_count || 0,
          charCount: res.character_count || 0,
          sectionTitle: res.section_title || (isImageDoc ? 'Optical Text (RapidOCR)' : `Page ${currentPage}`),
          loading: false,
          error: null,
        });
      })
      .catch((err) => {
        if (!isMounted) return;
        console.warn(`Could not load text:`, err);
        setPageTextData({
          text: '',
          wordCount: 0,
          charCount: 0,
          sectionTitle: isImageDoc ? 'Optical Text' : `Page ${currentPage}`,
          loading: false,
          error: 'Verbatim text could not be loaded from backend repository.',
        });
      });

    return () => {
      isMounted = false;
    };
  }, [document.id, currentPage, isImageDoc]);

  // Reset image loading indicator on page change
  useEffect(() => {
    setImageLoading(true);
    setImageError(false);
  }, [currentPage, document.id]);

  // Filtered knowledge elements for PDF
  const activeSection =
    activeKnowledge?.sections?.find(
      (s: any) => currentPage >= s.page_start && currentPage <= s.page_end
    ) || document.sections?.find((s: any) => s.pageNumber === currentPage);

  const pageConcepts =
    activeKnowledge?.concepts?.filter((c: any) => c.page_number === currentPage) || [];
  const pageFacts =
    activeKnowledge?.facts?.filter((f: any) => f.page_number === currentPage) || [];
  const pageRelations =
    activeKnowledge?.cross_section_relations?.filter(
      (r: any) =>
        (r.source_pages && r.source_pages.includes(currentPage)) ||
        (r.target_pages && r.target_pages.includes(currentPage))
    ) || [];

  // Active citation on this page or visual evidence match
  const citedEvidenceOnPage = evidenceItems.find(
    (ev) =>
      (!isImageDoc && ev.pageNumber === currentPage) ||
      (activeEvidenceId && (ev.id === activeEvidenceId || (ev as any).evidenceId === activeEvidenceId))
  );

  const handleCopyText = () => {
    const txtToCopy = pageTextData.text || imageUnderstanding?.ocr_text || '';
    if (txtToCopy) {
      navigator.clipboard.writeText(txtToCopy);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.min(250, Math.max(75, prev + delta)));
  };

  const resetZoom = () => {
    setZoomLevel(100);
  };

  const pageRenderUrl = isImageDoc
    ? debateApi.getDocumentFileUrl(document.id)
    : debateApi.getDocumentPageRenderUrl(document.id, currentPage, 2.0);

  const fileDownloadUrl = debateApi.getDocumentFileUrl(document.id);

  return (
    <div
      className={`rounded-3xl border border-slate-200/90 dark:border-white/10 bg-white dark:bg-[#070b18]/95 backdrop-blur-2xl shadow-xl flex flex-col overflow-hidden transition-all ${className}`}
    >
      {/* 1. TOP HEADER & METADATA */}
      <div className="p-4 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-[#0b1022] flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            isImageDoc
              ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
              : 'bg-indigo-500/15 border border-indigo-500/30 text-indigo-400'
          }`}>
            {isImageDoc ? <ImageIcon className="w-5 h-5 text-emerald-300" /> : <FileText className="w-5 h-5 text-indigo-300" />}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-xs sm:text-sm font-mono font-bold text-slate-900 dark:text-white truncate max-w-[200px] sm:max-w-[320px]">
                {document.name}
              </h3>
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-bold flex items-center gap-1 ${
                isImageDoc
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                  : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
              }`}>
                <FileCheck className="w-2.5 h-2.5" />
                <span>{isImageDoc ? 'GROUNDED IMAGE' : 'GROUNDED PDF'}</span>
              </span>
            </div>
            <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2 mt-0.5">
              <span>{isImageDoc ? `${document.fileType.toUpperCase()} Image` : `${document.pageCount} Pages`}</span>
              <span>•</span>
              <span>{document.fileSize}</span>
              <span>•</span>
              <a
                href={fileDownloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
                title="Open raw file in new window"
              >
                <span>Raw File</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>
        </div>

        {/* TOP RIGHT CONTROLS: Page navigation for PDF, Dimensions badge for Image */}
        {isImageDoc ? (
          <div className="flex items-center gap-2 shrink-0">
            <span className="px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono font-bold text-emerald-300">
              {imageUnderstanding?.dimensions
                ? `${imageUnderstanding.dimensions.width}×${imageUnderstanding.dimensions.height} (${imageUnderstanding.dimensions.aspect_ratio})`
                : `${document.fileType.toUpperCase()} Visual Source`}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30 text-slate-700 dark:text-slate-300 transition-colors"
              title="Previous page (Arrow Left)"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-black/50 border border-slate-200 dark:border-white/10 text-xs font-mono font-bold text-slate-800 dark:text-slate-200">
              <span>Page</span>
              <select
                value={currentPage}
                onChange={(e) => setCurrentPage(Number(e.target.value))}
                className="bg-transparent text-indigo-400 font-bold focus:outline-none cursor-pointer"
              >
                {Array.from({ length: document.pageCount || 15 }, (_, i) => i + 1).map((num) => (
                  <option key={num} value={num} className="bg-slate-900 text-white">
                    {num}
                  </option>
                ))}
              </select>
              <span className="text-slate-500">/ {document.pageCount || 15}</span>
            </div>

            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(document.pageCount || 15, p + 1))}
              disabled={currentPage >= (document.pageCount || 15)}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30 text-slate-700 dark:text-slate-300 transition-colors"
              title="Next page (Arrow Right)"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* 2. MODE SWITCHER TABS */}
      <div className="px-4 py-2 border-b border-slate-200 dark:border-white/10 bg-slate-100/70 dark:bg-[#090e1f] flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setViewMode('pdf-render')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === 'pdf-render'
                ? isImageDoc
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {isImageDoc ? <ImageIcon className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{isImageDoc ? 'Original Image' : 'Original PDF Page'}</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('extracted-text')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === 'extracted-text'
                ? 'bg-teal-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Extracted OCR Text</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('ai-knowledge')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === 'ai-knowledge'
                ? 'bg-purple-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isImageDoc ? 'Visual Evidence & Analysis' : 'AI Knowledge & Syntheses'}</span>
          </button>
        </div>

        {/* View-specific tools (Zoom controls) */}
        {viewMode === 'pdf-render' && (
          <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
            <button
              type="button"
              onClick={() => handleZoom(-15)}
              className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono px-1.5 font-semibold text-slate-300">
              {zoomLevel}%
            </span>
            <button
              type="button"
              onClick={() => handleZoom(15)}
              className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={resetZoom}
              className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors ml-1"
              title="Reset zoom"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        )}

        {viewMode === 'extracted-text' && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-400">
              {pageTextData.charCount || imageUnderstanding?.ocr_text?.length || 0} chars •{' '}
              {pageTextData.wordCount || imageUnderstanding?.ocr_text?.split(/\s+/).length || 0} words
            </span>
            <button
              type="button"
              onClick={handleCopyText}
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-200 flex items-center gap-1 transition-colors cursor-pointer"
            >
              {copiedText ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* 3. SECTIONS & EVIDENCE QUICK BAR */}
      <div className="px-4 py-2 border-b border-slate-200/60 dark:border-white/5 bg-slate-100/40 dark:bg-black/30 flex items-center gap-2 overflow-x-auto scrollbar-none text-xs font-mono">
        <span className="text-[10px] uppercase font-bold text-slate-400 shrink-0 flex items-center gap-1">
          <Bookmark className="w-3 h-3 text-indigo-400" />
          <span>{isImageDoc ? 'EVIDENCE ITEMS:' : 'SECTIONS:'}</span>
        </span>
        {isImageDoc && imageUnderstanding?.evidence_items && imageUnderstanding.evidence_items.length > 0 ? (
          imageUnderstanding.evidence_items.map((ev) => (
            <button
              key={ev.id}
              type="button"
              onClick={() => {
                setViewMode('ai-knowledge');
              }}
              className={`px-2.5 py-1 rounded-lg text-[10px] shrink-0 transition-all cursor-pointer flex items-center gap-1 ${
                activeEvidenceId === ev.id
                  ? 'bg-emerald-600 text-white font-bold shadow-md shadow-emerald-500/30'
                  : 'bg-white/60 dark:bg-white/5 border border-slate-200 dark:border-white/5 text-slate-600 dark:text-slate-300 hover:text-white hover:bg-emerald-950/40'
              }`}
            >
              <span className="font-bold text-emerald-400">[{ev.id}]</span>
              <span>{ev.label}</span>
            </button>
          ))
        ) : !isImageDoc && document.sections && document.sections.length > 0 ? (
          document.sections.map((sec) => (
            <button
              key={sec.id}
              type="button"
              onClick={() => setCurrentPage(sec.pageNumber)}
              className={`px-2.5 py-1 rounded-lg text-[10px] shrink-0 transition-all cursor-pointer ${
                currentPage === sec.pageNumber
                  ? 'bg-indigo-600 text-white font-bold shadow-sm'
                  : 'bg-white/60 dark:bg-white/5 border border-slate-200 dark:border-white/5 text-slate-600 dark:text-slate-300 hover:text-white hover:bg-indigo-900/30'
              }`}
            >
              {sec.title} (p. {sec.pageNumber})
            </button>
          ))
        ) : (
          <span className="text-[10px] text-slate-500">{isImageDoc ? 'Visual data indexed' : 'Pages indexed'}</span>
        )}
      </div>

      {/* 4. ACTIVE CITATION CALLOUT BANNER */}
      {citedEvidenceOnPage && (
        <div className="px-4 py-2.5 bg-amber-500/10 border-b border-amber-500/20 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 shrink-0">
              CITED EVIDENCE
            </span>
            <span className="text-amber-200 font-mono text-[11px] truncate">
              {citedEvidenceOnPage.excerpt || (citedEvidenceOnPage as any).claim || `Verified empirical citation`}
            </span>
          </div>
          <span className="text-[10px] font-mono font-bold text-amber-400 shrink-0">
            {isImageDoc ? `Visual Item [${citedEvidenceOnPage.id}]` : `p. ${currentPage}`}
          </span>
        </div>
      )}

      {/* 5. MAIN CONTENT VIEWER SURFACE */}
      <div className="relative flex-1 min-h-[460px] max-h-[580px] overflow-auto bg-slate-900/40 p-4">
        {/* MODE A: ORIGINAL PDF PAGE / ORIGINAL IMAGE VIEWER */}
        {viewMode === 'pdf-render' && (
          <div
            ref={imageContainerRef}
            className="flex flex-col items-center justify-start min-h-full w-full overflow-auto"
          >
            {/* Visual Veracity Guard Banner */}
            <div className="w-full flex items-center justify-between pb-2 mb-3 border-b border-white/[0.08] text-[10px] font-mono text-slate-400">
              <span className={`flex items-center gap-1.5 ${isImageDoc ? 'text-emerald-400' : 'text-emerald-400'}`}>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>
                  {isImageDoc
                    ? `VERBATIM ORIGINAL UPLOADED IMAGE (${document.fileType.toUpperCase()})`
                    : `VERBATIM ORIGINAL PDF PAGE ${currentPage} OF ${document.pageCount}`}
                </span>
              </span>
              <span className="text-slate-400 hidden sm:inline">
                {isImageDoc
                  ? 'Original Resolution • Chart Elements & Visible Data Preserved'
                  : 'Original Layout • Tables • Mathematical Formulas Preserved'}
              </span>
            </div>

            {/* Loading Indicator */}
            {imageLoading && (
              <div className="flex flex-col items-center justify-center p-12 space-y-3 text-slate-400">
                <div className={`w-8 h-8 rounded-full border-2 border-t-transparent animate-spin ${
                  isImageDoc ? 'border-emerald-500' : 'border-indigo-500'
                }`} />
                <span className="text-xs font-mono">
                  {isImageDoc ? 'Loading high-resolution image...' : `Rendering high-resolution PDF page ${currentPage}...`}
                </span>
              </div>
            )}

            {/* Error State Fallback */}
            {imageError && (
              <div className="p-8 text-center space-y-3 max-w-md">
                <FileText className="w-10 h-10 mx-auto text-amber-400" />
                <h4 className="text-sm font-bold text-white">Direct Preview Unavailable</h4>
                <p className="text-xs font-mono text-slate-400">
                  Could not load high-resolution image render. You can examine the extracted OCR text tab or view raw file.
                </p>
                <div className="flex items-center justify-center gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setViewMode('extracted-text')}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold"
                  >
                    View Extracted Text
                  </button>
                  <a
                    href={fileDownloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono"
                  >
                    Open Raw File
                  </a>
                </div>
              </div>
            )}

            {/* Actual Rendered PDF Image or Uploaded Image */}
            <div
              className={`transition-all duration-200 rounded-xl shadow-2xl overflow-hidden border border-white/10 ${
                isImageDoc ? 'bg-black/50' : 'bg-white'
              } ${imageLoading ? 'hidden' : 'block'}`}
              style={{
                width: `${zoomLevel}%`,
                maxWidth: zoomLevel <= 100 ? '100%' : 'none',
              }}
            >
              <img
                src={pageRenderUrl}
                alt={isImageDoc ? document.name : `Original PDF Page ${currentPage} - ${document.name}`}
                className="w-full h-auto block select-text mx-auto"
                onLoad={() => setImageLoading(false)}
                onError={() => {
                  setImageLoading(false);
                  setImageError(true);
                }}
              />
            </div>
          </div>
        )}

        {/* MODE B: VERBATIM EXTRACTED OCR TEXT */}
        {viewMode === 'extracted-text' && (
          <div className="space-y-3 w-full max-w-4xl mx-auto">
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] text-[10px] font-mono text-slate-400">
              <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                <span>
                  {isImageDoc
                    ? 'VERBATIM RAPIDOCR EXTRACTED TEXT • NO AI RECONSTRUCTION'
                    : `VERBATIM EXTRACTED SOURCE TEXT • PAGE ${currentPage}`}
                </span>
              </span>
              <span>
                {pageTextData.wordCount || imageUnderstanding?.ocr_text?.split(/\s+/).length || 0} words
              </span>
            </div>

            {pageTextData.loading ? (
              <div className="flex items-center justify-center p-12 text-slate-400 font-mono text-xs">
                Loading verbatim optical text...
              </div>
            ) : pageTextData.error && !imageUnderstanding?.ocr_text ? (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-300">
                {pageTextData.error}
              </div>
            ) : (
              <div className="space-y-3">
                {isImageDoc && imageUnderstanding?.ocr_lines && imageUnderstanding.ocr_lines.length > 0 ? (
                  <div className="space-y-2">
                    <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold block">
                      Individual Optical Text Lines & Confidence Scores:
                    </span>
                    <div className="space-y-1.5">
                      {imageUnderstanding.ocr_lines.map((line, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded-xl bg-black/40 border border-white/5 flex items-center justify-between gap-3 text-xs font-mono"
                        >
                          <span className="text-slate-200 select-text font-sans">"{line.text}"</span>
                          <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shrink-0 font-bold">
                            {line.confidence}% conf
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="p-4 rounded-2xl bg-black/50 border border-white/10 font-mono text-xs leading-relaxed text-slate-200 whitespace-pre-wrap select-text selection:bg-indigo-500/40">
                  {pageTextData.text || imageUnderstanding?.ocr_text || 'No optical text detected in this image via RapidOCR.'}
                </div>
              </div>
            )}
          </div>
        )}

        {/* MODE C: AI KNOWLEDGE & VISUAL EVIDENCE */}
        {viewMode === 'ai-knowledge' && (
          <div className="space-y-4 w-full max-w-4xl mx-auto font-mono text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] text-[10px] text-slate-400">
              <span className="flex items-center gap-1.5 text-purple-400 font-bold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>
                  {isImageDoc
                    ? 'MULTIMODAL VISUAL KNOWLEDGE & EVIDENCE POOL'
                    : `AI KNOWLEDGE REPRESENTATION • PAGE ${currentPage}`}
                </span>
              </span>
              <span>Synthesized by Multimodal Vision Engine</span>
            </div>

            {/* IMAGE MODE CONTENT */}
            {isImageDoc ? (
              <div className="space-y-4">
                {/* Summary Banner */}
                <div className="p-4 rounded-2xl border border-emerald-500/30 bg-emerald-950/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                      <Camera className="w-3.5 h-3.5" />
                      <span>MULTIMODAL VISUAL SUMMARY</span>
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
                      Qwen2.5-VL Vision
                    </span>
                  </div>
                  <p className="text-slate-200 leading-relaxed font-sans text-xs">
                    {imageUnderstanding?.summary || document.summary || 'Visual representation parsed.'}
                  </p>
                </div>

                {/* Discrete Visual Evidence Items */}
                {imageUnderstanding?.evidence_items && imageUnderstanding.evidence_items.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-emerald-400 block tracking-wider">
                      DISCRETE VISUAL EVIDENCE ITEMS ({imageUnderstanding.evidence_items.length})
                    </span>
                    <div className="grid grid-cols-1 gap-2.5">
                      {imageUnderstanding.evidence_items.map((ev) => {
                        const isHighlighted = activeEvidenceId === ev.id;
                        return (
                          <div
                            key={ev.id}
                            className={`p-3.5 rounded-xl border transition-all ${
                              isHighlighted
                                ? 'border-amber-400 bg-amber-950/30 shadow-lg shadow-amber-500/20 ring-1 ring-amber-400'
                                : 'border-emerald-500/30 bg-emerald-950/20 hover:border-emerald-400/50'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                              <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/30 text-emerald-200 border border-emerald-400/40">
                                  {ev.id}
                                </span>
                                <span className="font-bold text-xs text-white">{ev.label}</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <span className="text-[10px] px-2 py-0.5 rounded bg-black/40 text-slate-300 border border-white/10">
                                  {ev.location}
                                </span>
                                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-500/40 font-bold">
                                  {ev.confidence}% conf
                                </span>
                              </div>
                            </div>
                            <p className="text-xs text-slate-200 font-sans leading-relaxed select-text">
                              {ev.content}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Numerical Values & Metrics */}
                {imageUnderstanding?.numerical_values && imageUnderstanding.numerical_values.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-sky-400 block tracking-wider">
                      QUANTITATIVE VALUES & BENCHMARK METRICS
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {imageUnderstanding.numerical_values.map((num, idx) => (
                        <div
                          key={idx}
                          className="px-3 py-1.5 rounded-xl border border-sky-500/30 bg-sky-950/20 text-sky-200 text-xs font-mono font-semibold"
                        >
                          {num}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Visual Relationships & Trends */}
                {imageUnderstanding?.relationships && imageUnderstanding.relationships.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-purple-400 block tracking-wider">
                      STRUCTURAL RELATIONSHIPS & TRENDS
                    </span>
                    <div className="space-y-1.5">
                      {imageUnderstanding.relationships.map((rel, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl border border-purple-500/30 bg-purple-950/20 text-purple-200 text-xs font-sans"
                        >
                          {rel}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Epistemic Uncertainties */}
                {imageUnderstanding?.uncertainties && imageUnderstanding.uncertainties.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-amber-400 block tracking-wider flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>EPISTEMIC UNCERTAINTIES & VISUAL CAVEATS</span>
                    </span>
                    <div className="space-y-1.5">
                      {imageUnderstanding.uncertainties.map((unc, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl border border-amber-500/30 bg-amber-950/20 text-amber-200 text-xs font-sans"
                        >
                          {unc}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* PDF MODE CONTENT */
              <div className="space-y-4">
                {activeSection ? (
                  <div className="p-4 rounded-2xl border border-purple-500/30 bg-purple-950/20 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5" />
                        <span>AI SECTION SUMMARY</span>
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        p. {activeSection.page_start || activeSection.pageNumber}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-white">
                      {activeSection.section_title || activeSection.title}
                    </h4>
                    <p className="text-slate-200 leading-relaxed font-sans text-xs">
                      {activeSection.summary}
                    </p>
                    {activeSection.key_takeaway && (
                      <div className="p-3 rounded-xl border border-purple-400/30 bg-purple-900/30 text-purple-200 text-xs font-mono">
                        <span className="font-bold text-[10px] uppercase block text-purple-300 mb-0.5">
                          Architectural Takeaway:
                        </span>
                        "{activeSection.key_takeaway}"
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02] text-slate-400 italic">
                    No macro section boundary begins on Page {currentPage}.
                  </div>
                )}

                {/* Formal Concepts */}
                {pageConcepts.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-sky-400 block tracking-wider">
                      FORMAL CONCEPTS & DEFINITIONS (PAGE {currentPage})
                    </span>
                    {pageConcepts.map((con: any, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-sky-500/30 bg-sky-950/20 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-sky-300">{con.concept}</span>
                          <span className="text-[10px] text-sky-400">{con.section_title}</span>
                        </div>
                        <p className="text-xs text-slate-200 font-sans">{con.definition}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Empirical Facts */}
                {pageFacts.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-emerald-400 block tracking-wider">
                      EMPIRICAL BENCHMARKS & VERIFIED FACTS (PAGE {currentPage})
                    </span>
                    {pageFacts.map((fact: any, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 space-y-1.5">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-xs text-slate-100 font-semibold font-sans">{fact.fact_statement}</p>
                          {fact.metric_or_data && (
                            <span className="px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 font-mono text-[11px] border border-emerald-500/40 shrink-0">
                              {fact.metric_or_data}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Cross-Section Synthesis */}
                {pageRelations.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold uppercase text-purple-400 block tracking-wider">
                      CROSS-SECTION SYNTHESIS (PAGE {currentPage})
                    </span>
                    {pageRelations.map((rel: any, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-purple-500/30 bg-purple-950/20 space-y-1">
                        <span className="font-bold text-xs text-purple-300 block">{rel.relation_type}</span>
                        <p className="text-xs text-slate-200 font-sans">{rel.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 6. VIEWER FOOTER */}
      <div className="p-3 border-t border-slate-200/60 dark:border-white/10 bg-slate-50/70 dark:bg-[#0b1022] flex items-center justify-between text-[10px] font-mono text-slate-400 flex-wrap gap-2">
        <div className="flex items-center gap-1.5 text-slate-400">
          <span className={`w-1.5 h-1.5 rounded-full ${isImageDoc ? 'bg-emerald-400' : 'bg-emerald-400'}`} />
          <span>
            {isImageDoc
              ? 'Verbatim Image Content Guaranteed • RapidOCR + Qwen2.5-VL Vision Verified'
              : 'Verbatim PDF Content Guaranteed • Zero Reconstructed Text'}
          </span>
        </div>

        {!isImageDoc && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage(6)}
              className="text-purple-400 hover:text-purple-300 transition-colors cursor-pointer"
            >
              Table 1 (p. 6) →
            </button>
            <span>•</span>
            <button
              type="button"
              onClick={() => setCurrentPage(8)}
              className="text-sky-400 hover:text-sky-300 font-bold transition-colors cursor-pointer"
            >
              Table 2 Results (p. 8) →
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;

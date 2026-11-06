export type DocumentType = 'pdf' | 'docx' | 'txt' | 'pptx' | 'csv' | 'md' | 'png' | 'jpg' | 'jpeg' | 'webp' | 'bmp';

export interface OCRLine {
  text: string;
  confidence: number;
  box?: number[][];
}

export interface VisualEvidenceItem {
  id: string;
  label: string;
  type: string;
  location: string;
  content: string;
  confidence: number;
}

export interface ImageUnderstanding {
  image_id: string;
  filename: string;
  dimensions: {
    width: number;
    height: number;
    format: string;
    mode: string;
    megapixels: number;
    aspect_ratio: string;
  };
  summary: string;
  ocr_text: string;
  ocr_lines: OCRLine[];
  visual_observations: string[];
  key_entities: string[];
  numerical_values: string[];
  relationships: string[];
  evidence_items: VisualEvidenceItem[];
  uncertainties: string[];
}

export type DocumentProcessingStatus =
  | 'idle'
  | 'uploading'
  | 'reading'
  | 'extracting_claims'
  | 'locating_evidence'
  | 'ready'
  | 'error';

export type EvidenceType =
  | 'claim'
  | 'evidence'
  | 'limitation'
  | 'counterargument'
  | 'assumption'
  | 'uncertainty';

export interface EvidenceReference {
  id: string;
  documentId: string;
  documentName: string;
  pageNumber: number;
  sectionTitle: string;
  excerpt: string;
  type: EvidenceType;
  relevanceScore: number; // 0 - 100
  speakerTarget?: 'PRO' | 'CON';
}

export interface DocumentSection {
  id: string;
  title: string;
  pageNumber: number;
  wordCount: number;
  claimsCount: number;
  summary: string;
}

export interface DocumentMetadata {
  id: string;
  name: string;
  fileSize: string;
  fileSizeBytes: number;
  fileType: DocumentType;
  pageCount: number;
  uploadedAt: string;
  status: DocumentProcessingStatus;
  summary: string;
  keyClaimsCount: number;
  evidencePointsCount: number;
  debatesCount: number;
  sections: DocumentSection[];
  suggestedQuestions: string[];
}

export type DebateMode = 'claim-challenge' | 'critical-review' | 'balanced-analysis';

export interface DebateModeOption {
  id: DebateMode;
  name: string;
  description: string;
  proRole: string;
  conRole: string;
}

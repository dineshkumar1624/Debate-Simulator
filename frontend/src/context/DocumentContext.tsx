import React, { createContext, useContext, useState, useCallback } from 'react';
import { DocumentMetadata, EvidenceReference, DebateMode } from '../types/document';

export const VALID_EXTENSIONS = ['pdf', 'docx', 'txt'] as const;
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

export function validateDocumentFile(file: File): { valid: boolean; error?: string } {
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (!ext || !['pdf', 'docx', 'txt'].includes(ext)) {
    return {
      valid: false,
      error: 'Unsupported file format. Please upload a PDF, DOCX, or TXT document.',
    };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: 'File size exceeds 25 MB limit for document processing.',
    };
  }
  return { valid: true };
}

interface DocumentContextType {
  activeDocument: DocumentMetadata;
  documents: DocumentMetadata[];
  activeQuestion: string;
  setActiveQuestion: (q: string) => void;
  selectedMode: DebateMode;
  setSelectedMode: (m: DebateMode) => void;
  isProcessing: boolean;
  processingStage: string;
  uploadDocument: (file: File) => Promise<DocumentMetadata>;
  replaceActiveDocument: (file: File) => Promise<DocumentMetadata>;
  removeDocument: (id: string) => void;
  selectDocument: (id: string) => void;
  evidenceItems: EvidenceReference[];
}

const DEFAULT_DOCUMENTS: DocumentMetadata[] = [
  {
    id: 'doc-ai-law',
    name: 'AI_in_HighStakes_Law.pdf',
    fileSize: '1.8 MB',
    fileSizeBytes: 1887436,
    fileType: 'pdf',
    pageCount: 24,
    uploadedAt: 'Today, 2:40 PM',
    status: 'ready',
    summary:
      'Empirical evaluation of neural decision-support algorithms deployed in civil and criminal liability adjudication, analyzing error distribution, statutory compliance, and due process bounds.',
    keyClaimsCount: 14,
    evidencePointsCount: 38,
    debatesCount: 3,
    sections: [
      {
        id: 'sec-1',
        title: 'Executive Summary & Jurisprudential Context',
        pageNumber: 1,
        wordCount: 820,
        claimsCount: 3,
        summary: 'Introduces statutory tension between algorithmic consistency and constitutional human oversight.',
      },
      {
        id: 'sec-2',
        title: 'Methodology & Error Distribution Analysis',
        pageNumber: 5,
        wordCount: 1450,
        claimsCount: 4,
        summary: 'Benchmarking 12,000 synthetic judicial rulings comparing autonomous and human panels.',
      },
      {
        id: 'sec-3',
        title: 'Empirical Results & Consistency Gains',
        pageNumber: 8,
        wordCount: 1980,
        claimsCount: 5,
        summary: 'Reports 32% lower inter-circuit sentencing variance and Bayesian prior adherence.',
      },
      {
        id: 'sec-4',
        title: 'Out-of-Distribution Failures & Black Swan Vulnerabilities',
        pageNumber: 14,
        wordCount: 1640,
        claimsCount: 4,
        summary: 'Exposes catastrophic misclassification in novel socio-legal dilemmas lacking training precedents.',
      },
      {
        id: 'sec-5',
        title: 'Constitutional Recourse & Legitimacy Bounds',
        pageNumber: 19,
        wordCount: 1320,
        claimsCount: 3,
        summary: 'Argues algorithmic opacity violates procedural due process and democratic accountability.',
      },
      {
        id: 'sec-6',
        title: 'Concluding Policy Framework',
        pageNumber: 23,
        wordCount: 910,
        claimsCount: 2,
        summary: 'Recommends dual-track framework: automated bounded verification with non-delegable human liability.',
      },
    ],
    suggestedQuestions: [
      'Does the document provide sufficient empirical evidence to justify replacing human judges in liability rulings?',
      'What are the strongest methodological limitations identified in the study on Page 14?',
      'How does the author resolve the conflict between mathematical consistency and democratic legitimacy?',
      'Is the 32% variance reduction supported by statistically sound benchmarks across all circuits?',
    ],
  },
  {
    id: 'doc-triage',
    name: 'Autonomous_Clinical_Triage.pdf',
    fileSize: '1.4 MB',
    fileSizeBytes: 1468006,
    fileType: 'pdf',
    pageCount: 18,
    uploadedAt: 'Yesterday',
    status: 'ready',
    summary:
      'Prospective trial of multi-agent Bayesian triage systems across 4 intensive care networks during peak respiratory surge.',
    keyClaimsCount: 11,
    evidencePointsCount: 29,
    debatesCount: 1,
    sections: [
      {
        id: 'sec-t1',
        title: 'Clinical Triage Benchmark Protocol',
        pageNumber: 2,
        wordCount: 950,
        claimsCount: 3,
        summary: 'Protocol definition across 4 tertiary trauma hospitals measuring bed allocation speed.',
      },
      {
        id: 'sec-t2',
        title: 'Primary Outcomes: Triage Accuracy & Latency',
        pageNumber: 7,
        wordCount: 1820,
        claimsCount: 4,
        summary: 'Demonstrated 41-minute median reduction in ICU transfer delays with verified Bayesian priors.',
      },
      {
        id: 'sec-t3',
        title: 'Atypical Presentation & Diagnostic Bias Blind Spots',
        pageNumber: 12,
        wordCount: 1530,
        claimsCount: 3,
        summary: 'Demonstrated systemic under-triage for comorbid geriatric patients with atypical symptomatology.',
      },
    ],
    suggestedQuestions: [
      'Does the 41-minute latency reduction outweigh the risk of atypical under-triage?',
      'Can the trial results be generalized beyond high-resource tertiary trauma hospitals?',
    ],
  },
];

const DEFAULT_EVIDENCE: EvidenceReference[] = [
  {
    id: 'ev-1',
    documentId: 'doc-ai-law',
    documentName: 'AI_in_HighStakes_Law.pdf',
    pageNumber: 8,
    sectionTitle: 'Section 3: Empirical Results',
    excerpt:
      'Across 12,000 simulated appellate rulings, autonomous Bayesian priors achieved a 32% reduction in inter-circuit sentencing variance compared to historical judicial panels (p < 0.001).',
    type: 'evidence',
    relevanceScore: 96,
    speakerTarget: 'PRO',
  },
  {
    id: 'ev-2',
    documentId: 'doc-ai-law',
    documentName: 'AI_in_HighStakes_Law.pdf',
    pageNumber: 14,
    sectionTitle: 'Section 4: Out-of-Distribution Failures',
    excerpt:
      'When presented with non-precedential novel fact patterns (black-swan socio-legal dilemmas), the neural classifier produced confidence scores exceeding 91% on objectively erroneous statutory interpretations.',
    type: 'limitation',
    relevanceScore: 94,
    speakerTarget: 'CON',
  },
  {
    id: 'ev-3',
    documentId: 'doc-ai-law',
    documentName: 'AI_in_HighStakes_Law.pdf',
    pageNumber: 11,
    sectionTitle: 'Section 3.2: Runtime Invariant Verification',
    excerpt:
      'Coupling generative deliberation with SMT constraint solvers guaranteed zero violation of codified statutory floor penalties across the affirmative test corpus.',
    type: 'claim',
    relevanceScore: 89,
    speakerTarget: 'PRO',
  },
  {
    id: 'ev-4',
    documentId: 'doc-ai-law',
    documentName: 'AI_in_HighStakes_Law.pdf',
    pageNumber: 19,
    sectionTitle: 'Section 5: Constitutional Recourse',
    excerpt:
      'Mathematical consistency cannot substitute for civic legitimacy; algorithmic recourse lacks the non-delegable moral accountability demanded by procedural due process.',
    type: 'counterargument',
    relevanceScore: 92,
    speakerTarget: 'CON',
  },
  {
    id: 'ev-5',
    documentId: 'doc-ai-law',
    documentName: 'AI_in_HighStakes_Law.pdf',
    pageNumber: 23,
    sectionTitle: 'Section 6: Concluding Framework',
    excerpt:
      'The data indicates optimal societal outcomes emerge when autonomous calculation handles bounded formal checks, while final normative discretionary decisions remain with human tribunals.',
    type: 'uncertainty',
    relevanceScore: 95,
  },
];

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export const DocumentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<DocumentMetadata[]>(DEFAULT_DOCUMENTS);
  const [activeDocumentId, setActiveDocumentId] = useState<string>('doc-ai-law');
  const [activeQuestion, setActiveQuestion] = useState<string>(
    'Does the document provide sufficient empirical evidence to justify replacing human judges in liability rulings?'
  );
  const [selectedMode, setSelectedMode] = useState<DebateMode>('claim-challenge');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingStage, setProcessingStage] = useState<string>('DOCUMENT READY');

  const activeDocument =
    documents.find((d) => d.id === activeDocumentId) || documents[0] || DEFAULT_DOCUMENTS[0];

  const selectDocument = useCallback(
    (id: string) => {
      const doc = documents.find((d) => d.id === id);
      if (doc) {
        setActiveDocumentId(id);
        if (doc.suggestedQuestions.length > 0) {
          setActiveQuestion(doc.suggestedQuestions[0]);
        }
      }
    },
    [documents]
  );

  const uploadDocument = useCallback(async (file: File): Promise<DocumentMetadata> => {
    setIsProcessing(true);
    setProcessingStage('READING DOCUMENT...');

    await new Promise((r) => setTimeout(r, 600));
    setProcessingStage('EXTRACTING TEXT & SECTIONS...');

    await new Promise((r) => setTimeout(r, 700));
    setProcessingStage('IDENTIFYING CLAIMS & EVIDENCE...');

    await new Promise((r) => setTimeout(r, 600));
    setProcessingStage('DOCUMENT READY');

    const ext = file.name.split('.').pop()?.toLowerCase() || 'pdf';
    const type = ext === 'docx' ? 'docx' : ext === 'txt' ? 'txt' : 'pdf';
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    const estimatedPages = Math.max(1, Math.round(file.size / (60 * 1024)));

    const newDoc: DocumentMetadata = {
      id: `doc-${Date.now()}`,
      name: file.name,
      fileSize: `${sizeMb} MB`,
      fileSizeBytes: file.size,
      fileType: type,
      pageCount: estimatedPages,
      uploadedAt: 'Just now',
      status: 'ready',
      summary: `Uploaded document "${file.name}". Ready for evidence-grounded dialectic analysis between opposing AI reasoning systems.`,
      keyClaimsCount: Math.min(18, Math.max(6, Math.round(estimatedPages * 0.7))),
      evidencePointsCount: Math.min(45, Math.max(12, Math.round(estimatedPages * 1.6))),
      debatesCount: 0,
      sections: [
        {
          id: 'sec-u1',
          title: 'Primary Thesis & Abstract',
          pageNumber: 1,
          wordCount: 650,
          claimsCount: 2,
          summary: 'Core proposition and problem definition extracted from introductory passages.',
        },
        {
          id: 'sec-u2',
          title: 'Empirical Findings & Data Records',
          pageNumber: Math.max(2, Math.round(estimatedPages * 0.4)),
          wordCount: 1400,
          claimsCount: 5,
          summary: 'Quantitative benchmarks and observed effects extracted from central tables.',
        },
        {
          id: 'sec-u3',
          title: 'Stated Constraints & Critical Limitations',
          pageNumber: Math.max(3, Math.round(estimatedPages * 0.75)),
          wordCount: 1100,
          claimsCount: 4,
          summary: 'Author-acknowledged bounds, sampling constraints, and scope limitations.',
        },
      ],
      suggestedQuestions: [
        `Does "${file.name}" provide sufficient evidence to support its central claims?`,
        `What are the most significant methodological weaknesses or limitations stated in this document?`,
        `How reliably can the findings in "${file.name}" be applied beyond its specific test conditions?`,
      ],
    };

    setDocuments((prev) => [newDoc, ...prev]);
    setActiveDocumentId(newDoc.id);
    setActiveQuestion(newDoc.suggestedQuestions[0]);
    setIsProcessing(false);

    return newDoc;
  }, []);

  const replaceActiveDocument = useCallback(async (file: File): Promise<DocumentMetadata> => {
    return uploadDocument(file);
  }, [uploadDocument]);

  const removeDocument = useCallback((id: string) => {
    setDocuments((prev) => {
      const filtered = prev.filter((d) => d.id !== id);
      if (filtered.length === 0) return DEFAULT_DOCUMENTS;
      return filtered;
    });
    if (activeDocumentId === id) {
      setDocuments((prev) => {
        const next = prev.find((d) => d.id !== id) || DEFAULT_DOCUMENTS[0];
        setActiveDocumentId(next.id);
        if (next.suggestedQuestions.length > 0) {
          setActiveQuestion(next.suggestedQuestions[0]);
        }
        return prev;
      });
    }
  }, [activeDocumentId]);

  return (
    <DocumentContext.Provider
      value={{
        activeDocument,
        documents,
        activeQuestion,
        setActiveQuestion,
        selectedMode,
        setSelectedMode,
        isProcessing,
        processingStage,
        uploadDocument,
        replaceActiveDocument,
        removeDocument,
        selectDocument,
        evidenceItems: DEFAULT_EVIDENCE,
      }}
    >
      {children}
    </DocumentContext.Provider>
  );
};

export const useDocument = (): DocumentContextType => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocument must be used within a DocumentProvider');
  }
  return context;
};

export default DocumentContext;

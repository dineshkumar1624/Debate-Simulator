import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { DocumentMetadata, EvidenceReference, DebateMode } from '../types/document';
import { debateApi } from '../services/api';

interface DocumentContextType {
  activeDocument: DocumentMetadata | null;
  documents: DocumentMetadata[];
  activeKnowledge: any | null;
  queryKnowledge: (query: string) => Promise<any>;
  activeQuestion: string;
  setActiveQuestion: (q: string) => void;
  selectedMode: DebateMode;
  setSelectedMode: (m: DebateMode) => void;
  isProcessing: boolean;
  processingStage: string;
  uploadDocument: (file: File) => Promise<DocumentMetadata>;
  replaceActiveDocument: (file: File) => Promise<DocumentMetadata>;
  removeDocument: (id: string) => Promise<void>;
  clearAllDocuments: () => Promise<void>;
  selectDocument: (id: string) => void;
  evidenceItems: EvidenceReference[];
}

const DEFAULT_EVIDENCE: EvidenceReference[] = [];

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export const DocumentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [activeKnowledge, setActiveKnowledge] = useState<any | null>(null);
  const [activeQuestion, setActiveQuestion] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<DebateMode>('claim-challenge');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingStage, setProcessingStage] = useState<string>('IDLE');

  // Load persistent documents from FastAPI backend
  useEffect(() => {
    let isMounted = true;
    async function loadBackendDocuments() {
      try {
        const backendDocs = await debateApi.getDocuments();
        if (backendDocs && backendDocs.length > 0 && isMounted) {
          setDocuments(backendDocs);
          setActiveDocumentId(backendDocs[0].id);
          if (backendDocs[0].suggestedQuestions?.length > 0) {
            setActiveQuestion(backendDocs[0].suggestedQuestions[0]);
          }
        } else if (isMounted) {
          setDocuments([]);
          setActiveDocumentId(null);
          setActiveKnowledge(null);
          setActiveQuestion('');
        }
      } catch (err) {
        console.warn('Backend documents API unavailable, initializing empty library:', err);
        if (isMounted) {
          setDocuments([]);
          setActiveDocumentId(null);
          setActiveKnowledge(null);
          setActiveQuestion('');
        }
      }
    }
    loadBackendDocuments();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch whole-document knowledge whenever active document changes
  useEffect(() => {
    if (!activeDocumentId) {
      setActiveKnowledge(null);
      return;
    }
    let isMounted = true;
    debateApi
      .getDocumentKnowledge(activeDocumentId)
      .then((k) => {
        if (isMounted) setActiveKnowledge(k);
      })
      .catch((e) => {
        console.warn('Could not fetch whole-document knowledge:', e);
        if (isMounted) setActiveKnowledge(null);
      });
    return () => {
      isMounted = false;
    };
  }, [activeDocumentId]);

  const activeDocument =
    (activeDocumentId ? documents.find((d) => d.id === activeDocumentId) : null) ||
    (documents.length > 0 ? documents[0] : null);

  const selectDocument = useCallback(
    (id: string) => {
      const doc = documents.find((d) => d.id === id);
      if (doc) {
        setActiveDocumentId(id);
        if (doc.suggestedQuestions && doc.suggestedQuestions.length > 0) {
          setActiveQuestion(doc.suggestedQuestions[0]);
        }
      }
    },
    [documents]
  );

  const queryKnowledge = useCallback(
    async (query: string): Promise<any> => {
      if (!activeDocumentId) {
        return null;
      }
      return await debateApi.queryDocument(activeDocumentId, query);
    },
    [activeDocumentId]
  );

  const uploadDocument = useCallback(async (file: File): Promise<DocumentMetadata> => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const isImage = ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(ext);

    setIsProcessing(true);
    const stageTimers: ReturnType<typeof setTimeout>[] = [];

    if (isImage) {
      setProcessingStage('Validating image & orientation...');
      stageTimers.push(setTimeout(() => setProcessingStage('Extracting text via RapidOCR...'), 1500));
      stageTimers.push(setTimeout(() => setProcessingStage('Running Qwen multimodal vision analysis...'), 4000));
      stageTimers.push(setTimeout(() => setProcessingStage('Structuring visual evidence & indexing...'), 40000));
    } else {
      setProcessingStage('Uploading file...');
      stageTimers.push(setTimeout(() => setProcessingStage('Extracting PDF pages...'), 2000));
      stageTimers.push(setTimeout(() => setProcessingStage('Generating embeddings...'), 25000));
      stageTimers.push(setTimeout(() => setProcessingStage('Indexing evidence...'), 55000));
      stageTimers.push(setTimeout(() => setProcessingStage('Building document knowledge...'), 85000));
    }

    const clearTimers = () => {
      stageTimers.forEach((t) => clearTimeout(t));
    };

    try {
      const response = await debateApi.uploadDocument(file);
      clearTimers();
      const newDoc: DocumentMetadata = response.document;
      setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
      setActiveDocumentId(newDoc.id);
      if (newDoc.suggestedQuestions && newDoc.suggestedQuestions.length > 0) {
        setActiveQuestion(newDoc.suggestedQuestions[0]);
      }
      setIsProcessing(false);
      setProcessingStage(isImage ? 'Image ready for debate' : 'Document ready');
      return newDoc;
    } catch (err: any) {
      clearTimers();
      setIsProcessing(false);
      const detailMsg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to upload and process document on backend server.';
      setProcessingStage(`Error: ${detailMsg}`);
      console.error('Document upload failed on backend:', err);
      throw new Error(detailMsg);
    }
  }, []);

  const replaceActiveDocument = useCallback(async (file: File): Promise<DocumentMetadata> => {
    return uploadDocument(file);
  }, [uploadDocument]);

  const removeDocument = useCallback(async (id: string) => {
    try {
      await debateApi.deleteDocument(id);
    } catch (err) {
      console.warn('Backend delete document failed:', err);
    }
    setDocuments((prev) => {
      const remaining = prev.filter((d) => d.id !== id);
      if (activeDocumentId === id) {
        if (remaining.length > 0) {
          setActiveDocumentId(remaining[0].id);
          setActiveQuestion(remaining[0].suggestedQuestions?.[0] || '');
        } else {
          setActiveDocumentId(null);
          setActiveKnowledge(null);
          setActiveQuestion('');
        }
      }
      return remaining;
    });
  }, [activeDocumentId]);

  const clearAllDocuments = useCallback(async () => {
    try {
      await debateApi.clearAllDocuments();
    } catch (err) {
      console.warn('Backend clear all documents failed:', err);
    }
    setDocuments([]);
    setActiveDocumentId(null);
    setActiveKnowledge(null);
    setActiveQuestion('');
  }, []);

  return (
    <DocumentContext.Provider
      value={{
        activeDocument,
        documents,
        activeKnowledge,
        queryKnowledge,
        activeQuestion,
        setActiveQuestion,
        selectedMode,
        setSelectedMode,
        isProcessing,
        processingStage,
        uploadDocument,
        replaceActiveDocument,
        removeDocument,
        clearAllDocuments,
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

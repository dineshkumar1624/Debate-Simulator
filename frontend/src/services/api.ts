import axios, { AxiosInstance } from 'axios';
import {
  StartDebateRequest,
  StartDebateResponse,
  DebateSession,
  DebateHistoryItem,
  DebateHistoryResponse,
  DebateSynthesis,
  DebateStreamEvent,
  ShowcaseResponse,
  ResearchResponse,
  ResearchSource,
} from '../types/debate';

// Base API configuration from Vite environment variable (optional placeholder in Phase 1)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Standard Axios client instance configured for future FastAPI backend integration.
 * In Phase 1, this service acts solely as an abstraction layer with typed contracts.
 * No real HTTP requests or fake responses are fabricated.
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  timeout: 300000,
});

/**
 * Debate API Service Abstraction
 * Ready to connect to FastAPI endpoints in Phase 2.
 */
export const debateApi = {
  /**
   * Initializes a new multi-agent debate session with the given configuration
   */
  async startDebate(payload: StartDebateRequest): Promise<StartDebateResponse> {
    const response = await apiClient.post<StartDebateResponse>('/debates', payload);
    return response.data;
  },

  /**
   * Fetches the current session state, turns, and progress for an active debate
   */
  async getDebate(debateId: string): Promise<DebateSession> {
    const response = await apiClient.get<DebateSession>(`/debates/${debateId}`);
    return response.data;
  },

  /**
   * Safely cancels an active debate without deleting its history or recorded messages
   */
  async cancelDebate(debateId: string): Promise<{ status: string; debateId: string; message: string }> {
    const response = await apiClient.post<{ status: string; debateId: string; message: string }>(`/debates/${debateId}/cancel`);
    return response.data;
  },

  /**
   * Retrieves the currently active / running debate across the entire platform for seamless reconnection
   */
  async getActiveDebate(): Promise<{
    hasActive: boolean;
    debateId: string | null;
    status?: string | null;
    topic?: string | null;
    rounds?: number | null;
    documentId?: string | null;
    sourceScope?: string | null;
    evidenceMode?: boolean | null;
    debate?: DebateSession | null;
  }> {
    const response = await apiClient.get<any>('/debates/active');
    return response.data;
  },

  /**
   * Fetches past debate history list from the dedicated /history endpoint with search and pagination
   */
  async getHistory(params?: {
    query?: string;
    status?: string;
    page?: number;
    pageSize?: number;
  }): Promise<DebateHistoryResponse> {
    const response = await apiClient.get<DebateHistoryResponse>('/history', {
      params: {
        query: params?.query,
        status: params?.status,
        page: params?.page || 1,
        page_size: params?.pageSize || 20,
      },
    });
    return response.data;
  },

  /**
   * Retrieves a single historical debate in full detail for read-only replay
   */
  async getHistoryDebate(debateId: string): Promise<DebateSession> {
    const response = await apiClient.get<DebateSession>(`/history/${debateId}`);
    return response.data;
  },

  /**
   * Deletes a single debate attempt by ID from history
   */
  async deleteHistoryAttempt(debateId: string): Promise<{ status: string; deletedId?: string; message: string }> {
    const response = await apiClient.delete<{ status: string; deletedId?: string; message: string }>(`/history/${debateId}`);
    return response.data;
  },

  /**
   * Deletes an entire debate topic group and all its attempts
   */
  async deleteHistoryGroup(payload: {
    groupKey?: string;
    debateIds?: string[];
    topic?: string;
    documentId?: string;
  }): Promise<{ status: string; deletedCount?: number; message: string }> {
    const response = await apiClient.delete<{ status: string; deletedCount?: number; message: string }>('/history/group', {
      data: payload,
    });
    return response.data;
  },

  /**
   * Batch deletes multiple debates by their IDs (e.g. all debates on current page)
   */
  async deleteDebatesBatch(debateIds: string[]): Promise<{ status: string; deletedCount?: number; message: string }> {
    const response = await apiClient.delete<{ status: string; deletedCount?: number; message: string }>('/history/batch', {
      data: { debateIds },
    });
    return response.data;
  },

  /**
   * Retrieves lightweight showcase debates for homepage rotation (strictly read-only, 0 LLM calls)
   */
  async getShowcaseDebates(limit = 8): Promise<ShowcaseResponse> {
    const response = await apiClient.get<ShowcaseResponse>('/history/showcase', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Fetches past debate history list (backward-compatible)
   */
  async getDebateHistory(): Promise<DebateHistoryItem[]> {
    const response = await apiClient.get<DebateHistoryItem[]>('/debates');
    return response.data;
  },

  /**
   * Retrieves final synthesis, verdict, and evidence rating for a completed debate
   */
  async getDebateResult(debateId: string): Promise<DebateSynthesis> {
    const response = await apiClient.get<DebateSynthesis>(`/debates/${debateId}/synthesis`);
    return response.data;
  },

  /**
   * Stream debate events in real time via Server-Sent Events (SSE) placeholder
   */
  getDebateStream(
    debateId: string,
    onMessage: (event: DebateStreamEvent) => void,
    onError?: (error: unknown) => void
  ): () => void {
    // SSE connection abstraction for Phase 2
    const eventSource = new EventSource(`${API_BASE_URL}/debates/${debateId}/stream`);
    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onMessage(parsed);
      } catch (err) {
        if (onError) onError(err);
      }
    };
    eventSource.onerror = (err) => {
      if (onError) onError(err);
    };

    return () => {
      eventSource.close();
    };
  },

  /**
   * Whole-Document Understanding & Knowledge API
   */
  async getDocuments(): Promise<any[]> {
    const response = await apiClient.get<any[]>('/documents');
    return response.data;
  },

  async getDocument(documentId: string): Promise<any> {
    const response = await apiClient.get<any>(`/documents/${documentId}`);
    return response.data;
  },

  async getDocumentKnowledge(documentId: string): Promise<any> {
    const response = await apiClient.get<any>(`/documents/${documentId}/knowledge`);
    return response.data;
  },

  async queryDocument(documentId: string, query: string): Promise<any> {
    const response = await apiClient.post<any>(`/documents/${documentId}/query`, { query });
    return response.data;
  },

  async reuseDocumentForDebate(documentId: string, proposition: string): Promise<any> {
    const response = await apiClient.post<any>(`/documents/${documentId}/reuse-for-debate`, { proposition });
    return response.data;
  },

  async uploadDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<any>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async deleteDocument(documentId: string): Promise<any> {
    const response = await apiClient.delete<any>(`/documents/${documentId}`);
    return response.data;
  },

  async clearAllDocuments(): Promise<any> {
    const response = await apiClient.delete<any>('/documents/clear-all');
    return response.data;
  },

  getDocumentPageRenderUrl(documentId: string, pageNumber: number, scale: number = 2.0): string {
    return `${API_BASE_URL}/documents/${documentId}/pages/${pageNumber}/render?scale=${scale}`;
  },

  async getDocumentPageText(documentId: string, pageNumber: number): Promise<{
    document_id: string;
    page_number: number;
    section_title: string;
    extracted_text: string;
    character_count: number;
    word_count: number;
    chunks_count: number;
  }> {
    const response = await apiClient.get<any>(`/documents/${documentId}/pages/${pageNumber}/text`);
    return response.data;
  },

  async getDocumentImageUnderstanding(documentId: string): Promise<any> {
    const response = await apiClient.get<any>(`/documents/${documentId}/image-understanding`);
    return response.data;
  },

  getDocumentFileUrl(documentId: string): string {
    return `${API_BASE_URL}/documents/${documentId}/file`;
  },

  /**
   * Conducts real web research on a debate topic, collecting articles and indexing them in Qdrant
   */
  async conductResearch(topic: string, maxSources = 4, debateId?: string): Promise<ResearchResponse> {
    const response = await apiClient.post<ResearchResponse>('/research', {
      topic,
      max_sources: maxSources,
      debate_id: debateId,
    });
    return response.data;
  },

  /**
   * Generates the SSE streaming endpoint URL for real-time web research events.
   */
  getResearchStreamUrl(topic: string, maxSources = 4, debateId?: string): string {
    const params = new URLSearchParams({ topic, max_sources: String(maxSources) });
    if (debateId) params.append('debate_id', debateId);
    return `${API_BASE_URL}/research/stream?${params.toString()}`;
  },

  /**
   * Retrieves saved web research sources by debate ID or topic
   */
  async getResearchSources(identifier: string): Promise<ResearchSource[]> {
    const response = await apiClient.get<ResearchSource[]>(`/research/sources/${encodeURIComponent(identifier)}`);
    return response.data;
  },
};

export default debateApi;

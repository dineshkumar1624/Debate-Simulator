import axios, { AxiosInstance } from 'axios';
import {
  StartDebateRequest,
  StartDebateResponse,
  DebateSession,
  DebateHistoryItem,
  DebateSynthesis,
  DebateStreamEvent,
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
  timeout: 30000,
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
   * Fetches past debate history list
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
};

export default debateApi;

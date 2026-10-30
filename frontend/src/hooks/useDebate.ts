import { useState, useCallback } from 'react';
import { StartDebateRequest, DebateSession, DebateStatus } from '../types/debate';
import debateApi from '../services/api';

export function useDebate() {
  const [session, setSession] = useState<DebateSession | null>(null);
  const [status, setStatus] = useState<DebateStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const startDebate = useCallback(async (config: StartDebateRequest) => {
    setStatus('configuring');
    setError(null);
    try {
      const response = await debateApi.startDebate(config);
      setStatus(response.status);
      return response;
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to debate service';
      setError(errorMessage);
      setStatus('failed');
      throw err;
    }
  }, []);

  const resetDebate = useCallback(() => {
    setSession(null);
    setStatus('idle');
    setError(null);
  }, []);

  return {
    session,
    status,
    error,
    startDebate,
    resetDebate,
  };
}

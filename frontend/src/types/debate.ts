export type DebaterPosition = 'PRO' | 'CON';

export type DebateStatus =
  | 'idle'
  | 'configuring'
  | 'debating'
  | 'verifying'
  | 'evaluating'
  | 'synthesizing'
  | 'completed'
  | 'failed'
  | 'evaluation_failed';

export interface DebateConfig {
  topic: string;
  debaterAModel: string;
  debaterBModel: string;
  judgeModel: string;
  rounds: number;
  evidenceMode: boolean;
  strictFactChecking?: boolean;
}

export interface EvidenceItem {
  id: string;
  claim: string;
  source: string;
  url?: string;
  pageNumber?: number;
  sectionTitle?: string;
  verdict: 'supported' | 'contradicted' | 'unverifiable';
  confidenceScore: number;
}

export interface DebateTurn {
  speaker: 'DEBATER_A' | 'DEBATER_B' | 'JUDGE' | 'SYNTHESIZER';
  role?: DebaterPosition;
  title?: string;
  content: string;
  timestamp: string;
  evidence?: EvidenceItem[];
  executionStatus?: 'REAL_LOCAL_MODEL' | 'REAL_REMOTE_API' | 'SIMULATED';
}

export interface DebateRound {
  roundNumber: number;
  turns: DebateTurn[];
}

export interface DebateSynthesis {
  summary: string;
  keyConsensus: string[];
  keyContentions: string[];
  evidenceReliabilityScore: number; // 0-100
  balancedVerdict: string;
  judgeModelUsed?: string;
  isFallback?: boolean;
  executionStatus?: 'REAL_REMOTE_API' | 'SIMULATED';
}

export interface DebateSession {
  id: string;
  topic: string;
  createdAt: string;
  status: DebateStatus;
  config: DebateConfig;
  rounds: DebateRound[];
  synthesis?: DebateSynthesis;
}

export interface StartDebateRequest {
  topic: string;
  debaterAModel: string;
  debaterBModel: string;
  judgeModel: string;
  rounds: number;
  evidenceMode: boolean;
  documentId?: string;
  sourceScope?: string;
  strictFactChecking?: boolean;
}

export interface StartDebateResponse {
  debateId: string;
  status: DebateStatus;
  message: string;
}

export interface DebateHistoryItem {
  id: string;
  topic: string;
  createdAt: string;
  roundsCount: number;
  status: DebateStatus;
}

export interface DebateStreamEvent {
  event: 'turn' | 'evidence' | 'evaluation' | 'synthesis' | 'status';
  data: Record<string, unknown>;
}

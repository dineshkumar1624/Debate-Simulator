export type DebaterPosition = 'PRO' | 'CON';

export type DebateStatus =
  | 'idle'
  | 'configuring'
  | 'queued'
  | 'running'
  | 'debating'
  | 'verifying'
  | 'evaluating'
  | 'synthesizing'
  | 'completed'
  | 'failed'
  | 'evaluation_failed'
  | 'cancelled';

export interface DebateConfig {
  topic: string;
  debaterAModel: string;
  debaterBModel: string;
  judgeModel: string;
  judgeProvider?: 'gemini' | 'nvidia';
  rounds: number;
  evidenceMode: boolean;
  strictFactChecking?: boolean;
  documentId?: string;
  documentName?: string;
  documentType?: string;
  sourceScope?: string;
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
  confidence?: number;
  evidence?: EvidenceItem[];
  executionStatus?: 'REAL_LOCAL_MODEL' | 'REAL_REMOTE_API' | 'SIMULATED';
}

export interface DebateRound {
  roundNumber: number;
  turns: DebateTurn[];
}

export interface CriterionScoreDetail {
  score: number;
  max_score: number;
  reason?: string;
  deductions_explanation?: string;
  supporting_message_refs?: string[];
  supporting_evidence_refs?: string[];
}

export interface CitationAssessmentItem {
  citation_id?: string;
  source_reference: string;
  speaker?: string;
  verification_status: 'verified' | 'unverified' | 'fabricated' | 'contradicted';
  claim_supported: boolean;
  details: string;
}

export interface DebateSynthesis {
  summary: string;
  keyConsensus: string[];
  keyContentions: string[];
  evidenceReliabilityScore: number; // 0-100
  balancedVerdict: string;
  judgeModelUsed?: string;
  judgeProvider?: 'gemini' | 'nvidia';
  isFallback?: boolean;
  executionStatus?: 'REAL_REMOTE_API' | 'SIMULATED';
  proScore?: number;
  conScore?: number;
  winner?: 'PRO' | 'CON' | 'INCONCLUSIVE' | 'FAILED';
  verdictType?: 'DECISIVE_PRO' | 'DECISIVE_CON' | 'DRAW' | 'INCONCLUSIVE' | 'FAILED';
  proCriteriaScores?: Record<string, CriterionScoreDetail>;
  conCriteriaScores?: Record<string, CriterionScoreDetail>;
  decisiveArguments?: string[];
  unsupportedClaims?: string[];
  citationAssessments?: CitationAssessmentItem[];
  confidence?: number;
}

export interface DebateSession {
  id: string;
  topic: string;
  createdAt: string;
  status: DebateStatus;
  config: DebateConfig;
  rounds: DebateRound[];
  synthesis?: DebateSynthesis;
  errorMessage?: string;
  error_message?: string;
  documentId?: string;
  documentName?: string;
  documentType?: string;
  sourceScope?: string;
  evidenceMode?: boolean;
  completedAt?: string;
  startedAtEpochMs?: number;
  completedAtEpochMs?: number;
  startedAtIso?: string;
  elapsedSeconds?: number;
  researchSources?: ResearchSource[];
}

export interface StartDebateRequest {
  topic: string;
  debaterAModel: string;
  debaterBModel: string;
  judgeModel: string;
  judgeProvider?: 'gemini' | 'nvidia';
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
  startedAtEpochMs?: number;
  startedAtIso?: string;
  elapsedSeconds?: number;
}

export interface DebateAttempt {
  attemptNumber: number;
  debateId: string;
  status?: string;
  createdAt: string;
  completedAt?: string;
  winner?: 'PRO' | 'CON' | 'INCONCLUSIVE' | 'FAILED' | string;
  proScore?: number;
  conScore?: number;
  roundsCount: number;
  speechesCount: number;
  judgeModel?: string;
  judgeProvider?: string;
  sourceScope?: string;
}

export interface GroupedDebateHistoryItem {
  groupKey: string;
  topic: string;
  id?: string;
  status?: string;
  createdAt?: string;
  completedAt?: string;
  winner?: 'PRO' | 'CON' | 'INCONCLUSIVE' | 'FAILED' | string;
  proScore?: number;
  conScore?: number;
  roundsCount?: number;
  messagesCount?: number;
  documentId?: string;
  documentName?: string;
  sourceScope?: string;
  totalAttempts: number;
  latestCompletedAt?: string;
  latestWinner?: 'PRO' | 'CON' | 'INCONCLUSIVE' | 'FAILED' | string;
  latestProScore?: number;
  latestConScore?: number;
  latestRoundsCount: number;
  latestSpeechesCount: number;
  attempts: DebateAttempt[];
}

export interface DebateHistoryItem {
  id: string;
  topic: string;
  createdAt: string;
  roundsCount: number;
  status: DebateStatus;
  documentName?: string;
  documentId?: string;
  winner?: 'PRO' | 'CON' | 'INCONCLUSIVE' | 'FAILED' | string;
  proScore?: number;
  conScore?: number;
  judgeModel?: string;
  judgeProvider?: string;
  messagesCount?: number;
  completedAt?: string;
}

export interface DebateHistoryResponse {
  groups: GroupedDebateHistoryItem[];
  items?: (GroupedDebateHistoryItem | DebateHistoryItem | any)[];
  totalGroups: number;
  totalCompletedDebates: number;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface DebateStreamEvent {
  event: 'turn' | 'evidence' | 'evaluation' | 'synthesis' | 'status';
  data: Record<string, unknown>;
}

export interface ShowcaseArgument {
  speaker: 'PRO' | 'CON';
  roundNumber: number;
  roundLabel: string;
  title: string;
  content: string;
  evidence?: string;
  pageCitation?: string;
  confidence?: number;
}

export interface ShowcaseDebate {
  id: string;
  topic: string;
  createdAt: string;
  documentName?: string | null;
  documentId?: string | null;
  isReal: boolean;
  roundsCount: number;
  proArguments: ShowcaseArgument[];
  conArguments: ShowcaseArgument[];
  judgeWinner: 'PRO' | 'CON' | 'DRAW' | 'TIE' | 'INCONCLUSIVE' | string;
  judgeProScore?: number | null;
  judgeConScore?: number | null;
  judgeReasoning?: string | null;
  judgeVerdict?: string | null;
  judgeModel?: string | null;
  judgeProvider?: string | null;
}

export interface ShowcaseResponse {
  debates: ShowcaseDebate[];
  totalAvailable: number;
}

export interface ResearchSource {
  id: string;
  title: string;
  url: string;
  snippet: string;
  publishedDate?: string;
  retrievalTimestamp?: string;
}

export interface ResearchEvidenceItem {
  id: string;
  claim: string;
  source: string;
  url?: string;
  publishedDate?: string;
}

export interface ResearchStage {
  id: string;
  name: string;
  status: 'completed' | 'in_progress' | 'pending' | 'failed';
  detail?: string;
}

export interface ResearchResponse {
  topic: string;
  query: string;
  sources: ResearchSource[];
  evidenceItems: ResearchEvidenceItem[];
  stages: ResearchStage[];
  indexedChunks: number;
  status: 'completed' | 'empty' | 'failed';
  message: string;
}

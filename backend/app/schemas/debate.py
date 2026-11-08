from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator

DebaterPosition = Literal["PRO", "CON"]
DebateStatus = Literal[
    "idle", "configuring", "queued", "running", "debating", "verifying", "evaluating", "synthesizing", "completed", "failed", "evaluation_failed", "cancelled"
]

class EvidenceItemSchema(BaseModel):
    id: str
    claim: str
    source: str
    url: Optional[str] = None
    verdict: Literal["supported", "contradicted", "unverifiable"] = "supported"
    confidenceScore: float = 90.0
    page: Optional[int] = None
    section: Optional[str] = None
    content: Optional[str] = None  # Genuine PDF passage for "View Source"
    relevanceScore: Optional[float] = None
    relevanceExplanation: Optional[str] = None

class GroundedEvidenceReference(BaseModel):
    chunk_id: Optional[str] = None
    source: str = "Document"
    page: Optional[int] = None
    section: Optional[str] = None
    excerpt: Optional[str] = None  # Genuine PDF passage
    relevance_score: Optional[float] = None
    relevance_explanation: Optional[str] = None
    verdict: Optional[str] = "supported"

class GroundedTurnPayload(BaseModel):
    argument_title: str
    argument_text: str  # The LLM's own synthesized argument in its own words
    main_claim: str
    reasoning_summary: str
    evidence_references: List[GroundedEvidenceReference] = []
    limitations: Optional[str] = None

class DebateConfigSchema(BaseModel):
    topic: str
    debaterAModel: str = "gemma-4-E4B-Q4_0"
    debaterBModel: str = "Qwen2.5-VL-7B-Instruct"
    judgeModel: str = "gemini-3.5-flash"
    judgeProvider: Optional[str] = "gemini"
    rounds: int = 3
    evidenceMode: bool = True
    strictFactChecking: Optional[bool] = True
    documentId: Optional[str] = None
    documentName: Optional[str] = None
    documentType: Optional[str] = None
    sourceScope: Optional[str] = "document"

class DebateTurnSchema(BaseModel):
    speaker: Literal["DEBATER_A", "DEBATER_B", "JUDGE", "SYNTHESIZER", "PRO", "CON"]
    role: Optional[DebaterPosition] = "PRO"
    content: str
    timestamp: str
    title: Optional[str] = ""
    confidence: Optional[float] = 90.0
    evidence: Optional[List[EvidenceItemSchema]] = []
    mainClaim: Optional[str] = None
    reasoningSummary: Optional[str] = None
    limitations: Optional[str] = None
    executionStatus: Optional[Literal["REAL_LOCAL_MODEL", "REAL_REMOTE_API", "SIMULATED"]] = "SIMULATED"

class DebateRoundSchema(BaseModel):
    roundNumber: int
    turns: List[DebateTurnSchema]

class DebateSynthesisSchema(BaseModel):
    summary: str
    keyConsensus: List[str] = []
    keyContentions: List[str] = []
    evidenceReliabilityScore: float = 85.0
    balancedVerdict: str
    judgeModelUsed: Optional[str] = "gemini-3.5-flash"
    judgeProvider: Optional[str] = "gemini"
    isFallback: Optional[bool] = False
    executionStatus: Optional[Literal["REAL_REMOTE_API", "SIMULATED"]] = "SIMULATED"
    proScore: Optional[float] = None
    conScore: Optional[float] = None
    winner: Optional[str] = None
    verdictType: Optional[str] = None
    proCriteriaScores: Optional[Dict[str, Any]] = None
    conCriteriaScores: Optional[Dict[str, Any]] = None
    decisiveArguments: Optional[List[str]] = None
    unsupportedClaims: Optional[List[str]] = None
    citationAssessments: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None

class DebateSessionSchema(BaseModel):
    id: str
    topic: str
    createdAt: str
    startedAtEpochMs: Optional[int] = None
    completedAtEpochMs: Optional[int] = None
    startedAtIso: Optional[str] = None
    elapsedSeconds: Optional[int] = None
    status: str
    config: DebateConfigSchema
    rounds: List[DebateRoundSchema]
    synthesis: Optional[DebateSynthesisSchema] = None
    errorMessage: Optional[str] = None
    documentId: Optional[str] = None
    documentName: Optional[str] = None
    documentType: Optional[str] = None
    sourceScope: Optional[str] = None
    evidenceMode: Optional[bool] = None
    completedAt: Optional[str] = None
    researchSources: Optional[List[Dict[str, Any]]] = None
    performanceMetrics: Optional[Dict[str, Any]] = None

class StartDebateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Debate proposition")
    debaterAModel: Optional[str] = "gemma-4-E4B-Q4_0"
    debaterBModel: Optional[str] = "Qwen2.5-VL-7B-Instruct"
    judgeModel: Optional[str] = "gemini-3.5-flash"
    judgeProvider: Optional[str] = "gemini"
    rounds: Optional[int] = 3
    evidenceMode: Optional[bool] = True
    strictFactChecking: Optional[bool] = True
    documentId: Optional[str] = None
    sourceScope: Optional[str] = "document"
    researchTimings: Optional[Dict[str, Any]] = None

    @field_validator("rounds")
    @classmethod
    def validate_rounds(cls, v: Optional[int]) -> int:
        if v is None:
            return 3
        if v not in (1, 3, 5):
            if v <= 1:
                return 1
            elif v <= 3:
                return 3
            else:
                return 5
        return v

    @field_validator("topic")
    @classmethod
    def validate_topic_not_empty_or_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Debate topic cannot be empty or whitespace-only.")
        return v.strip()

class StartDebateResponse(BaseModel):
    debateId: str
    status: str
    message: str
    startedAtEpochMs: Optional[int] = None
    startedAtIso: Optional[str] = None

class DebateAttemptSchema(BaseModel):
    attemptNumber: int
    debateId: str
    status: Optional[str] = "completed"
    createdAt: str
    completedAt: Optional[str] = None
    winner: Optional[str] = None
    proScore: Optional[float] = None
    conScore: Optional[float] = None
    roundsCount: int
    speechesCount: int
    judgeModel: Optional[str] = None
    judgeProvider: Optional[str] = None
    sourceScope: Optional[str] = "document"

class GroupedDebateHistoryItemSchema(BaseModel):
    groupKey: str
    topic: str
    id: Optional[str] = None
    status: str = "completed"
    createdAt: Optional[str] = None
    documentId: Optional[str] = None
    documentName: Optional[str] = None
    sourceScope: Optional[str] = "document"
    totalAttempts: int
    latestCompletedAt: Optional[str] = None
    latestWinner: Optional[str] = None
    winner: Optional[str] = None
    latestProScore: Optional[float] = None
    latestConScore: Optional[float] = None
    latestRoundsCount: int
    roundsCount: Optional[int] = None
    latestSpeechesCount: int
    attempts: List[DebateAttemptSchema]

class DebateHistoryItemSchema(BaseModel):
    id: str
    topic: str
    createdAt: str
    roundsCount: int
    status: str
    documentName: Optional[str] = None
    documentId: Optional[str] = None
    sourceScope: Optional[str] = "document"
    winner: Optional[str] = None
    proScore: Optional[float] = None
    conScore: Optional[float] = None
    judgeModel: Optional[str] = None
    judgeProvider: Optional[str] = None
    messagesCount: Optional[int] = 0
    completedAt: Optional[str] = None

class DebateHistoryResponse(BaseModel):
    groups: List[GroupedDebateHistoryItemSchema] = []
    items: List[GroupedDebateHistoryItemSchema] = []
    totalGroups: int
    totalCompletedDebates: int
    total: int
    page: int
    pageSize: int
    totalPages: int

class DeleteGroupRequest(BaseModel):
    groupKey: Optional[str] = None
    debateIds: Optional[List[str]] = None
    topic: Optional[str] = None
    documentId: Optional[str] = None

class DeleteResponse(BaseModel):
    status: str
    message: str
    deletedId: Optional[str] = None
    deletedCount: Optional[int] = None

class ShowcaseArgumentSchema(BaseModel):
    speaker: str
    roundNumber: int
    roundLabel: str
    title: str
    content: str
    evidence: Optional[str] = None
    pageCitation: Optional[str] = None
    confidence: Optional[float] = None

class ShowcaseDebateSchema(BaseModel):
    id: str
    topic: str
    createdAt: str
    documentName: Optional[str] = None
    documentId: Optional[str] = None
    isReal: bool = True
    roundsCount: int
    proArguments: List[ShowcaseArgumentSchema]
    conArguments: List[ShowcaseArgumentSchema]
    judgeWinner: str
    judgeProScore: Optional[float] = None
    judgeConScore: Optional[float] = None
    judgeReasoning: Optional[str] = None
    judgeVerdict: Optional[str] = None
    judgeModel: Optional[str] = None
    judgeProvider: Optional[str] = None

class ShowcaseResponse(BaseModel):
    debates: List[ShowcaseDebateSchema]
    totalAvailable: int

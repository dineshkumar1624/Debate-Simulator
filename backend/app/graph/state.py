from typing import TypedDict, List, Dict, Any, Optional

class DebateGraphState(TypedDict):
    debate_id: str
    topic: str
    document_ids: List[str]
    source_scope: str # 'document' or 'general_topic'
    current_round: int
    max_rounds: int
    current_speaker: str # 'PRO' or 'CON'
    
    # Evidence Contexts
    current_pro_evidence: List[Dict[str, Any]]
    current_con_evidence: List[Dict[str, Any]]
    pro_evidence_context: str
    con_evidence_context: str
    
    # Turn payloads
    current_pro_turn: Optional[Dict[str, Any]]
    current_con_turn: Optional[Dict[str, Any]]
    latest_pro_argument: Optional[str]
    latest_con_argument: Optional[str]
    con_max_tokens: Optional[int]
    
    # Authoritative Transcript
    transcript: List[Dict[str, Any]]
    
    # Intelligent Debate Context Management
    permanent_context: Optional[str]
    rolling_summary: Optional[Dict[str, Any]]
    telemetry: Optional[List[Dict[str, Any]]]
    
    # Final Judge Evaluation
    judge_provider: Optional[str] # 'gemini' or 'nvidia'
    judge_model: Optional[str]
    judge_report: Optional[Dict[str, Any]]
    
    # Execution Tracking
    status: str
    error: Optional[str]
    resume_target: Optional[str]
    winner: Optional[str]

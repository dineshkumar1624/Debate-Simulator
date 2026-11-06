from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RollingDebateSummary(BaseModel):
    """
    Compact, structured summary of debate rounds generated after each completed round.
    Preserves dialectical clash points, claims, and verified evidence IDs without bloating prompts.
    """
    round_completed: int = Field(..., description="The round number just completed")
    pro_core_thesis: str = Field(..., description="Core affirmative proposition framework")
    pro_key_claims: List[str] = Field(default_factory=list, description="Key affirmative claims established")
    con_core_thesis: str = Field(..., description="Core opposition counter-thesis")
    con_key_objections: List[str] = Field(default_factory=list, description="Key negative clash points and objections")
    challenged_claims: List[str] = Field(default_factory=list, description="Specific assertions challenged by opponent")
    defended_arguments: List[str] = Field(default_factory=list, description="Arguments defended with evidentiary citations")
    unresolved_disagreements: List[str] = Field(default_factory=list, description="Active points of contention for upcoming rounds")
    evidence_discussed: List[str] = Field(default_factory=list, description="Evidence IDs/citations referenced (e.g. [p.8 Table 2])")
    remaining_inquiries: List[str] = Field(default_factory=list, description="Open empirical or architectural questions to address")
    is_valid: bool = Field(default=True, description="Whether the summary passed structural and factual validation")

class PermanentContextPayload(BaseModel):
    """
    Invariant permanent context preserved across all debate rounds.
    """
    topic: str
    source_scope: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    document_page_count: Optional[int] = None
    core_evidence_items: List[Dict[str, Any]] = Field(default_factory=list)
    key_benchmarks: List[str] = Field(default_factory=list)


from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class SectionSummarySchema(BaseModel):
    section_id: str
    section_title: str
    page_start: int
    page_end: int
    summary: str
    key_takeaway: str
    topics_covered: List[str] = Field(default_factory=list)

class ConceptDefinitionSchema(BaseModel):
    concept: str
    definition: str
    page_number: int
    section_title: str
    mathematical_formulation: Optional[str] = None

class FactFindingSchema(BaseModel):
    fact_statement: str
    metric_or_data: str
    page_number: int
    section_title: str
    evidence_type: str = "benchmark"  # "benchmark", "complexity", "architecture", "training", "ablation"

class ArgumentThesisSchema(BaseModel):
    claim: str
    reasoning: str
    evidence_pages: List[int] = Field(default_factory=list)
    addressed_counterargument: Optional[str] = None

class CrossSectionRelationSchema(BaseModel):
    source_section: str
    target_section: str
    relation_type: str = "implements"  # "implements", "substantiates", "contrasts", "validates", "previews"
    explanation: str
    source_pages: List[int] = Field(default_factory=list)
    target_pages: List[int] = Field(default_factory=list)

class DocumentKnowledgeRepresentation(BaseModel):
    document_id: str
    document_name: str
    total_pages: int
    executive_summary: str
    sections: List[SectionSummarySchema] = Field(default_factory=list)
    concepts: List[ConceptDefinitionSchema] = Field(default_factory=list)
    facts: List[FactFindingSchema] = Field(default_factory=list)
    arguments: List[ArgumentThesisSchema] = Field(default_factory=list)
    cross_section_relations: List[CrossSectionRelationSchema] = Field(default_factory=list)
    unsupported_claims_boundary: List[str] = Field(default_factory=list)

class DocumentQueryResponseSchema(BaseModel):
    query: str
    is_supported: bool
    support_verdict: Literal["SUPPORTED", "CONTRADICTED", "NOT_SUPPORTED"]
    answer: str
    retrieved_sections: List[str] = Field(default_factory=list)
    retrieved_pages: List[int] = Field(default_factory=list)
    knowledge_sources: List[str] = Field(default_factory=list)  # ["document_knowledge", "original_chunks"]
    evidence_excerpts: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0


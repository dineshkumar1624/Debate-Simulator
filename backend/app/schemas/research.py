from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ResearchStageSchema(BaseModel):
    id: str
    name: str
    status: str # "completed", "in_progress", "pending", "failed"
    detail: Optional[str] = None

class ResearchEvidenceItem(BaseModel):
    id: str
    claim: str
    source: str
    url: Optional[str] = None
    page: Optional[int] = None
    contentType: Optional[str] = None
    publishedDate: Optional[str] = None

class ResearchSourceSchema(BaseModel):
    id: str
    title: str
    url: str
    snippet: str
    publishedDate: Optional[str] = None
    retrievalTimestamp: str
    contentType: Optional[str] = "SEARCH_SNIPPET_ONLY" # "FULL_PDF_TEXT", "FULL_HTML_ARTICLE", "SEARCH_SNIPPET_ONLY"
    pageCount: Optional[int] = None
    pagesExtracted: Optional[int] = None
    contentHash: Optional[str] = None

class ResearchRequest(BaseModel):
    topic: str
    max_sources: Optional[int] = 5
    debate_id: Optional[str] = None

class ResearchResponse(BaseModel):
    topic: str
    query: str
    sources: List[ResearchSourceSchema]
    evidenceItems: List[ResearchEvidenceItem] = []
    stages: List[ResearchStageSchema] = []
    indexedChunks: int
    status: str = "completed" # "completed", "empty", "failed"
    message: str = "Web evidence gathered and indexed"
    timings: Optional[Dict[str, Any]] = None

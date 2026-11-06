from typing import List, Optional
from pydantic import BaseModel, Field

class DirectTextInputRequest(BaseModel):
    title: Optional[str] = Field("Direct Text Input", description="Title or identifier for the direct text input")
    content: str = Field(..., min_length=1, description="Raw text content to ingest")

class EvidenceReferenceSchema(BaseModel):
    id: str
    documentId: str
    documentName: str
    pageNumber: int
    sectionTitle: str
    excerpt: str
    type: str = "evidence"  # claim, evidence, limitation, counterargument, assumption, uncertainty
    relevanceScore: float = 85.0
    speakerTarget: Optional[str] = None  # PRO or CON

class DocumentSectionSchema(BaseModel):
    id: str
    title: str
    pageNumber: int
    wordCount: int = 0
    claimsCount: int = 0
    summary: str = ""

class DocumentMetadataSchema(BaseModel):
    id: str
    name: str
    fileSize: str = "0 B"
    fileSizeBytes: int = 0
    fileType: str = "pdf"
    pageCount: int = 1
    uploadedAt: str
    status: str = "ready"
    summary: str = ""
    keyClaimsCount: int = 0
    evidencePointsCount: int = 0
    debatesCount: int = 0
    sections: List[DocumentSectionSchema] = []
    suggestedQuestions: List[str] = []

class DocumentUploadResponse(BaseModel):
    document: DocumentMetadataSchema
    message: str = "Document successfully ingested and indexed"

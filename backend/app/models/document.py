import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from ..database.session import Base

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False, default="pdf")
    file_size = Column(String(64), default="0 B")
    file_size_bytes = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    status = Column(String(64), default="ready") # idle, uploading, reading, ready, error
    summary = Column(Text, default="")
    key_claims_count = Column(Integer, default=0)
    evidence_points_count = Column(Integer, default=0)
    debates_count = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")
    debates = relationship("DebateModel", back_populates="document")


class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    page_number = Column(Integer, default=1)
    section_title = Column(String(255), default="General")
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("DocumentModel", back_populates="chunks")

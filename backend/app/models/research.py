import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON
from ..database.session import Base

class ResearchSourceModel(Base):
    __tablename__ = "research_sources"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    debate_id = Column(String(64), nullable=True, index=True)
    topic = Column(String(255), nullable=False)
    query = Column(String(255), nullable=False)
    title = Column(String(255), default="")
    url = Column(String(1024), default="")
    content = Column(Text, default="")
    published_date = Column(String(64), nullable=True)
    metadata_json = Column(JSON, default=dict)
    retrieval_timestamp = Column(DateTime, default=datetime.utcnow)

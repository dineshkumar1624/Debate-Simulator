import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, foreign
from ..database.session import Base

class DebateModel(Base):
    __tablename__ = "debates"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(Text, nullable=False)
    debater_a_model = Column(String(128), default="gemma-4-E4B-Q4_0")
    debater_b_model = Column(String(128), default="Qwen2.5-VL-7B-Instruct")
    judge_model = Column(String(128), default="gemini-3.5-flash")
    judge_provider = Column(String(64), default="gemini")
    rounds = Column(Integer, default=3)
    evidence_mode = Column(Boolean, default=True)
    strict_fact_checking = Column(Boolean, default=True)
    source_scope = Column(String(64), default="document") # 'document' or 'general_topic'
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(64), default="idle") # idle, configuring, debating, verifying, evaluating, synthesizing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("DocumentModel", back_populates="debates")
    round_records = relationship("DebateRoundModel", back_populates="debate", cascade="all, delete-orphan", order_by="DebateRoundModel.round_number")
    messages = relationship("DebateMessageModel", back_populates="debate", cascade="all, delete-orphan", order_by="DebateMessageModel.created_at")
    evaluation = relationship("JudgeEvaluationModel", back_populates="debate", uselist=False, cascade="all, delete-orphan")
    research_sources = relationship("ResearchSourceModel", primaryjoin="DebateModel.id == foreign(ResearchSourceModel.debate_id)", cascade="all, delete-orphan", lazy="select")


class DebateRoundModel(Base):
    __tablename__ = "debate_rounds"
    __table_args__ = (
        UniqueConstraint("debate_id", "round_number", name="uq_debate_round_number"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    debate_id = Column(String(64), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(Integer, nullable=False)
    status = Column(String(64), default="completed") # in_progress, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    debate = relationship("DebateModel", back_populates="round_records")


class DebateMessageModel(Base):
    __tablename__ = "debate_messages"
    __table_args__ = (
        UniqueConstraint("debate_id", "round_number", "role", name="uq_debate_message_round_role"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    debate_id = Column(String(64), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(Integer, nullable=False)
    speaker = Column(String(32), nullable=False) # 'DEBATER_A', 'DEBATER_B', 'PRO', 'CON'
    role = Column(String(32), default="PRO")      # 'PRO' or 'CON'
    title = Column(String(255), default="")
    content = Column(Text, nullable=False)
    confidence = Column(Float, default=90.0)
    evidence_references = Column(JSON, default=list) # List of EvidenceItem
    created_at = Column(DateTime, default=datetime.utcnow)

    debate = relationship("DebateModel", back_populates="messages")


class JudgeEvaluationModel(Base):
    __tablename__ = "judge_evaluations"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    debate_id = Column(String(64), ForeignKey("debates.id", ondelete="CASCADE"), unique=True, nullable=False)
    pro_score = Column(Float, nullable=False, default=0.0)
    con_score = Column(Float, nullable=False, default=0.0)
    winner = Column(String(32), nullable=False, default="INCONCLUSIVE") # 'PRO', 'CON', 'INCONCLUSIVE', 'FAILED'
    status = Column(String(32), default="completed") # 'completed' or 'failed'
    pro_strengths = Column(JSON, default=list)
    pro_weaknesses = Column(JSON, default=list)
    con_strengths = Column(JSON, default=list)
    con_weaknesses = Column(JSON, default=list)
    key_points = Column(JSON, default=list)
    judge_reasoning = Column(Text, default="")
    balanced_verdict = Column(Text, default="")
    evidence_reliability_score = Column(Float, default=85.0)
    raw_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    debate = relationship("DebateModel", back_populates="evaluation")

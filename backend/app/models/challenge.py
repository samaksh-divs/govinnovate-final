"""Challenge, requirement, KPI, pilot-criteria and AI-suggestion models."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.user import utcnow


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    department = Column(String, default="")
    problem_category = Column(String, default="")
    problem_statement = Column(Text, default="")
    current_situation = Column(Text, default="")
    affected_population = Column(String, default="")
    existing_process = Column(Text, default="")
    current_limitations = Column(Text, default="")
    expected_outcome = Column(Text, default="")
    geographic_scope = Column(String, default="")
    constraints = Column(Text, default="")
    priority = Column(String, default="MEDIUM")
    status = Column(String, default="DRAFT", index=True)  # DRAFT | PUBLISHED | CLOSED | ARCHIVED
    budget_min = Column(Float, default=0)
    budget_max = Column(Float, default=0)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    published_at = Column(DateTime, nullable=True)

    requirements = Column(JSON, default=dict)  # functional/technical/security/data requirement lists
    pilot_criteria = Column(JSON, default=dict)
    data_policy = Column(JSON, default=dict)
    ip_policy = Column(JSON, default=dict)
    cybersecurity = Column(JSON, default=dict)
    risks = Column(JSON, default=list)


class Kpi(Base):
    """KPI definitions live on a challenge (pre-pilot) and are cloned into pilots."""

    __tablename__ = "kpis"

    id = Column(String, primary_key=True)
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=True, index=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    baseline = Column(String, default="")
    target = Column(String, default="")
    unit = Column(String, default="")
    measurement_method = Column(String, default="")
    evidence_source = Column(String, default="")
    success_threshold = Column(String, default="")
    direction = Column(String, default="reduce")  # reduce | increase
    source = Column(String, default="OFFICER")  # OFFICER | AI_ACCEPTED
    created_at = Column(DateTime, default=utcnow)


class AiSuggestion(Base):
    """AI Requirement Engine output. Nothing becomes official until explicitly accepted."""

    __tablename__ = "ai_suggestions"

    id = Column(String, primary_key=True)
    challenge_id = Column(String, ForeignKey("challenges.id"), index=True, nullable=False)
    suggestion_type = Column(String, nullable=False)  # requirement | kpi
    category = Column(String, default="")  # functional | technical | security | data | kpi
    text = Column(Text, default="")
    rationale = Column(Text, default="")
    confidence = Column(Float, default=0.5)
    extra = Column(JSON, default=dict)
    status = Column(String, default="PENDING")  # PENDING | ACCEPTED | REJECTED | EDITED
    edited_text = Column(Text, nullable=True)
    decided_by = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

"""Startup registry models."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.user import utcnow


class Startup(Base):
    __tablename__ = "startups"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    sector = Column(String, default="")
    description = Column(Text, default="")
    technology = Column(JSON, default=list)
    problem_areas = Column(JSON, default=list)
    hq_location = Column(String, default="")
    founded_year = Column(String, default="")
    team_size = Column(Integer, default=0)
    stage = Column(String, default="")
    dpiit_registered = Column(Boolean, default=False)
    experience_years = Column(Integer, default=0)
    previous_pilots = Column(JSON, default=list)
    evidence_summary = Column(JSON, default=dict)
    eligibility = Column(JSON, default=dict)
    scalability = Column(JSON, default=dict)
    risk_profile = Column(JSON, default=dict)
    relevant_projects = Column(JSON, default=list)
    pricing = Column(String, default="")
    is_demo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class StartupMatch(Base):
    """Explainable match result. Match Score ≠ Evidence Confidence: stored separately."""

    __tablename__ = "startup_matches"

    id = Column(String, primary_key=True)
    challenge_id = Column(String, ForeignKey("challenges.id"), index=True, nullable=False)
    startup_id = Column(String, ForeignKey("startups.id"), index=True, nullable=False)
    match_score = Column(Float, nullable=False)
    component_scores = Column(JSON, default=dict)
    explanations = Column(JSON, default=list)
    evidence_confidence = Column(String, default="LOW")  # HIGH | MEDIUM | LOW (separate concept)
    eligibility_status = Column(String, default="INCOMPLETE")
    rank = Column(Integer, default=0)
    overridden = Column(Boolean, default=False)
    override_reason = Column(String, nullable=True)
    run_version = Column(String, default="matching-engine@1.3")
    created_at = Column(DateTime, default=utcnow)

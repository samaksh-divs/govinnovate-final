"""Decision versions, scale-up, procurement, re-pilot and knowledge models."""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.user import utcnow


class DecisionRecommendation(Base):
    """Decision Intelligence output. Explainable and versioned; never a government decision."""

    __tablename__ = "decision_recommendations"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    outcome = Column(String, nullable=False)  # SCALE | RE_PILOT | REJECT | INSUFFICIENT_EVIDENCE
    confidence = Column(Float, default=0)
    reasons = Column(JSON, default=list)
    supporting_evidence = Column(JSON, default=list)
    missing_evidence = Column(JSON, default=list)
    risk_flags = Column(JSON, default=list)
    factor_scores = Column(JSON, default=dict)
    engine_version = Column(String, default="decision-engine@1.4")
    created_at = Column(DateTime, default=utcnow)


class GovernmentDecision(Base):
    """The authoritative human decision. Overrides append; history is never overwritten."""

    __tablename__ = "government_decisions"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    recommendation_id = Column(String, nullable=True)
    ai_outcome = Column(String, default="")
    decision = Column(String, nullable=False)  # SCALE | RE_PILOT | REJECT | INSUFFICIENT_EVIDENCE
    decision_type = Column(String, default="ALIGNED")  # ALIGNED | OVERRIDE
    reason = Column(Text, nullable=False)
    decided_by = Column(String, nullable=False)
    decided_by_name = Column(String, default="")
    decided_at = Column(DateTime, default=utcnow)


class ScaleUpPlan(Base):
    __tablename__ = "scaleup_plans"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    decision_id = Column(String, nullable=True)
    status = Column(String, default="DRAFT")  # DRAFT | SUBMITTED | APPROVED
    pilot_scope = Column(JSON, default=dict)
    scale_scope = Column(JSON, default=dict)
    new_kpis = Column(JSON, default=list)
    operational_risks = Column(JSON, default=list)
    cybersecurity_plan = Column(JSON, default=dict)
    support_requirements = Column(JSON, default=list)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class ProcurementPackage(Base):
    __tablename__ = "procurement_packages"

    id = Column(String, primary_key=True)
    scaleup_id = Column(String, ForeignKey("scaleup_plans.id"), index=True, nullable=False)
    pilot_id = Column(String, index=True, nullable=False)
    status = Column(String, default="DRAFT_NOT_LEGALLY_BINDING")
    content = Column(JSON, default=dict)  # requirements summary, KPIs, evidence, findings, lessons...
    generated_at = Column(DateTime, default=utcnow)
    generated_by = Column(String, nullable=False)


class RepilotPlan(Base):
    __tablename__ = "repilot_plans"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    decision_id = Column(String, nullable=True)
    new_pilot_id = Column(String, nullable=True)
    status = Column(String, default="PLANNED")  # PLANNED | PILOT_CREATED
    carried_forward = Column(JSON, default=dict)
    scope_changes = Column(JSON, default=dict)
    required_changes = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)


class KnowledgeLesson(Base):
    __tablename__ = "knowledge_lessons"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, nullable=True, index=True)
    challenge_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    lesson = Column(Text, nullable=False)
    evidence = Column(Text, default="")
    recommendation = Column(Text, default="")
    sector = Column(String, default="")
    problem_type = Column(String, default="")
    technology = Column(String, default="")
    source = Column(String, default="KNOWLEDGE_ENGINE")  # KNOWLEDGE_ENGINE | OFFICER
    tags = Column(JSON, default=list)
    status = Column(String, default="PENDING")  # PENDING | ACCEPTED | EDITED | IGNORED
    edited_lesson = Column(Text, nullable=True)
    decided_by = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class SimilarPilot(Base):
    """Demo historical pilots used by the similarity recommender."""

    __tablename__ = "similar_pilots"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String, default="")
    sector = Column(String, default="")
    problem_type = Column(String, default="")
    technology = Column(String, default="")
    kpi_focus = Column(String, default="")
    pilot_size = Column(String, default="")
    evidence_quality = Column(String, default="MEDIUM")
    outcome = Column(String, default="")
    year = Column(String, default="")
    summary = Column(Text, default="")
    lessons = Column(JSON, default=list)

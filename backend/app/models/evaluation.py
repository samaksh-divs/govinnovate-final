"""Expert assignment, COI declaration and versioned evaluation models."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.core.database import Base
from app.models.user import utcnow


class ExpertAssignment(Base):
    __tablename__ = "expert_assignments"
    __table_args__ = (UniqueConstraint("challenge_id", "startup_id", "expert_id", name="uq_assignment"),)

    id = Column(String, primary_key=True)
    challenge_id = Column(String, ForeignKey("challenges.id"), index=True, nullable=False)
    startup_id = Column(String, ForeignKey("startups.id"), index=True, nullable=False)
    expert_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    status = Column(String, default="AWAITING_COI")
    # AWAITING_COI | COI_CLEARED | EVALUATION_SUBMITTED | RECUSED | REASSIGNED
    assigned_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class CoiDeclaration(Base):
    """Conflict of interest declaration. CONFIRMED_CONFLICT permanently recuses the expert."""

    __tablename__ = "coi_declarations"

    id = Column(String, primary_key=True)
    assignment_id = Column(String, ForeignKey("expert_assignments.id"), index=True, nullable=False)
    expert_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # NO_CONFLICT | POTENTIAL_CONFLICT | CONFIRMED_CONFLICT
    conflict_type = Column(String, default="")
    description = Column(Text, default="")
    declared_at = Column(DateTime, default=utcnow)


class Evaluation(Base):
    """Versioned expert evaluation; submissions are additive, never overwritten."""

    __tablename__ = "evaluations"

    id = Column(String, primary_key=True)
    assignment_id = Column(String, ForeignKey("expert_assignments.id"), index=True, nullable=False)
    challenge_id = Column(String, index=True, nullable=False)
    startup_id = Column(String, index=True, nullable=False)
    expert_id = Column(String, nullable=False)
    version = Column(Integer, default=1)
    scores = Column(JSON, default=dict)          # criterion -> {score, justification}
    weighted_total = Column(Float, default=0)
    recommendation = Column(String, default="")  # RECOMMEND_FOR_PILOT | ... | DO_NOT_RECOMMEND
    final_comments = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class EvaluationAggregate(Base):
    """Materialized multi-expert aggregation: avg/median/min/max/stddev + disagreement."""

    __tablename__ = "evaluation_aggregates"

    id = Column(String, primary_key=True)
    challenge_id = Column(String, index=True, nullable=False)
    startup_id = Column(String, index=True, nullable=False)
    evaluation_count = Column(Integer, default=0)
    average = Column(Float, nullable=True)
    median = Column(Float, nullable=True)
    minimum = Column(Float, nullable=True)
    maximum = Column(Float, nullable=True)
    stddev = Column(Float, nullable=True)
    criterion_disagreement = Column(JSON, default=dict)   # criterion -> spread
    disagreement_flag = Column(Boolean, default=False)    # HIGH EVALUATOR DISAGREEMENT
    recommendation = Column(String, default="AWAITING_EVALUATION")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

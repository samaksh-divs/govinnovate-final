"""Pilot, pilot KPI status, milestone and payment models."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.user import utcnow


class Pilot(Base):
    __tablename__ = "pilots"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String, default="")
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=True)
    startup_id = Column(String, ForeignKey("startups.id"), nullable=False)
    startup_name = Column(String, default="")
    officer_id = Column(String, nullable=False)
    status = Column(String, default="DRAFT", index=True)
    # DRAFT | PENDING_APPROVAL | READY_TO_START | ACTIVE | CONCLUDED | DECIDED | SCALED | RE_PILOT
    duration_weeks = Column(Integer, default=12)
    budget = Column(Float, default=0)
    objectives = Column(Text, default="")
    expected_outcome = Column(Text, default="")
    sites = Column(Integer, default=0)
    target_users = Column(String, default="")
    geographic_scope = Column(String, default="")
    success_criteria = Column(Text, default="")
    payment_conditions = Column(String, default="")
    baseline = Column(JSON, default=dict)          # metric, value, status, source, validated_at
    data_ip = Column(JSON, default=dict)
    cybersecurity = Column(JSON, default=dict)
    health = Column(String, default="N/A")         # GREEN | AMBER | RED | N/A
    health_explanation = Column(JSON, default=list)  # human-readable reasons
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class PilotKpi(Base):
    """KPI cloned into a pilot with live monitoring status and measured values."""

    __tablename__ = "pilot_kpis"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    baseline = Column(String, default="")
    target = Column(String, default="")
    unit = Column(String, default="")
    measurement_method = Column(String, default="")
    evidence_source = Column(String, default="")
    success_threshold = Column(String, default="")
    direction = Column(String, default="reduce")
    status = Column(String, default="NOT_STARTED")
    # NOT_STARTED | BASELINE_PENDING | BASELINE_VALIDATED | IN_PROGRESS | TARGET_ON_TRACK
    # | AT_RISK | TARGET_ACHIEVED | TARGET_NOT_ACHIEVED | INSUFFICIENT_DATA
    observed_value = Column(String, default="")
    claimed_value = Column(String, default="")   # startup claim, kept separate from observation
    progress_notes = Column(JSON, default=list)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    start_date = Column(String, default="")
    end_date = Column(String, default="")
    deliverable = Column(String, default="")
    kpi_dependency = Column(String, default="")
    payment_percentage = Column(Float, default=0)
    status = Column(String, default="NOT_STARTED")
    # NOT_STARTED | IN_PROGRESS | SUBMITTED | ACCEPTED | BLOCKED
    payment_status = Column(String, default="NOT_ELIGIBLE")
    # NOT_ELIGIBLE | PENDING_APPROVAL | APPROVED | RELEASED (simulated demo ledger)
    accepted_at = Column(DateTime, nullable=True)


class PaymentPlan(Base):
    __tablename__ = "payment_plans"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    total_budget = Column(Float, default=0)
    validates_to_100 = Column(Boolean, default=False)
    note = Column(String, default="Demo workflow only. No payment gateway is integrated; "
                                  "amounts are simulated ledger entries.")

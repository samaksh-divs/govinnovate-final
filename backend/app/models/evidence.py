"""Evidence, validation package, validator assignment, findings and report models."""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.user import utcnow


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    kpi_id = Column(String, nullable=True, index=True)
    evidence_type = Column(String, default="REPORT")  # REPORT | TELEMETRY | PHOTO | CERTIFICATE | LOG | OTHER
    title = Column(String, default="")
    description = Column(Text, default="")
    submitted_by = Column(String, nullable=False)
    submitted_by_name = Column(String, default="")
    submission_date = Column(DateTime, default=utcnow)
    file_name = Column(String, default="")
    file_size = Column(Integer, default=0)
    mime_type = Column(String, default="")
    sha256 = Column(String, default="", index=True)
    storage_path = Column(String, default="")
    version = Column(Integer, default=1)
    replaces_id = Column(String, nullable=True)
    status = Column(String, default="UPLOADED", index=True)
    # UPLOADED | UNDER_REVIEW | ACCEPTED_FOR_MONITORING | READY_FOR_VALIDATION | VALIDATED
    # | NEEDS_CLARIFICATION | REJECTED | PARTIALLY_VALIDATED | NOT_VALIDATED | INSUFFICIENT_EVIDENCE
    claimed_value = Column(String, default="")   # what the submitter claims; NOT treated as truth
    review_note = Column(Text, default="")


class EvidenceVersion(Base):
    """Immutable version chain for evidence files."""

    __tablename__ = "evidence_versions"

    id = Column(String, primary_key=True)
    evidence_id = Column(String, ForeignKey("evidence.id"), index=True, nullable=False)
    version = Column(Integer, nullable=False)
    file_name = Column(String, default="")
    sha256 = Column(String, default="")
    uploaded_by = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=utcnow)
    note = Column(Text, default="")


class ValidationPackage(Base):
    __tablename__ = "validation_packages"

    id = Column(String, primary_key=True)
    pilot_id = Column(String, ForeignKey("pilots.id"), index=True, nullable=False)
    status = Column(String, default="PREPARED")
    # PREPARED | VALIDATOR_ASSIGNED | IN_VALIDATION | REPORT_SUBMITTED
    evidence_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)


class ValidatorAssignment(Base):
    __tablename__ = "validator_assignments"

    id = Column(String, primary_key=True)
    package_id = Column(String, ForeignKey("validation_packages.id"), index=True, nullable=False)
    validator_id = Column(String, nullable=False)
    validator_name = Column(String, default="")
    coi_status = Column(String, default="AWAITING_COI")  # AWAITING_COI | NO_CONFLICT | RECUSED
    status = Column(String, default="ASSIGNED")  # ASSIGNED | IN_PROGRESS | SUBMITTED | RECUSED
    assigned_at = Column(DateTime, default=utcnow)


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id = Column(String, primary_key=True)
    package_id = Column(String, ForeignKey("validation_packages.id"), index=True, nullable=False)
    kpi_id = Column(String, nullable=True)
    claimed = Column(String, default="")
    observed = Column(String, default="")
    validated_value = Column(String, default="")
    target = Column(String, default="")
    finding = Column(String, nullable=False)
    # SUPPORTED | PARTIALLY_SUPPORTED | NOT_SUPPORTED | INSUFFICIENT_EVIDENCE
    # | CONTRADICTORY_EVIDENCE | UNVERIFIABLE | UNKNOWN
    explanation = Column(Text, default="")
    evidence_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)


class ValidationReport(Base):
    __tablename__ = "validation_reports"

    id = Column(String, primary_key=True)
    package_id = Column(String, ForeignKey("validation_packages.id"), index=True, nullable=False)
    pilot_id = Column(String, index=True, nullable=False)
    validator_id = Column(String, nullable=False)
    summary = Column(Text, default="")
    overall_finding = Column(String, default="")
    validated_kpis = Column(JSON, default=dict)  # kpi_name -> validated value
    report_version = Column(Integer, default=1)
    sha256 = Column(String, default="")  # integrity digest of the report content
    created_at = Column(DateTime, default=utcnow)

"""Government public-data layer: sources, datasets, versioned snapshots, refresh log.

Separation of concerns (spec §Data Architecture):
  External Government Data  -> DataIngestion -> GovernmentDataset (versioned)
  GovInnovate workflow data -> existing workflow models (challenges/pilots/...)

The two are never silently mixed; every public figure carries provenance.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base


def _now():
    return datetime.utcnow()


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(String(64), primary_key=True)
    name = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=False)
    domain = Column(String(80))
    geography = Column(String(80))
    provider_type = Column(String(40), default="STATIC_SNAPSHOT")  # MSINS | OGD | DPIIT | STATIC_SNAPSHOT
    source_url = Column(String(500))
    license_note = Column(String(300))
    is_live_api = Column(Boolean, default=False)
    contact_note = Column(String(300))
    created_at = Column(DateTime, default=_now)


class GovernmentDataset(Base):
    """A logical dataset (e.g. 'DPIIT Recognized Startups by State')."""
    __tablename__ = "government_datasets"
    id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("data_sources.id"), nullable=False)
    title = Column(String(250), nullable=False)
    domain = Column(String(80))            # startup-ecosystem | policy | governance | problems
    geography = Column(String(80))         # Maharashtra | India | district
    data_type = Column(String(40), default="GOVERNMENT_PUBLIC_DATA")
    description = Column(Text)
    coverage_note = Column(Text)           # e.g. "district-level coverage unavailable"
    update_frequency = Column(String(60))
    last_updated = Column(DateTime)        # source's own as-of date (if known)
    retrieved_at = Column(DateTime, default=_now)
    record_count = Column(Integer, default=0)
    status = Column(String(30), default="SNAPSHOT")  # SNAPSHOT | IMPORTED | LIVE | UNAVAILABLE
    current_version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)


class DatasetVersion(Base):
    """Immutable snapshot of a dataset's payload. History is never overwritten."""
    __tablename__ = "dataset_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), ForeignKey("government_datasets.id"), nullable=False)
    version = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    record_count = Column(Integer, default=0)
    retrieved_at = Column(DateTime, default=_now)
    retrieved_by = Column(String(120), default="system-import")
    source_url = Column(String(500))
    checksum = Column(String(64))          # SHA-256 of canonical payload — integrity, not truth
    notes = Column(Text)


class DataRefreshLog(Base):
    __tablename__ = "data_refresh_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(64), ForeignKey("government_datasets.id"))
    provider = Column(String(60))
    outcome = Column(String(30))           # SUCCESS | SKIPPED | FAILED | SNAPSHOT_ONLY
    detail = Column(Text)
    duration_ms = Column(Integer)
    at = Column(DateTime, default=_now)

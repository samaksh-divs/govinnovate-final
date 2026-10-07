"""Evidence repository: secure upload, SHA-256 integrity, review workflow, versioning."""
import os
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.core.security import sha256_bytes
from app.models.evidence import Evidence, EvidenceVersion
from app.models.pilot import Pilot, PilotKpi
from app.models.user import User
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

STATUSES = ["UPLOADED", "UNDER_REVIEW", "ACCEPTED_FOR_MONITORING", "READY_FOR_VALIDATION",
            "VALIDATED", "NEEDS_CLARIFICATION", "REJECTED", "PARTIALLY_VALIDATED",
            "NOT_VALIDATED", "INSUFFICIENT_EVIDENCE"]
TRANSITIONS = {
    "UPLOADED": ["UNDER_REVIEW"],
    "UNDER_REVIEW": ["ACCEPTED_FOR_MONITORING", "NEEDS_CLARIFICATION", "REJECTED"],
    "NEEDS_CLARIFICATION": ["UNDER_REVIEW", "REJECTED"],
    "ACCEPTED_FOR_MONITORING": ["READY_FOR_VALIDATION"],
    "READY_FOR_VALIDATION": ["VALIDATED", "PARTIALLY_VALIDATED", "NOT_VALIDATED",
                             "INSUFFICIENT_EVIDENCE"],
}
REVIEW_TARGETS = {"ACCEPTED_FOR_MONITORING", "READY_FOR_VALIDATION", "NEEDS_CLARIFICATION", "REJECTED"}
VALIDATION_TARGETS = {"VALIDATED", "PARTIALLY_VALIDATED", "NOT_VALIDATED", "INSUFFICIENT_EVIDENCE"}


@router.get("")
def list_evidence(pilot_id: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(Evidence)
    if pilot_id:
        q = q.filter(Evidence.pilot_id == pilot_id)
    if user.role == "startup":
        own = {p.id for p in db.query(Pilot).filter(Pilot.startup_id == user.startup_id)}
        q = q.filter(Evidence.pilot_id.in_(own or {"__none__"}))
    rows = q.order_by(Evidence.submission_date.desc()).all()
    return [_out(e, db) for e in rows]


def _out(e: Evidence, db: Session) -> dict:
    kpi = db.query(PilotKpi).filter(PilotKpi.id == e.kpi_id).first() if e.kpi_id else None
    pilot = db.query(Pilot).filter(Pilot.id == e.pilot_id).first()
    versions = db.query(EvidenceVersion).filter(EvidenceVersion.evidence_id == e.id) \
        .order_by(EvidenceVersion.version).all()
    return {"id": e.id, "pilot_id": e.pilot_id, "pilot_name": pilot.name if pilot else None,
            "kpi_id": e.kpi_id, "kpi_name": kpi.name if kpi else None,
            "evidence_type": e.evidence_type, "title": e.title, "description": e.description,
            "submitted_by": e.submitted_by_name, "submission_date":
                e.submission_date.isoformat() if e.submission_date else None,
            "file_name": e.file_name, "file_size": e.file_size, "mime_type": e.mime_type,
            "sha256": e.sha256, "version": e.version, "status": e.status,
            "claimed_value": e.claimed_value, "review_note": e.review_note,
            "integrity_note": "SHA-256 proves file integrity (unchanged since upload), "
                              "NOT the truthfulness of the content.",
            "versions": [{"version": v.version, "file_name": v.file_name, "sha256": v.sha256,
                          "uploaded_at": v.uploaded_at.isoformat() if v.uploaded_at else None,
                          "note": v.note} for v in versions]}


@router.post("", status_code=201)
def upload_evidence(pilot_id: str = Form(...), kpi_id: str | None = Form(None),
                    evidence_type: str = Form("REPORT"), title: str = Form(...),
                    description: str = Form(""), claimed_value: str = Form(""),
                    file: UploadFile = File(...), db: Session = Depends(get_db),
                    user: User = Depends(require("EVIDENCE_SUBMIT"))):
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    if user.role == "startup" and p.startup_id != user.startup_id:
        raise HTTPException(403, "You can only submit evidence to your own pilot")
    if p.status not in ("ACTIVE", "CONCLUDED", "READY_TO_START"):
        raise HTTPException(409, f"Evidence can only be submitted for an active or concluded "
                                 f"pilot (current: {p.status})")
    if not title.strip():
        raise HTTPException(422, "Title is required")

    # ---- file validation -----------------------------------------------------
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(422, f"File extension '{ext or '(none)'}' not allowed. "
                                 f"Allowed: {settings.allowed_extensions}")
    data = file.file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(422, f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit")
    if not data:
        raise HTTPException(422, "Empty files are not accepted")
    mime = file.content_type or "application/octet-stream"

    digest = sha256_bytes(data)
    latest = db.query(Evidence).filter(Evidence.pilot_id == pilot_id, Evidence.kpi_id == kpi_id,
                                       Evidence.title == title.strip()) \
        .order_by(Evidence.version.desc()).first()
    version = (latest.version + 1) if latest else 1

    storage_dir = settings.UPLOAD_DIR
    os.makedirs(storage_dir, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename or "upload")
    storage_path = os.path.join(storage_dir, f"{digest[:16]}_{safe_name}")
    with open(storage_path, "wb") as fh:
        fh.write(data)

    e = Evidence(id=new_id("EV"), pilot_id=pilot_id, kpi_id=kpi_id, evidence_type=evidence_type,
                 title=title.strip(), description=description, submitted_by=user.id,
                 submitted_by_name=user.name, file_name=file.filename or safe_name,
                 file_size=len(data), mime_type=mime, sha256=digest,
                 storage_path=storage_path, version=version, claimed_value=claimed_value,
                 status="UPLOADED",
                 replaces_id=latest.id if latest else None)
    db.add(e)
    db.add(EvidenceVersion(id=new_id("EVV"), evidence_id=e.id, version=version,
                           file_name=e.file_name, sha256=digest, uploaded_by=user.id,
                           note="Initial upload" if version == 1 else
                                f"Revision of evidence {latest.id}"))
    db.commit()
    audit(db, user, "EVIDENCE_UPLOADED", "evidence", e.id,
          new_value={"title": e.title, "version": version, "sha256": digest[:16] + "...",
                     "claimed_value": claimed_value},
          metadata={"integrity_only": True})
    return _out(e, db)


@router.patch("/{evidence_id}/status")
def review_evidence(evidence_id: str, status: str, note: str = "",
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(404, "Evidence not found")
    if status not in STATUSES:
        raise HTTPException(422, "Unknown evidence status")
    old = e.status
    if status in REVIEW_TARGETS:
        if not require("EVIDENCE_REVIEW")(user=user):  # raises 403 for unauthorized roles
            pass
    elif status in VALIDATION_TARGETS:
        if not require("VALIDATION_SUBMIT")(user=user):
            pass
    if status not in TRANSITIONS.get(old, []):
        raise HTTPException(409, f"Invalid transition {old} → {status}. "
                                 f"Allowed: {TRANSITIONS.get(old, [])}")
    e.status = status
    if note:
        e.review_note = note
    db.commit()
    audit(db, user, "EVIDENCE_STATUS_CHANGED", "evidence", e.id,
          old_value={"status": old}, new_value={"status": status}, reason=note or None)
    return _out(e, db)

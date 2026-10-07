"""Independent validation workflow: package → validator + COI → findings → report."""
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.core.security import ROLE_LABELS
from app.models.evidence import (Evidence, ValidationFinding, ValidationPackage,
                                 ValidatorAssignment, ValidationReport)
from app.models.pilot import Pilot, PilotKpi
from app.models.user import User
from app.schemas.pilot import CoiIn, ValidationFindingIn, ValidationReportIn
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/validation", tags=["validation"])

FINDINGS = ["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE",
            "CONTRADICTORY_EVIDENCE", "UNVERIFIABLE", "UNKNOWN"]


def _package_out(db: Session, pkg: ValidationPackage) -> dict:
    validators = db.query(ValidatorAssignment).filter(ValidatorAssignment.package_id == pkg.id).all()
    findings = db.query(ValidationFinding).filter(ValidationFinding.package_id == pkg.id).all()
    report = db.query(ValidationReport).filter(ValidationReport.package_id == pkg.id) \
        .order_by(ValidationReport.report_version.desc()).first()
    pilot = db.query(Pilot).filter(Pilot.id == pkg.pilot_id).first()
    evidence = db.query(Evidence).filter(Evidence.id.in_(pkg.evidence_ids or ["__none__"])).all()
    return {
        "id": pkg.id, "pilot_id": pkg.pilot_id, "pilot_name": pilot.name if pilot else None,
        "status": pkg.status, "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
        "validators": [{"id": v.id, "validator_id": v.validator_id,
                        "name": v.validator_name, "coi_status": v.coi_status,
                        "status": v.status} for v in validators],
        "findings": [{"id": f.id, "kpi_id": f.kpi_id, "claimed": f.claimed,
                      "observed": f.observed, "validated_value": f.validated_value,
                      "target": f.target, "finding": f.finding,
                      "explanation": f.explanation,
                      "evidence_ids": f.evidence_ids or []} for f in findings],
        "report": _report_out(report) if report else None,
        "evidence": [{"id": e.id, "title": e.title, "sha256": e.sha256, "status": e.status,
                      "claimed_value": e.claimed_value} for e in evidence],
    }


def _report_out(r: ValidationReport) -> dict:
    return {"id": r.id, "summary": r.summary, "overall_finding": r.overall_finding,
            "validated_kpis": r.validated_kpis or {}, "report_version": r.report_version,
            "sha256": r.sha256,
            "created_at": r.created_at.isoformat() if r.created_at else None}


@router.get("/packages")
def list_packages(pilot_id: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(ValidationPackage)
    if pilot_id:
        q = q.filter(ValidationPackage.pilot_id == pilot_id)
    return [_package_out(db, p) for p in q.order_by(ValidationPackage.created_at.desc()).all()]


@router.post("/packages", status_code=201)
def prepare_package(pilot_id: str, db: Session = Depends(get_db),
                    user: User = Depends(require("EVIDENCE_REVIEW"))):
    """Bundle reviewed evidence for a pilot into a validation package."""
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    ready = db.query(Evidence).filter(Evidence.pilot_id == pilot_id,
                                      Evidence.status.in_(["READY_FOR_VALIDATION",
                                                           "ACCEPTED_FOR_MONITORING"])).all()
    if not ready:
        raise HTTPException(409, "No evidence is ready for validation. Review and accept "
                                 "evidence items first.")
    pkg = ValidationPackage(id=new_id("VP"), pilot_id=pilot_id,
                            evidence_ids=[e.id for e in ready])
    db.add(pkg)
    db.commit()
    audit(db, user, "VALIDATION_PACKAGE_PREPARED", "validation_package", pkg.id,
          new_value={"pilot_id": pilot_id, "evidence_count": len(ready)})
    return _package_out(db, pkg)


@router.post("/packages/{package_id}/assign", status_code=201)
def assign_validator(package_id: str, validator_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require("VALIDATION_ASSIGN"))):
    pkg = db.query(ValidationPackage).filter(ValidationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(404, "Package not found")
    if pkg.status not in ("PREPARED", "VALIDATOR_ASSIGNED"):
        raise HTTPException(409, "Validators can only be assigned before validation starts")
    v = db.query(User).filter(User.id == validator_id, User.role == "validator").first()
    if not v:
        raise HTTPException(404, "Validator not found")
    a = ValidatorAssignment(id=new_id("VA"), package_id=package_id, validator_id=validator_id,
                            validator_name=v.name)
    db.add(a)
    pkg.status = "VALIDATOR_ASSIGNED"
    db.commit()
    audit(db, user, "VALIDATOR_ASSIGNED", "validation_package", package_id,
          new_value={"validator": v.name})
    return _package_out(db, pkg)


@router.post("/assignments/{assignment_id}/coi")
def validator_coi(assignment_id: str, payload: CoiIn, db: Session = Depends(get_db),
                  user: User = Depends(require("COI_DECLARE"))):
    a = db.query(ValidatorAssignment).filter(ValidatorAssignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Validator assignment not found")
    if a.validator_id != user.id and user.role != "administrator":
        raise HTTPException(403, "Only the assigned validator can declare COI")
    if payload.status == "CONFIRMED_CONFLICT":
        a.coi_status = "RECUSED"
        a.status = "RECUSED"
    else:
        a.coi_status = payload.status
        a.status = "ASSIGNED"
    db.commit()
    audit(db, user, "VALIDATOR_COI_DECLARED", "validator_assignment", a.id,
          new_value={"status": payload.status})
    return {"id": a.id, "coi_status": a.coi_status, "status": a.status}


@router.post("/packages/{package_id}/start")
def start_validation(package_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require("VALIDATION_SUBMIT"))):
    """A validator with cleared COI may begin validation. Assignment + COI are hard gates."""
    pkg = db.query(ValidationPackage).filter(ValidationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(404, "Package not found")
    assignment = db.query(ValidatorAssignment).filter(
        ValidatorAssignment.package_id == package_id,
        ValidatorAssignment.validator_id == user.id).first()
    if not assignment and user.role != "administrator":
        raise HTTPException(403, "You are not the assigned validator for this package")
    if assignment and assignment.coi_status == "RECUSED":
        raise HTTPException(403, "You declared a confirmed conflict of interest and cannot "
                                 "validate this package")
    if assignment and assignment.coi_status == "AWAITING_COI":
        raise HTTPException(409, "Declare COI before starting validation")
    if pkg.status not in ("VALIDATOR_ASSIGNED", "IN_VALIDATION"):
        raise HTTPException(409, "Package is not open for validation")
    pkg.status = "IN_VALIDATION"
    if assignment:
        assignment.status = "IN_PROGRESS"
    db.commit()
    audit(db, user, "VALIDATION_STARTED", "validation_package", package_id)
    return _package_out(db, pkg)


@router.post("/packages/{package_id}/findings", status_code=201)
def add_finding(package_id: str, payload: ValidationFindingIn,
                db: Session = Depends(get_db), user: User = Depends(require("VALIDATION_SUBMIT"))):
    pkg = db.query(ValidationPackage).filter(ValidationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(404, "Package not found")
    if pkg.status != "IN_VALIDATION":
        raise HTTPException(409, "Findings can only be added while validation is in progress")
    if payload.finding not in FINDINGS:
        raise HTTPException(422, f"finding must be one of {FINDINGS}")
    _assert_assigned(db, package_id, user)
    f = ValidationFinding(id=new_id("VF"), package_id=package_id, **payload.model_dump())
    db.add(f)
    db.commit()
    audit(db, user, "VALIDATION_FINDING_RECORDED", "validation_finding", f.id,
          new_value={"finding": payload.finding, "kpi_id": payload.kpi_id})
    return _package_out(db, pkg)


@router.post("/packages/{package_id}/report", status_code=201)
def submit_report(package_id: str, payload: ValidationReportIn, db: Session = Depends(get_db),
                  user: User = Depends(require("VALIDATION_SUBMIT"))):
    pkg = db.query(ValidationPackage).filter(ValidationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(404, "Package not found")
    if pkg.status != "IN_VALIDATION":
        raise HTTPException(409, "Report can only be submitted while validation is in progress")
    if payload.overall_finding not in FINDINGS:
        raise HTTPException(422, f"overall_finding must be one of {FINDINGS}")
    _assert_assigned(db, package_id, user)
    findings = db.query(ValidationFinding).filter(ValidationFinding.package_id == package_id).all()
    if not findings:
        raise HTTPException(409, "Record at least one KPI finding before submitting the report")

    previous = db.query(ValidationReport).filter(ValidationReport.package_id == package_id) \
        .order_by(ValidationReport.report_version.desc()).first()
    content = payload.model_dump()
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()
    r = ValidationReport(id=new_id("VR"), package_id=package_id, pilot_id=pkg.pilot_id,
                         validator_id=user.id, report_version=(previous.report_version + 1)
                         if previous else 1, sha256=digest, **content)
    db.add(r)
    pkg.status = "REPORT_SUBMITTED"
    # mirror validated values onto pilot KPIs and flip evidence states
    pilot = db.query(Pilot).filter(Pilot.id == pkg.pilot_id).first()
    if pilot:
        for kpi_name, validated in (payload.validated_kpis or {}).items():
            k = db.query(PilotKpi).filter(PilotKpi.pilot_id == pkg.pilot_id,
                                          PilotKpi.name == kpi_name).first()
            if k:
                k.observed_value = str(validated)
                k.status = "TARGET_ACHIEVED" if _meets(k, str(validated)) else "TARGET_NOT_ACHIEVED"
        for e in db.query(Evidence).filter(Evidence.id.in_(pkg.evidence_ids or ["__none__"])):
            if e.status == "READY_FOR_VALIDATION":
                e.status = ("VALIDATED" if payload.overall_finding == "SUPPORTED"
                            else "PARTIALLY_VALIDATED" if payload.overall_finding == "PARTIALLY_SUPPORTED"
                            else "INSUFFICIENT_EVIDENCE")
    from app.routers.pilots_router import recompute_health
    recompute_health(db, pkg.pilot_id)
    db.commit()
    audit(db, user, "VALIDATION_REPORT_SUBMITTED", "validation_report", r.id,
          new_value={"overall_finding": payload.overall_finding,
                     "validated_kpis": payload.validated_kpis,
                     "version": r.report_version})
    return _package_out(db, pkg)


def _assert_assigned(db: Session, package_id: str, user: User):
    if user.role == "administrator":
        return
    a = db.query(ValidatorAssignment).filter(ValidatorAssignment.package_id == package_id,
                                             ValidatorAssignment.validator_id == user.id).first()
    if not a:
        raise HTTPException(403, "You are not the assigned validator for this package")
    if a.coi_status == "RECUSED":
        raise HTTPException(403, "Recused validators cannot submit findings or reports")
    if a.coi_status == "AWAITING_COI":
        raise HTTPException(409, "Declare COI before submitting validation work")


def _meets(k: PilotKpi, value: str) -> bool:
    def num(s):
        try:
            return float(str(s).replace("%", "").replace(",", "").strip())
        except (TypeError, ValueError):
            return None
    v, t = num(value), num(k.success_threshold or k.target)
    if v is None or t is None:
        return False
    return v >= t if k.direction == "increase" else v <= t

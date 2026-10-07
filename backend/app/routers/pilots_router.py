"""Pilots: creation, wizard updates, milestones/payments, monitoring, health explanation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.models.challenge import Challenge, Kpi
from app.models.evidence import Evidence
from app.models.pilot import Milestone, PaymentPlan, Pilot, PilotKpi
from app.models.startup import Startup
from app.models.user import User
from app.schemas.pilot import (KpiObservation, MilestoneIn, MilestoneStatus, PilotIn, PilotPatch, PilotKpiPatch)
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/pilots", tags=["pilots"])

PILOT_STATUSES = ["DRAFT", "PENDING_APPROVAL", "READY_TO_START", "ACTIVE", "CONCLUDED",
                  "DECIDED", "SCALED", "RE_PILOT"]
KPI_STATUSES = ["NOT_STARTED", "BASELINE_PENDING", "BASELINE_VALIDATED", "IN_PROGRESS",
                "TARGET_ON_TRACK", "AT_RISK", "TARGET_ACHIEVED", "TARGET_NOT_ACHIEVED",
                "INSUFFICIENT_DATA"]
MILESTONE_STATUSES = ["NOT_STARTED", "IN_PROGRESS", "SUBMITTED", "ACCEPTED", "BLOCKED"]
PAYMENT_STATUSES = ["NOT_ELIGIBLE", "PENDING_APPROVAL", "APPROVED", "RELEASED"]


def pilot_out(db: Session, p: Pilot, detail: bool = True) -> dict:
    base = {"id": p.id, "name": p.name, "department": p.department, "challenge_id": p.challenge_id,
            "startup_id": p.startup_id, "startup_name": p.startup_name, "status": p.status,
            "duration_weeks": p.duration_weeks, "budget": p.budget, "objectives": p.objectives,
            "expected_outcome": p.expected_outcome, "sites": p.sites,
            "target_users": p.target_users, "geographic_scope": p.geographic_scope,
            "success_criteria": p.success_criteria, "payment_conditions": p.payment_conditions,
            "baseline": p.baseline or {}, "data_ip": p.data_ip or {},
            "cybersecurity": p.cybersecurity or {}, "health": p.health,
            "health_explanation": p.health_explanation or []}
    if not detail:
        return base
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == p.id).all()
    milestones = db.query(Milestone).filter(Milestone.pilot_id == p.id) \
        .order_by(Milestone.start_date.asc()).all()
    evidence_count = db.query(Evidence).filter(Evidence.pilot_id == p.id).count()
    base.update({
        "kpis": [_kpi_out(k) for k in kpis],
        "milestones": [_milestone_out(m) for m in milestones],
        "payment_total": sum(m.payment_percentage for m in milestones),
        "evidence_count": evidence_count,
        "payment_plan": {"total_budget": p.budget,
                         "validates_to_100": sum(m.payment_percentage for m in milestones) == 100,
                         "note": "Demo workflow only. No payment gateway is integrated."},
    })
    return base


def _kpi_out(k: PilotKpi) -> dict:
    return {"id": k.id, "name": k.name, "description": k.description, "baseline": k.baseline,
            "target": k.target, "unit": k.unit, "measurement_method": k.measurement_method,
            "evidence_source": k.evidence_source, "success_threshold": k.success_threshold,
            "direction": k.direction, "status": k.status, "observed_value": k.observed_value,
            "claimed_value": k.claimed_value, "progress_notes": k.progress_notes or []}


def _milestone_out(m: Milestone) -> dict:
    return {"id": m.id, "name": m.name, "description": m.description, "start_date": m.start_date,
            "end_date": m.end_date, "deliverable": m.deliverable,
            "kpi_dependency": m.kpi_dependency, "payment_percentage": m.payment_percentage,
            "status": m.status, "payment_status": m.payment_status}


@router.get("")
def list_pilots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Pilot).order_by(Pilot.updated_at.desc()).all()
    if user.role == "startup":
        rows = [p for p in rows if p.startup_id == user.startup_id]
    return [pilot_out(db, p, detail=False) for p in rows]


@router.post("", status_code=201)
def create_pilot(payload: PilotIn, db: Session = Depends(get_db),
                 user: User = Depends(require("PILOT_CREATE"))):
    s = db.query(Startup).filter(Startup.id == payload.startup_id).first()
    if not s:
        raise HTTPException(404, "Startup not found")
    p = Pilot(id=new_id("P"), name=payload.name, startup_id=s.id, startup_name=s.name,
              officer_id=user.id, **{k: v for k, v in payload.model_dump().items()
                                     if k not in ("startup_id", "name")})
    db.add(p)
    # clone challenge KPIs into the pilot as monitorable pilot-KPIs
    if payload.challenge_id:
        c = db.query(Challenge).filter(Challenge.id == payload.challenge_id).first()
        if c:
            p.department = p.department or c.department
            for k in db.query(Kpi).filter(Kpi.challenge_id == c.id).all():
                db.add(PilotKpi(id=new_id("PK"), pilot_id=p.id, name=k.name,
                                description=k.description, baseline=k.baseline, target=k.target,
                                unit=k.unit, measurement_method=k.measurement_method,
                                evidence_source=k.evidence_source,
                                success_threshold=k.success_threshold, direction=k.direction,
                                status="BASELINE_PENDING"))
    db.add(PaymentPlan(id=new_id("PAY"), pilot_id=p.id, total_budget=p.budget))
    db.commit()
    audit(db, user, "PILOT_CREATED", "pilot", p.id, new_value={"name": p.name,
                                                               "startup": s.name})
    return pilot_out(db, p)


@router.get("/{pilot_id}")
def get_pilot(pilot_id: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    p = _get_pilot_checked(db, pilot_id, user)
    return pilot_out(db, p)


def _get_pilot_checked(db: Session, pilot_id: str, user: User) -> Pilot:
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    if user.role == "startup" and p.startup_id != user.startup_id:
        raise HTTPException(403, "Startups can only access their own pilots")
    return p


@router.patch("/{pilot_id}")
def update_pilot(pilot_id: str, payload: PilotPatch, db: Session = Depends(get_db),
                 user: User = Depends(require("PILOT_TRANSITION"))):
    p = _get_pilot_checked(db, pilot_id, user)
    if user.role == "startup" and p.status not in ("DRAFT", "PENDING_APPROVAL", "READY_TO_START", "ACTIVE"):
        raise HTTPException(403, "Startups cannot modify a concluded pilot")
    changed = {}
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(p, key, value)
        changed[key] = value
    db.commit()
    audit(db, user, "PILOT_UPDATED", "pilot", p.id, new_value=changed)
    return pilot_out(db, p)


@router.post("/{pilot_id}/transition")
def transition(pilot_id: str, to_status: str, db: Session = Depends(get_db),
               user: User = Depends(require("PILOT_TRANSITION"))):
    """Server-side status transition validation (workflow gates)."""
    p = _get_pilot_checked(db, pilot_id, user)
    if to_status not in PILOT_STATUSES:
        raise HTTPException(422, f"Unknown status '{to_status}'")
    allowed = {
        "DRAFT": ["PENDING_APPROVAL"],
        "PENDING_APPROVAL": ["READY_TO_START", "DRAFT"],
        "READY_TO_START": ["ACTIVE", "PENDING_APPROVAL"],
        "ACTIVE": ["CONCLUDED"],
        "CONCLUDED": ["DECIDED"],
        "DECIDED": ["SCALED", "RE_PILOT"],
        "SCALED": [], "RE_PILOT": [],
    }
    if user.role == "startup" and to_status not in ("READY_TO_START",):
        raise HTTPException(403, "Startups may only accept (READY_TO_START) a pilot")
    if to_status not in allowed.get(p.status, []):
        raise HTTPException(409, f"Invalid transition {p.status} → {to_status}. Allowed: "
                                 f"{allowed.get(p.status, [])}")
    if to_status == "ACTIVE" and sum(m.payment_percentage for m in
                                     db.query(Milestone).filter(Milestone.pilot_id == p.id)) != 100:
        raise HTTPException(409, "Milestone payment percentages must total exactly 100% before start")
    old = p.status
    p.status = to_status
    db.commit()
    audit(db, user, "PILOT_STATUS_TRANSITION", "pilot", p.id,
          old_value={"status": old}, new_value={"status": to_status})
    return pilot_out(db, p)


# ---- readiness gates (mirrors the wizard's Review & Approval) ---------------

@router.get("/{pilot_id}/readiness")
def readiness(pilot_id: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    p = _get_pilot_checked(db, pilot_id, user)
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == p.id).count()
    milestones = db.query(Milestone).filter(Milestone.pilot_id == p.id).all()
    checks = [
        {"key": "objectives", "label": "Objectives defined", "ok": bool(p.objectives)},
        {"key": "baseline", "label": "Baseline recorded",
         "ok": bool((p.baseline or {}).get("value"))},
        {"key": "kpis", "label": "At least one KPI", "ok": kpis > 0},
        {"key": "scope", "label": "Scope defined (sites & geography)",
         "ok": bool(p.sites and p.geographic_scope)},
        {"key": "milestones", "label": "At least one milestone", "ok": len(milestones) > 0},
        {"key": "payments", "label": "Payments total exactly 100%",
         "ok": sum(m.payment_percentage for m in milestones) == 100},
        {"key": "data_ip", "label": "Data & IP policy configured",
         "ok": bool(p.data_ip and (p.data_ip.get("ownership") or p.data_ip.get("usage_rights")))},
        {"key": "security", "label": "Cybersecurity checklist configured",
         "ok": bool(p.cybersecurity and p.cybersecurity.get("checklist"))},
    ]
    score = round(100 * sum(1 for c in checks if c["ok"]) / len(checks))
    status = "READY" if all(c["ok"] for c in checks) else "NOT_READY"
    return {"score": score, "status": status, "checks": checks,
            "missing": [c["label"] for c in checks if not c["ok"]]}


@router.post("/{pilot_id}/approve")
def approve_pilot(pilot_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require("PILOT_APPROVE"))):
    p = _get_pilot_checked(db, pilot_id, user)
    result = readiness(pilot_id, db=db, user=user)
    if result["status"] != "READY":
        raise HTTPException(409, {"message": "Approval blocked by readiness gates",
                                  "missing": result["missing"]})
    old = p.status
    p.status = "PENDING_APPROVAL"
    db.commit()
    audit(db, user, "PILOT_APPROVED_FOR_ACCEPTANCE", "pilot", p.id,
          old_value={"status": old}, new_value={"status": "PENDING_APPROVAL"})
    return pilot_out(db, p)


# ---- milestones --------------------------------------------------------------

@router.post("/{pilot_id}/milestones", status_code=201)
def add_milestone(pilot_id: str, payload: MilestoneIn, db: Session = Depends(get_db),
                  user: User = Depends(require("PILOT_CREATE"))):
    p = _get_pilot_checked(db, pilot_id, user)
    if p.status not in ("DRAFT", "PENDING_APPROVAL"):
        raise HTTPException(409, "Milestones can only be added while the pilot is in design")
    m = Milestone(id=new_id("MS"), pilot_id=p.id, **payload.model_dump())
    db.add(m)
    db.commit()
    total = sum(x.payment_percentage for x in db.query(Milestone).filter(Milestone.pilot_id == p.id))
    audit(db, user, "MILESTONE_ADDED", "milestone", m.id,
          new_value={"name": m.name, "payment_percentage": m.payment_percentage},
          metadata={"payment_total": total})
    return {"milestone": _milestone_out(m), "payment_total": total,
            "validates_to_100": total == 100}


@router.delete("/{pilot_id}/milestones/{milestone_id}")
def delete_milestone(pilot_id: str, milestone_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require("PILOT_CREATE"))):
    m = db.query(Milestone).filter(Milestone.id == milestone_id,
                                   Milestone.pilot_id == pilot_id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")
    db.delete(m)
    db.commit()
    audit(db, user, "MILESTONE_DELETED", "milestone", milestone_id, old_value={"name": m.name})
    return {"message": "Milestone deleted"}


@router.patch("/{pilot_id}/kpis/{kpi_id}")
def update_pilot_kpi(pilot_id: str, kpi_id: str, payload: PilotKpiPatch, db: Session = Depends(get_db),
                     user: User = Depends(require("PILOT_CREATE"))):
    k = db.query(PilotKpi).filter(PilotKpi.id == kpi_id, PilotKpi.pilot_id == pilot_id).first()
    if not k:
        raise HTTPException(404, "Pilot KPI not found")
    changed = {}
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(k, key, value)
        changed[key] = value
    db.commit()
    audit(db, user, "PILOT_KPI_UPDATED", "pilot_kpi", k.id, new_value=changed)
    return _kpi_out(k)


@router.patch("/{pilot_id}/milestones/{milestone_id}/status")
def update_milestone(pilot_id: str, milestone_id: str, payload: MilestoneStatus,
                     db: Session = Depends(get_db), user: User = Depends(require("MILESTONE_UPDATE"))):
    m = db.query(Milestone).filter(Milestone.id == milestone_id,
                                   Milestone.pilot_id == pilot_id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")
    transitions_m = {"NOT_STARTED": ["IN_PROGRESS", "BLOCKED"],
                     "IN_PROGRESS": ["SUBMITTED", "BLOCKED"],
                     "SUBMITTED": ["ACCEPTED", "BLOCKED"],
                     "ACCEPTED": [], "BLOCKED": ["IN_PROGRESS"]}
    payments_m = {"NOT_ELIGIBLE": ["PENDING_APPROVAL"],
                  "PENDING_APPROVAL": ["APPROVED"],
                  "APPROVED": ["RELEASED"], "RELEASED": []}
    old_m, old_p = m.status, m.payment_status
    changed = {}
    if payload.status:
        if payload.status not in MILESTONE_STATUSES:
            raise HTTPException(422, "Invalid milestone status")
        if m.status == "SUBMITTED" and payload.status == "ACCEPTED" and user.role == "startup":
            raise HTTPException(403, "Startups cannot accept their own milestones")
        if payload.status not in transitions_m.get(m.status, []):
            raise HTTPException(409, f"Invalid transition {m.status} → {payload.status}")
        m.status = payload.status
        changed["status"] = payload.status
        if payload.status == "ACCEPTED":
            from app.models.user import utcnow
            m.accepted_at = utcnow()
    if payload.payment_status:
        if payload.payment_status not in PAYMENT_STATUSES:
            raise HTTPException(422, "Invalid payment status")
        if m.status != "ACCEPTED" and payload.payment_status in ("PENDING_APPROVAL", "APPROVED"):
            raise HTTPException(409, "Payment becomes eligible only after the milestone is ACCEPTED "
                                     "with linked evidence")
        if payload.payment_status not in payments_m.get(m.payment_status, []):
            raise HTTPException(409, f"Invalid payment transition {m.payment_status} → "
                                     f"{payload.payment_status}")
        m.payment_status = payload.payment_status
        changed["payment_status"] = payload.payment_status
    db.commit()
    audit(db, user, "MILESTONE_STATUS_UPDATED", "milestone", m.id,
          old_value={"status": old_m, "payment_status": old_p}, new_value=changed)
    return _milestone_out(m)


# ---- KPI monitoring -----------------------------------------------------------

@router.post("/{pilot_id}/kpis/{kpi_id}/observation")
def record_observation(pilot_id: str, kpi_id: str, payload: KpiObservation,
                       db: Session = Depends(get_db),
                       user: User = Depends(require("EVIDENCE_OBSERVE"))):
    """Startup claims and government/validator observations are stored separately."""
    k = db.query(PilotKpi).filter(PilotKpi.id == kpi_id, PilotKpi.pilot_id == pilot_id).first()
    if not k:
        raise HTTPException(404, "Pilot KPI not found")
    changed = {}
    if payload.claimed_value is not None:
        k.claimed_value = payload.claimed_value
        changed["claimed_value"] = payload.claimed_value
    if payload.observed_value is not None:
        if user.role == "startup":
            raise HTTPException(403, "Startups submit claims; observed values are recorded by "
                                     "the department or validator")
        k.observed_value = payload.observed_value
        changed["observed_value"] = payload.observed_value
    if payload.status:
        if payload.status not in KPI_STATUSES:
            raise HTTPException(422, "Invalid KPI status")
        k.status = payload.status
        changed["status"] = payload.status
    notes = list(k.progress_notes or [])
    if payload.note:
        notes.append({"note": payload.note, "by": user.name,
                      "role": user.role,
                      "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
        k.progress_notes = notes
    db.commit()
    audit(db, user, "KPI_OBSERVATION_RECORDED", "pilot_kpi", k.id, new_value=changed)
    recompute_health(db, pilot_id)
    return _kpi_out(k)


# ---- pilot health -------------------------------------------------------------

def recompute_health(db: Session, pilot_id: str):
    """Explainable health: never a black box; reasons are always attached."""
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        return
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == pilot_id).all()
    evidence = db.query(Evidence).filter(Evidence.pilot_id == pilot_id).all()
    reasons, health = [], "GREEN"

    at_risk = [k for k in kpis if k.status in ("AT_RISK", "TARGET_NOT_ACHIEVED")]
    if at_risk:
        health = "RED" if any(k.status == "TARGET_NOT_ACHIEVED" for k in at_risk) else "AMBER"
        reasons.append("KPI status requires attention: " +
                       ", ".join(f"{k.name} ({k.status})" for k in at_risk))

    needs_clarification = [e for e in evidence if e.status in ("NEEDS_CLARIFICATION", "REJECTED")]
    if needs_clarification:
        health = max(health, "AMBER", key=lambda h: ["GREEN", "AMBER", "RED"].index(h))
        reasons.append(f"{len(needs_clarification)} evidence item(s) need clarification or were rejected")

    sec = p.cybersecurity or {}
    pending_sec = [k for k, v in (sec.get("checklist") or {}).items() if not v]
    if pending_sec:
        if health == "GREEN":
            health = "AMBER"
        reasons.append("Cybersecurity checklist items pending: " + ", ".join(pending_sec))

    if not reasons:
        reasons.append("All monitored KPIs are on track and no evidence or security exceptions are open.")
    p.health, p.health_explanation = health, reasons
    db.commit()

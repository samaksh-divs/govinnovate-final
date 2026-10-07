"""Decision Intelligence → Government Decision → Scale-Up → Procurement → Re-Pilot."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.engines.decision_engine import evaluate
from app.models.challenge import Challenge
from app.models.decision import (DecisionRecommendation, GovernmentDecision,
                                 KnowledgeLesson, ProcurementPackage, RepilotPlan,
                                 ScaleUpPlan)
from app.models.evidence import Evidence, ValidationPackage, ValidationReport
from app.models.pilot import Milestone, Pilot, PilotKpi
from app.models.user import User
from app.schemas.pilot import GovernmentDecisionIn
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


def _validation_for(db: Session, pilot_id: str) -> dict | None:
    pkg = db.query(ValidationPackage).filter(ValidationPackage.pilot_id == pilot_id,
                                             ValidationPackage.status == "REPORT_SUBMITTED") \
        .order_by(ValidationPackage.created_at.desc()).first()
    if not pkg:
        return None
    report = db.query(ValidationReport).filter(ValidationReport.package_id == pkg.id) \
        .order_by(ValidationReport.report_version.desc()).first()
    if not report:
        return None
    return {"id": pkg.id, "overall_finding": report.overall_finding,
            "validated_kpis": report.validated_kpis or {}, "summary": report.summary,
            "sha256": report.sha256, "report_version": report.report_version}


@router.post("/{pilot_id}/recommendation", status_code=201)
def generate_recommendation(pilot_id: str, db: Session = Depends(get_db),
                            user: User = Depends(require("DECISION_REQUEST"))):
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == pilot_id).all()
    milestones = db.query(Milestone).filter(Milestone.pilot_id == pilot_id).all()
    evidence = [{"status": e.status} for e in
                db.query(Evidence).filter(Evidence.pilot_id == pilot_id).all()]
    validation = _validation_for(db, pilot_id)

    result = evaluate(
        pilot={"id": p.id, "status": p.status, "sites": p.sites, "baseline": p.baseline or {},
               "cybersecurity": p.cybersecurity or {}, "objectives": p.objectives,
               "startup_name": p.startup_name},
        pilot_kpis=[{"name": k.name, "claimed_value": k.claimed_value,
                     "observed_value": k.observed_value, "target": k.target,
                     "success_threshold": k.success_threshold, "direction": k.direction}
                    for k in kpis],
        validation=validation,
        milestones=[{"status": m.status} for m in milestones],
        evidence=evidence,
    )
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    rec = DecisionRecommendation(
        id=new_id("DR"), pilot_id=pilot_id, outcome=result["outcome"],
        confidence=result["confidence"], reasons=result["reasons"],
        supporting_evidence=result["supporting_evidence"],
        missing_evidence=result["missing_evidence"], risk_flags=result["risk_flags"],
        factor_scores=result["factor_scores"], engine_version=result["engine_version"])
    db.add(rec)
    db.commit()
    audit(db, user, "DECISION_RECOMMENDATION_GENERATED", "pilot", pilot_id,
          new_value={"outcome": result["outcome"], "confidence": result["confidence"],
                     "engine_version": result["engine_version"]})
    return {"id": rec.id, **result, "validation": validation}


@router.get("/{pilot_id}/recommendations")
def list_recommendations(pilot_id: str, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    rows = db.query(DecisionRecommendation).filter(DecisionRecommendation.pilot_id == pilot_id) \
        .order_by(DecisionRecommendation.created_at.desc()).all()
    return [{"id": r.id, "outcome": r.outcome, "confidence": r.confidence, "reasons": r.reasons,
             "supporting_evidence": r.supporting_evidence, "missing_evidence": r.missing_evidence,
             "risk_flags": r.risk_flags, "factor_scores": r.factor_scores,
             "engine_version": r.engine_version,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.post("/{pilot_id}/government-decision", status_code=201)
def government_decision(pilot_id: str, payload: GovernmentDecisionIn,
                        db: Session = Depends(get_db),
                        user: User = Depends(require("GOVERNMENT_DECISION"))):
    """The human, authoritative decision. Overrides require a reason; history is append-only."""
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    if payload.decision not in ("SCALE", "RE_PILOT", "REJECT", "INSUFFICIENT_EVIDENCE"):
        raise HTTPException(422, "decision must be SCALE, RE_PILOT, REJECT or INSUFFICIENT_EVIDENCE")
    if not payload.reason.strip():
        raise HTTPException(422, "A decision reason is mandatory — this is a government record")

    latest_rec = db.query(DecisionRecommendation).filter(
        DecisionRecommendation.pilot_id == pilot_id) \
        .order_by(DecisionRecommendation.created_at.desc()).first()
    d = GovernmentDecision(id=new_id("GD"), pilot_id=pilot_id,
                           recommendation_id=latest_rec.id if latest_rec else None,
                           ai_outcome=latest_rec.outcome if latest_rec else "",
                           decision=payload.decision,
                           decision_type="OVERRIDE" if payload.override else "ALIGNED",
                           reason=payload.reason.strip(), decided_by=user.id,
                           decided_by_name=user.name)
    db.add(d)
    old = p.status
    p.status = "DECIDED"
    db.commit()
    audit(db, user, "GOVERNMENT_DECISION_RECORDED", "pilot", pilot_id,
          old_value={"status": old, "ai_recommendation": d.ai_outcome},
          new_value={"decision": payload.decision, "type": d.decision_type},
          reason=payload.reason.strip())
    return {"id": d.id, "decision": d.decision, "decision_type": d.decision_type,
            "ai_outcome": d.ai_outcome, "decided_by": d.decided_by_name,
            "at": d.decided_at.isoformat()}


@router.get("/{pilot_id}/government-decisions")
def decision_history(pilot_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Full versioned history — never silently overwritten."""
    rows = db.query(GovernmentDecision).filter(GovernmentDecision.pilot_id == pilot_id) \
        .order_by(GovernmentDecision.decided_at.asc()).all()
    return [{"id": d.id, "decision": d.decision, "decision_type": d.decision_type,
             "ai_outcome": d.ai_outcome, "reason": d.reason, "decided_by": d.decided_by_name,
             "at": d.decided_at.isoformat() if d.decided_at else None} for d in rows]


# ---------------------------------------------------------------------------
# Scale-up (hard-gated on a government SCALE decision)
# ---------------------------------------------------------------------------

scale_router = APIRouter(prefix="/api/scaleup", tags=["scaleup"])


@scale_router.post("/{pilot_id}/plan", status_code=201)
def create_scale_plan(pilot_id: str, db: Session = Depends(get_db),
                      user: User = Depends(require("SCALE_PLAN"))):
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    decision = db.query(GovernmentDecision).filter(GovernmentDecision.pilot_id == pilot_id) \
        .order_by(GovernmentDecision.decided_at.desc()).first()
    if not decision or decision.decision != "SCALE":
        raise HTTPException(409, "Scale-up is available only after a government SCALE decision. "
                                 "This is a hard workflow gate.")
    plan = ScaleUpPlan(
        id=new_id("SU"), pilot_id=pilot_id, decision_id=decision.id,
        pilot_scope={"sites": p.sites, "users": p.target_users, "budget": p.budget,
                     "duration_weeks": p.duration_weeks,
                     "geographic_scope": p.geographic_scope},
        scale_scope={"sites": (p.sites or 1) * 5, "users": "District-wide rollout",
                     "budget": p.budget * 6,
                     "infrastructure": "Redundant hosting at Maharashtra SDC",
                     "geographic_scope": "State-wide (phased by district)"},
        support_requirements=["Program management office", "Training program",
                              "24×7 helpdesk", "Spares & maintenance network"],
        new_kpis=["Scale-phase uptime ≥ 99.5%", "Cost per site within sanctioned budget",
                  "Adoption ≥ 70% of field staff"],
        operational_risks=["Hardware supply chain at scale",
                           "Field-staff adoption across districts",
                           "Data volume growth vs telemetry capacity"],
        cybersecurity_plan={"review": "Full re-assessment for expanded footprint",
                            "certification": "CERT-In audit before district rollout",
                            "data_residency": "Maharashtra SDC (Pune) only"})
    db.add(plan)
    db.commit()
    audit(db, user, "SCALE_PLAN_CREATED", "scaleup_plan", plan.id, new_value={"pilot_id": pilot_id})
    return _scale_out(db, plan)


@scale_router.get("/{pilot_id}/plan")
def get_scale_plan(pilot_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    plan = db.query(ScaleUpPlan).filter(ScaleUpPlan.pilot_id == pilot_id) \
        .order_by(ScaleUpPlan.created_at.desc()).first()
    if not plan:
        raise HTTPException(404, "No scale-up plan exists. It is created only after a SCALE decision.")
    return _scale_out(db, plan)


@scale_router.post("/plans/{plan_id}/approve")
def approve_scale(plan_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require("SCALE_APPROVE"))):
    plan = db.query(ScaleUpPlan).filter(ScaleUpPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.status == "APPROVED":
        raise HTTPException(409, "Plan already approved")
    plan.status = "APPROVED"
    plan.reviewed_by = user.id
    plan.reviewed_at = datetime.now(timezone.utc)
    p = db.query(Pilot).filter(Pilot.id == plan.pilot_id).first()
    if p:
        p.status = "SCALED"
    db.commit()
    audit(db, user, "SCALE_PLAN_APPROVED", "scaleup_plan", plan.id, new_value={"status": "APPROVED"})
    return _scale_out(db, plan)


def _scale_out(db: Session, plan: ScaleUpPlan) -> dict:
    return {"id": plan.id, "pilot_id": plan.pilot_id, "decision_id": plan.decision_id,
            "status": plan.status, "pilot_scope": plan.pilot_scope or {},
            "scale_scope": plan.scale_scope or {}, "new_kpis": plan.new_kpis or [],
            "operational_risks": plan.operational_risks or [],
            "cybersecurity_plan": plan.cybersecurity_plan or {},
            "support_requirements": plan.support_requirements or [],
            "reviewed_by": plan.reviewed_by,
            "reviewed_at": plan.reviewed_at.isoformat() if plan.reviewed_at else None}


# ---------------------------------------------------------------------------
# Procurement preparation (hard-gated on an APPROVED scale plan)
# ---------------------------------------------------------------------------

proc_router = APIRouter(prefix="/api/procurement", tags=["procurement"])


@proc_router.post("/{pilot_id}/package", status_code=201)
def generate_package(pilot_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require("PROCUREMENT_GENERATE"))):
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    plan = db.query(ScaleUpPlan).filter(ScaleUpPlan.pilot_id == pilot_id,
                                        ScaleUpPlan.status == "APPROVED").first()
    if not plan:
        raise HTTPException(409, "Procurement preparation requires an APPROVED scale-up plan. "
                                 "This platform is not a marketplace; it only prepares "
                                 "evidence-backed documents.")
    validation = _validation_for(db, pilot_id)
    lessons = db.query(KnowledgeLesson).filter(KnowledgeLesson.pilot_id == pilot_id,
                                               KnowledgeLesson.status == "ACCEPTED").all()
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == pilot_id).all()
    challenge = db.query(Challenge).filter(Challenge.id == p.challenge_id).first() \
        if p.challenge_id else None
    content = {
        "requirements_summary": (challenge.requirements or {}) if challenge else {},
        "validated_kpis": [{"name": k.name, "target": k.target, "validated": k.observed_value,
                            "threshold": k.success_threshold} for k in kpis],
        "pilot_evidence_summary": {"budget": p.budget, "duration_weeks": p.duration_weeks,
                                   "sites": p.sites,
                                   "validation": (validation or {}).get("overall_finding", "N/A"),
                                   "validation_report_sha256": (validation or {}).get("sha256", "")},
        "validation_findings": (validation or {}).get("validated_kpis", {}),
        "risks": plan.operational_risks or [],
        "cybersecurity_requirements": plan.cybersecurity_plan or {},
        "implementation_scope": plan.scale_scope or {},
        "lessons_learned": [{"title": l.title, "lesson": l.edited_lesson or l.lesson}
                            for l in lessons],
    }
    pkg = ProcurementPackage(id=new_id("PP"), scaleup_id=plan.id, pilot_id=pilot_id,
                             content=content, generated_by=user.id)
    db.add(pkg)
    db.commit()
    audit(db, user, "PROCUREMENT_PACKAGE_GENERATED", "procurement_package", pkg.id,
          new_value={"pilot_id": pilot_id, "scaleup_id": plan.id})
    return _proc_out(pkg)


@proc_router.get("/{pilot_id}/package")
def get_package(pilot_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    pkg = db.query(ProcurementPackage).filter(ProcurementPackage.pilot_id == pilot_id) \
        .order_by(ProcurementPackage.generated_at.desc()).first()
    if not pkg:
        raise HTTPException(404, "No procurement package generated for this pilot")
    return _proc_out(pkg)


def _proc_out(pkg: ProcurementPackage) -> dict:
    return {"id": pkg.id, "status": pkg.status,
            "generated_at": pkg.generated_at.isoformat() if pkg.generated_at else None,
            "warnings": ["DRAFT — NOT A LEGALLY BINDING TENDER",
                         "LEGAL REVIEW REQUIRED before any procurement use"],
            "content": pkg.content or {}}


# ---------------------------------------------------------------------------
# Re-pilot planning (hard-gated on a government RE_PILOT decision)
# ---------------------------------------------------------------------------

repilot_router = APIRouter(prefix="/api/repilots", tags=["repilots"])


@repilot_router.post("/{pilot_id}/plan", status_code=201)
def create_repilot_plan(pilot_id: str, db: Session = Depends(get_db),
                        user: User = Depends(require("REPILOT_PLAN"))):
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    decision = db.query(GovernmentDecision).filter(GovernmentDecision.pilot_id == pilot_id) \
        .order_by(GovernmentDecision.decided_at.desc()).first()
    if not decision or decision.decision != "RE_PILOT":
        raise HTTPException(409, "Re-pilot planning requires a government RE_PILOT decision.")
    rec = db.query(DecisionRecommendation).filter(DecisionRecommendation.pilot_id == pilot_id) \
        .order_by(DecisionRecommendation.created_at.desc()).first()
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == pilot_id).all()
    plan = RepilotPlan(
        id=new_id("RP"), pilot_id=pilot_id, decision_id=decision.id,
        carried_forward={
            "previous_kpi_results": [{"name": k.name, "target": k.target,
                                      "claimed": k.claimed_value, "observed": k.observed_value,
                                      "status": k.status} for k in kpis],
            "lessons": [{"title": l.title, "lesson": l.edited_lesson or l.lesson}
                        for l in db.query(KnowledgeLesson)
                        .filter(KnowledgeLesson.pilot_id == pilot_id).all()],
            "evidence_gaps": (rec.missing_evidence if rec else []),
            "validation_risk_flags": (rec.risk_flags if rec else []),
            "previous_scope": {"sites": p.sites, "budget": p.budget,
                               "duration_weeks": p.duration_weeks}},
        scope_changes={"sites": {"from": p.sites, "to": 10,
                                 "reason": "Expand baseline/data coverage"},
                       "duration_weeks": {"from": p.duration_weeks, "to": p.duration_weeks,
                                          "reason": "Same controlled duration for comparability"},
                       "budget": {"from": p.budget, "to": round(p.budget * 1.6),
                                  "reason": "Expanded site coverage and instrumentation"}},
        required_changes=["Expand from 3 sites to 10 sites",
                          "Improve baseline/data coverage",
                          "Complete cybersecurity review"])
    db.add(plan)
    db.commit()
    audit(db, user, "REPILOT_PLAN_CREATED", "repilot_plan", plan.id,
          new_value={"pilot_id": pilot_id})
    return _repilot_out(plan)


@repilot_router.get("/{pilot_id}/plan")
def get_repilot_plan(pilot_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    plan = db.query(RepilotPlan).filter(RepilotPlan.pilot_id == pilot_id) \
        .order_by(RepilotPlan.created_at.desc()).first()
    if not plan:
        raise HTTPException(404, "No re-pilot plan exists for this pilot")
    return _repilot_out(plan)


@repilot_router.post("/plans/{plan_id}/create-pilot", status_code=201)
def spawn_pilot(plan_id: str, db: Session = Depends(get_db),
                user: User = Depends(require("REPILOT_PLAN"))):
    """Create the follow-on pilot from the re-pilot plan."""
    plan = db.query(RepilotPlan).filter(RepilotPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.new_pilot_id:
        raise HTTPException(409, "A follow-on pilot already exists for this plan")
    old = db.query(Pilot).filter(Pilot.id == plan.pilot_id).first()
    if not old:
        raise HTTPException(404, "Original pilot not found")
    changes = plan.scope_changes or {}
    p = Pilot(id=new_id("P"), name=f"{old.name} — Phase 2 (Re-Pilot)",
              department=old.department, challenge_id=old.challenge_id,
              startup_id=old.startup_id, startup_name=old.startup_name,
              officer_id=user.id, status="DRAFT",
              duration_weeks=(changes.get("duration_weeks") or {}).get("to", old.duration_weeks),
              budget=(changes.get("budget") or {}).get("to", old.budget),
              objectives=old.objectives,
              sites=(changes.get("sites") or {}).get("to", old.sites),
              target_users=old.target_users, geographic_scope=old.geographic_scope,
              baseline={"status": "PENDING",
                        "note": "Baseline must be re-validated with expanded data coverage"})
    db.add(p)
    plan.new_pilot_id = p.id
    plan.status = "PILOT_CREATED"
    db.commit()
    audit(db, user, "REPILOT_PILOT_CREATED", "pilot", p.id,
          new_value={"from_pilot": old.id, "repilot_plan": plan.id})
    return {"new_pilot_id": p.id, "plan": _repilot_out(plan)}


def _repilot_out(plan: RepilotPlan) -> dict:
    return {"id": plan.id, "pilot_id": plan.pilot_id, "decision_id": plan.decision_id,
            "new_pilot_id": plan.new_pilot_id, "status": plan.status,
            "carried_forward": plan.carried_forward or {},
            "scope_changes": plan.scope_changes or {},
            "required_changes": plan.required_changes or []}

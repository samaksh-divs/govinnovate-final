"""Demo-mode endpoints: story shortcuts, seed reset, openapi visibility."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.models.challenge import Challenge
from app.models.decision import GovernmentDecision, ProcurementPackage, RepilotPlan, ScaleUpPlan
from app.models.evidence import Evidence, ValidationPackage
from app.models.pilot import Pilot
from app.models.user import User
from app.services.audit import audit
from app.services.seed import DEMO_PASSWORD, seed

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/story")
def demo_story(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Judge-facing shortcuts into the complete demo workflow."""
    def pilot_sum(p: Pilot) -> dict:
        return {"id": p.id, "name": p.name, "startup": p.startup_name, "status": p.status,
                "department": p.department}

    water = db.query(Pilot).filter(Pilot.id == "P-WTR-001").first()
    soil = db.query(Pilot).filter(Pilot.id == "P-AGR-001").first()
    water_pkg = db.query(ValidationPackage).filter(ValidationPackage.pilot_id == "P-WTR-001").first() \
        if water else None
    soil_scale = db.query(ScaleUpPlan).filter(ScaleUpPlan.pilot_id == "P-AGR-001").first() \
        if soil else None
    water_repi = db.query(RepilotPlan).filter(RepilotPlan.pilot_id == "P-WTR-001").first() \
        if water else None
    decisions = {d.pilot_id: d for d in db.query(GovernmentDecision).all()} \
        if db.query(GovernmentDecision).count() else {}
    ev_count = db.query(Evidence).count()
    ch = db.query(Challenge).filter(Challenge.id == "CH-WTR-001").first()
    return {
        "notice": "Every record here is DEMO DATA — fictional and for evaluation only.",
        "demo_password_hint": f"all demo accounts use password: {DEMO_PASSWORD}",
        "shortcuts": {
            "challenge": {"id": ch.id, "title": ch.title, "status": ch.status} if ch else None,
            "water_pilot": pilot_sum(water) if water else None,
            "water_validation_package": {"id": water_pkg.id, "status": water_pkg.status}
            if water_pkg else None,
            "water_decision": (decisions.get("P-WTR-001").decision if "P-WTR-001" in decisions else None)
            if water else None,
            "water_repilot_plan": {"id": water_repi.id, "status": water_repi.status,
                                   "new_pilot_id": water_repi.new_pilot_id} if water_repi else None,
            "soil_pilot": pilot_sum(soil) if soil else None,
            "soil_scale_plan": {"id": soil_scale.id, "status": soil_scale.status} if soil_scale else None,
            "soil_procurement": db.query(ProcurementPackage)
                .filter(ProcurementPackage.pilot_id == "P-AGR-001").count() > 0,
            "evidence_count": ev_count,
        },
        "story": [
            "Government identifies water leakage problem",
            "Creates challenge CH-WTR-001 with AI requirement assistant",
            "Officer approves KPIs (Leakage Reduction ≥18% threshold)",
            "AquaSense Technologies (demo) matched and evaluated",
            "Pilot P-WTR-001 runs 12 weeks, ₹10,00,000",
            "Startup claims 21% — observed 19% — validated 18%",
            "Decision intelligence recommends RE-PILOT (abstains from scale)",
            "Government records RE-PILOT: 3→10 sites, better baseline, security review",
            "Separate branch: P-AGR-001 validated → SCALE → procurement-ready (draft)",
        ],
    }


@router.post("/seed")
def run_seed(force: bool = False, db: Session = Depends(get_db),
             user: User = Depends(require("DEMO_SEED"))):
    result = seed(db, force=force)
    if not result.get("seeded") and not force:
        raise HTTPException(409, "Database already contains data. Pass force=true to rebuild "
                                 "the demo dataset (destructive).")
    if force:
        audit(db, user, "DEMO_DATA_REBUILT", "system", "seed", metadata={"forced": True})
    return result

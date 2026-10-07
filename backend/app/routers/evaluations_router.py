"""Expert evaluation: assignment, COI gating, versioned submissions, aggregation."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.core.security import ROLE_LABELS
from app.engines.evaluation_stats import RECOMMENDATION_RULES, aggregate_evaluations, weighted_total
from app.models.challenge import Challenge
from app.models.evaluation import (CoiDeclaration, Evaluation, EvaluationAggregate,
                                   ExpertAssignment)
from app.models.startup import Startup
from app.models.user import User
from app.schemas.pilot import CoiIn, EvaluationIn
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])

CRITERIA = [
    {"key": "problem_fit", "label": "Problem Fit", "weight": 20},
    {"key": "technical_feasibility", "label": "Technical Feasibility", "weight": 15},
    {"key": "relevant_experience", "label": "Relevant Experience", "weight": 15},
    {"key": "evidence_quality", "label": "Evidence Quality", "weight": 15},
    {"key": "pilot_readiness", "label": "Pilot Readiness", "weight": 10},
    {"key": "scalability", "label": "Scalability", "weight": 10},
    {"key": "value_for_money", "label": "Value for Money", "weight": 5},
    {"key": "risk_compliance", "label": "Risk & Compliance", "weight": 10},
]

COI_CATEGORIES = ["Financial", "Employment", "Consulting", "Investment", "Personal",
                  "Academic / Research", "Previous Collaboration", "Competitive",
                  "Institutional", "Other"]


@router.get("/criteria")
def criteria(user: User = Depends(get_current_user)):
    return {"criteria": CRITERIA, "coi_categories": COI_CATEGORIES,
            "note": "Scores below 40 require a written justification."}


@router.get("/assignments")
def list_assignments(challenge_id: str | None = None, expert_id: str | None = None,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Experts see their own assignments; officers see all for a challenge."""
    q = db.query(ExpertAssignment)
    if user.role == "expert":
        q = q.filter(ExpertAssignment.expert_id == user.id)
    else:
        if expert_id:
            q = q.filter(ExpertAssignment.expert_id == expert_id)
    if challenge_id:
        q = q.filter(ExpertAssignment.challenge_id == challenge_id)
    rows = q.all()
    return [_assignment_out(db, a) for a in rows]


@router.post("/assign", status_code=201)
def assign_expert(payload: dict = Body(...), db: Session = Depends(get_db),
                 user: User = Depends(require("EVALUATION_ASSIGN"))):
    """Assign an expert to a startup for a published challenge."""
    challenge_id = (payload.get("challenge_id") or "").strip()
    startup_id = (payload.get("startup_id") or "").strip()
    expert_id = (payload.get("expert_id") or "").strip()
    if not challenge_id or not startup_id or not expert_id:
        raise HTTPException(422, "Missing challenge_id, startup_id, or expert_id")
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c or c.status != "PUBLISHED":
        raise HTTPException(409, "Challenge must be published before assigning experts")
    expert = db.query(User).filter(User.id == expert_id, User.role == "expert").first()
    if not expert:
        raise HTTPException(404, "Expert not found")
    dup = db.query(ExpertAssignment).filter_by(challenge_id=challenge_id, startup_id=startup_id,
                                               expert_id=expert_id).first()
    if dup:
        raise HTTPException(409, "This expert is already assigned to this startup")
    a = ExpertAssignment(id=new_id("ASG"), challenge_id=challenge_id,
                         startup_id=startup_id, expert_id=expert_id)
    db.add(a)
    db.commit()
    audit(db, user, "EXPERT_ASSIGNED", "expert_assignment", a.id,
          new_value={"expert": expert.name, "startup_id": startup_id})
    return _assignment_out(db, a)


@router.post("/assignments/{assignment_id}/coi")
def declare_coi(assignment_id: str, payload: CoiIn, db: Session = Depends(get_db),
                user: User = Depends(require("COI_DECLARE"))):
    a = db.query(ExpertAssignment).filter(ExpertAssignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    if a.expert_id != user.id and user.role != "administrator":
        raise HTTPException(403, "Only the assigned expert (or an administrator) can declare COI")
    if payload.status not in ("NO_CONFLICT", "POTENTIAL_CONFLICT", "CONFIRMED_CONFLICT"):
        raise HTTPException(422, "Invalid COI status")
    if payload.status != "NO_CONFLICT" and not payload.conflict_type:
        raise HTTPException(422, "conflict_type is required when declaring a conflict")

    d = CoiDeclaration(id=new_id("COI"), assignment_id=assignment_id, expert_id=a.expert_id,
                       status=payload.status, conflict_type=payload.conflict_type,
                       description=payload.description)
    db.add(d)
    if payload.status == "CONFIRMED_CONFLICT":
        a.status = "RECUSED"
    elif a.status == "AWAITING_COI":
        a.status = "COI_CLEARED"
    db.commit()
    audit(db, user, "COI_DECLARED", "expert_assignment", a.id,
          new_value={"status": payload.status, "conflict_type": payload.conflict_type})
    return _assignment_out(db, a)


@router.get("/assignments/{assignment_id}/evaluation")
def get_evaluation(assignment_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    rows = db.query(Evaluation).filter(Evaluation.assignment_id == assignment_id) \
        .order_by(Evaluation.version.desc()).all()
    return [_evaluation_out(e) for e in rows]


@router.post("/assignments/{assignment_id}/evaluation", status_code=201)
def submit_evaluation(assignment_id: str, payload: EvaluationIn, db: Session = Depends(get_db),
                      user: User = Depends(require("EVALUATION_SUBMIT"))):
    a = db.query(ExpertAssignment).filter(ExpertAssignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    if a.expert_id != user.id:
        raise HTTPException(403, "You can only submit evaluations for your own assignments")

    # ---- hard workflow gates -------------------------------------------------
    if a.status == "RECUSED":
        raise HTTPException(403, "You declared a confirmed conflict of interest and are recused "
                                 "from evaluating this startup.")
    if a.status not in ("COI_CLEARED", "EVALUATION_SUBMITTED"):
        raise HTTPException(409, "COI declaration must be completed before evaluation")

    if payload.recommendation not in ("RECOMMEND_FOR_PILOT", "RECOMMEND_WITH_CONDITIONS",
                                      "NEED_MORE_EVIDENCE", "DO_NOT_RECOMMEND"):
        raise HTTPException(422, "Invalid recommendation")
    scores = {}
    for c in CRITERIA:
        entry = payload.scores.get(c["key"])
        # Score entries may be either a nested object (frontend default: {score, justification})
        # or a bare number for convenience. Normalize both, and also allow None.
        if isinstance(entry, dict):
            value = entry.get("score", 0)
            justification = (entry.get("justification") or "").strip()
        elif isinstance(entry, (int, float)):
            value = float(entry)
            justification = ""
        else:
            value = 0
            justification = ""
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise HTTPException(422, f"Score for '{c['label']}' must be numeric")
        # Normalize scores on a 0-10 scale to 0-100 (demo uses 9/10, 8/10, etc.,
        # while the engine weights are out of 100). A bare 0-10 score is multiplied
        # by 10 so 9 -> 90, 8 -> 80, etc. Already-100 scale values pass through.
        if 0 <= value <= 10:
            value = value * 10
        if not 0 <= value <= 100:
            raise HTTPException(422, f"Score for '{c['label']}' must be 0-100")
        if value < 40 and not justification:
            raise HTTPException(422, f"A low score on '{c['label']}' requires written justification")
        scores[c["key"]] = {"score": value, "justification": justification,
                            "comments": (entry.get("comments") if isinstance(entry, dict) else "")}

    previous = db.query(Evaluation).filter(Evaluation.assignment_id == assignment_id) \
        .order_by(Evaluation.version.desc()).first()
    e = Evaluation(id=new_id("EVAL"), assignment_id=assignment_id, challenge_id=a.challenge_id,
                   startup_id=a.startup_id, expert_id=user.id,
                   version=(previous.version + 1) if previous else 1,
                   scores=scores, weighted_total=weighted_total(scores, CRITERIA),
                   recommendation=payload.recommendation, final_comments=payload.final_comments)
    db.add(e)
    a.status = "EVALUATION_SUBMITTED"
    db.commit()
    _recompute_aggregate(db, a.challenge_id, a.startup_id)
    audit(db, user, "EXPERT_EVALUATION_SUBMITTED", "evaluation", e.id,
          new_value={"version": e.version, "weighted_total": e.weighted_total,
                     "recommendation": e.recommendation})
    return _evaluation_out(e)


@router.get("/aggregates/{challenge_id}")
def aggregates(challenge_id: str, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    rows = db.query(EvaluationAggregate).filter(EvaluationAggregate.challenge_id == challenge_id).all()
    out = []
    for r in rows:
        s = db.query(Startup).filter(Startup.id == r.startup_id).first()
        out.append({**_agg_out(r), "startup": {"id": s.id, "name": s.name, "sector": s.sector,
                                               "hq_location": s.hq_location} if s else None})
    return out


@router.post("/decisions", status_code=201)
def record_shortlist_decision(challenge_id: str, startup_id: str, decision: str, reason: str,
                              db: Session = Depends(get_db),
                              user: User = Depends(require("SHORTLIST_DECISION"))):
    """Officer's human decision on the expert-evaluation stage (pre-pilot)."""
    if decision not in ("SHORTLIST_FOR_PILOT", "REQUEST_MORE_EVIDENCE",
                        "REQUEST_RE_EVALUATION", "DO_NOT_SHORTLIST"):
        raise HTTPException(422, "Invalid decision")
    if not reason.strip():
        raise HTTPException(422, "A decision reason is required")
    audit(db, user, "SHORTLIST_DECISION_RECORDED", "challenge", challenge_id,
          new_value={"startup_id": startup_id, "decision": decision}, reason=reason.strip())
    return {"message": f"Decision '{decision}' recorded with reason and audit trail",
            "startup_id": startup_id, "decision": decision}


# --------------------------------------------------------------------------

def _assignment_out(db: Session, a: ExpertAssignment) -> dict:
    expert = db.query(User).filter(User.id == a.expert_id).first()
    coi = db.query(CoiDeclaration).filter(CoiDeclaration.assignment_id == a.id) \
        .order_by(CoiDeclaration.declared_at.desc()).first()
    latest = db.query(Evaluation).filter(Evaluation.assignment_id == a.id) \
        .order_by(Evaluation.version.desc()).first()
    return {
        "id": a.id, "challenge_id": a.challenge_id, "startup_id": a.startup_id,
        "expert": {"id": expert.id, "name": expert.name,
                   "organization": expert.organization,
                   "role_label": ROLE_LABELS.get(expert.role, expert.role)} if expert else None,
        "status": a.status, "coi": {"status": coi.status, "conflict_type": coi.conflict_type,
                                    "description": coi.description} if coi else None,
        "latest_evaluation": _evaluation_out(latest) if latest else None,
    }


def _evaluation_out(e: Evaluation) -> dict:
    return {"id": e.id, "assignment_id": e.assignment_id, "expert_id": e.expert_id,
            "version": e.version, "scores": e.scores or {}, "weighted_total": e.weighted_total,
            "recommendation": e.recommendation, "final_comments": e.final_comments,
            "created_at": e.created_at.isoformat() if e.created_at else None}


def _agg_out(r: EvaluationAggregate) -> dict:
    return {"startup_id": r.startup_id, "evaluation_count": r.evaluation_count,
            "average": r.average, "median": r.median, "minimum": r.minimum,
            "maximum": r.maximum, "stddev": r.stddev,
            "criterion_disagreement": r.criterion_disagreement or {},
            "disagreement_flag": r.disagreement_flag, "recommendation": r.recommendation}


def _recompute_aggregate(db: Session, challenge_id: str, startup_id: str):
    evals = db.query(Evaluation).filter(Evaluation.challenge_id == challenge_id,
                                        Evaluation.startup_id == startup_id).all()
    agg = aggregate_evaluations(
        [{"weighted_total": e.weighted_total, "scores": e.scores} for e in evals], CRITERIA)
    recommendation = next(r for cond, r in RECOMMENDATION_RULES if cond(agg))
    row = db.query(EvaluationAggregate).filter_by(challenge_id=challenge_id,
                                                  startup_id=startup_id).first()
    if not row:
        row = EvaluationAggregate(id=new_id("AGG"), challenge_id=challenge_id,
                                  startup_id=startup_id)
        db.add(row)
    for key, value in {**agg, "recommendation": recommendation}.items():
        setattr(row, key, value)
    db.commit()

"""Startup registry + explainable matching router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.engines.matching_engine import WEIGHTS, get_matching_engine
from app.models.challenge import Challenge
from app.models.evaluation import EvaluationAggregate
from app.models.evidence import Evidence
from app.models.pilot import Pilot
from app.models.startup import Startup, StartupMatch
from app.models.user import AuditLog, User
from app.schemas.common import Message
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/startups", tags=["startups"])


@router.get("/me/overview")
def my_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Startup persona's own cross-workflow view, assembled from the SAME shared
    records officers/experts/validators operate on (no separate copy):
    matching status per challenge (= application), expert evaluation aggregate,
    shortlist decision derived from the audit trail, own pilots and own evidence."""
    if user.role != "startup":
        raise HTTPException(403, "Only startup accounts have a personal workflow overview.")
    s = db.query(Startup).filter(Startup.id == user.startup_id).first() if user.startup_id else None
    if not s:
        raise HTTPException(404, "No startup profile is linked to this account.")
    applications = []
    for m in db.query(StartupMatch).filter(StartupMatch.startup_id == s.id).all():
        c = db.query(Challenge).filter(Challenge.id == m.challenge_id).first()
        agg = db.query(EvaluationAggregate).filter(EvaluationAggregate.challenge_id == m.challenge_id,
                                                   EvaluationAggregate.startup_id == s.id).first()
        # Application stage is DERIVED from shared records — never stored per-persona.
        # Officer shortlist decisions live in the append-only audit trail; a created
        # pilot for this startup+challenge means the application reached the pilot stage.
        decision_row = next(iter([
            r for r in db.query(AuditLog)
              .filter(AuditLog.action == "SHORTLIST_DECISION_RECORDED",
                      AuditLog.entity_id == m.challenge_id)
              .order_by(AuditLog.timestamp.desc()).all()
            if (r.new_value or {}).get("startup_id") == s.id]), None)
        decision = None
        if decision_row:
            decision = {"decision": decision_row.new_value.get("decision"),
                        "reason": decision_row.reason,
                        "by": decision_row.actor_name,
                        "at": decision_row.timestamp.isoformat()}
        pilot_row = db.query(Pilot).filter(Pilot.startup_id == s.id,
                                           Pilot.challenge_id == m.challenge_id).first()
        if pilot_row:
            stage = "PILOT_CREATED"
        elif decision:
            stage = {"SHORTLIST_FOR_PILOT": "APPROVED",
                     "DO_NOT_SHORTLIST": "REJECTED",
                     "REQUEST_MORE_EVIDENCE": "MORE_EVIDENCE_REQUESTED",
                     "REQUEST_RE_EVALUATION": "RE_EVALUATION_REQUESTED"}.get(
                         decision["decision"], "UNDER_REVIEW")
        elif agg:
            stage = "UNDER_REVIEW"
        else:
            stage = "SUBMITTED"
        applications.append({
            "challenge": {"id": c.id, "title": c.title, "department": c.department,
                          "status": c.status} if c else None,
            "rank": m.rank, "match_score": m.match_score,
            "eligibility_status": m.eligibility_status,
            "stage": stage,
            "decision": decision,
            "pilot_id": pilot_row.id if pilot_row else None,
            "evaluation": {"count": agg.evaluation_count, "average": agg.average,
                           "recommendation": agg.recommendation} if agg else None,
        })
    pilots = db.query(Pilot).filter(Pilot.startup_id == s.id).all()
    own_pilot_ids = [p.id for p in pilots]
    evidence_rows = db.query(Evidence).filter(Evidence.pilot_id.in_(own_pilot_ids or ["__none__"])).all()
    return {
        "startup": {"id": s.id, "name": s.name, "sector": s.sector, "stage": s.stage},
        "applications": applications,
        "pilots": [{"id": p.id, "name": p.name, "department": p.department,
                    "status": p.status, "health": p.health,
                    "duration_weeks": p.duration_weeks} for p in pilots],
        "evidence": {"total": len(evidence_rows),
                     "awaiting_review": sum(1 for e in evidence_rows if e.status in ("UPLOADED", "UNDER_REVIEW")),
                     "validated": sum(1 for e in evidence_rows if e.status in ("VALIDATED", "PARTIALLY_VALIDATED"))},
    }


def startup_out(s: Startup) -> dict:
    return {
        "id": s.id, "name": s.name, "sector": s.sector, "description": s.description,
        "technology": s.technology or [], "problem_areas": s.problem_areas or [],
        "hq_location": s.hq_location, "founded_year": s.founded_year, "team_size": s.team_size,
        "stage": s.stage, "dpiit_registered": s.dpiit_registered,
        "experience_years": s.experience_years, "previous_pilots": s.previous_pilots or [],
        "evidence_summary": s.evidence_summary or {}, "eligibility": s.eligibility or {},
        "scalability": s.scalability or {}, "risk_profile": s.risk_profile or {},
        "relevant_projects": s.relevant_projects or [], "pricing": s.pricing,
        "is_demo": s.is_demo,
    }


@router.get("")
def list_startups(q: str | None = None, sector: str | None = None,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Startup)
    rows = query.all()
    out = [startup_out(s) for s in rows]
    if q:
        ql = q.lower()
        out = [s for s in out if ql in json_blob(s)]
    if sector and sector != "All":
        out = [s for s in out if s["sector"] == sector]
    return out


def json_blob(s: dict) -> str:
    import json
    return json.dumps(s, default=str).lower()


@router.get("/sectors")
def sectors(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return sorted({s.sector for s in db.query(Startup).all() if s.sector})


@router.get("/weights")
def matching_weights(user: User = Depends(get_current_user)):
    return {"weights": WEIGHTS,
            "note": "Match Score ≠ Evidence Confidence. These are separate concepts."}


@router.get("/{startup_id}")
def get_startup(startup_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    s = db.query(Startup).filter(Startup.id == startup_id).first()
    if not s:
        raise HTTPException(404, "Startup not found")
    return startup_out(s)


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

match_router = APIRouter(prefix="/api/matching", tags=["matching"])


@match_router.post("/{challenge_id}/run")
def run_matching(challenge_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require("MATCH_RUN"))):
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    if c.status != "PUBLISHED":
        raise HTTPException(409, "Only PUBLISHED challenges can be matched")
    engine = get_matching_engine()
    challenge_dict = {"title": c.title, "problem_statement": c.problem_statement,
                      "problem_category": c.problem_category,
                      "expected_outcome": c.expected_outcome, "department": c.department}
    db.query(StartupMatch).filter(StartupMatch.challenge_id == c.id).delete()
    results = []
    for s in db.query(Startup).all():
        r = engine.score_startup(startup_out(s), challenge_dict)
        m = StartupMatch(id=new_id("M"), challenge_id=c.id, startup_id=s.id,
                         match_score=r["match_score"], component_scores=r["component_scores"],
                         explanations=r["explanations"], evidence_confidence=r["evidence_confidence"],
                         eligibility_status=r["eligibility_status"], run_version=r["engine_version"])
        db.add(m)
        results.append(m)
    db.commit()
    db.query(StartupMatch).filter(StartupMatch.challenge_id == c.id) \
        .update({"rank": 0}, synchronize_session=False)
    ranked = db.query(StartupMatch).filter(StartupMatch.challenge_id == c.id) \
        .order_by(StartupMatch.match_score.desc()).all()
    for i, m in enumerate(ranked, start=1):
        m.rank = i
    db.commit()
    audit(db, user, "MATCHING_RUN", "challenge", c.id,
          metadata={"startups_scored": len(results), "engine_version": engine.VERSION})
    return matches_out(db, c.id)


@match_router.get("/{challenge_id}")
def get_matches(challenge_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    return matches_out(db, challenge_id)


def matches_out(db: Session, challenge_id: str) -> list[dict]:
    rows = db.query(StartupMatch).filter(StartupMatch.challenge_id == challenge_id) \
        .order_by(StartupMatch.rank.asc(), StartupMatch.match_score.desc()).all()
    out = []
    for m in rows:
        s = db.query(Startup).filter(Startup.id == m.startup_id).first()
        out.append({
            "id": m.id, "challenge_id": m.challenge_id, "startup": startup_out(s) if s else None,
            "match_score": m.match_score, "component_scores": m.component_scores or {},
            "explanations": m.explanations or {}, "evidence_confidence": m.evidence_confidence,
            "eligibility_status": m.eligibility_status, "rank": m.rank,
            "overridden": m.overridden, "override_reason": m.override_reason,
            "run_version": m.run_version,
        })
    return out


@match_router.post("/{challenge_id}/override", response_model=Message)
def override_ranking(challenge_id: str, match_id: str, new_rank: int, reason: str,
                     db: Session = Depends(get_db), user: User = Depends(require("MATCH_OVERRIDE"))):
    """Government may override AI ranking. Requires a recorded reason + audit entry."""
    m = db.query(StartupMatch).filter(StartupMatch.id == match_id,
                                      StartupMatch.challenge_id == challenge_id).first()
    if not m:
        raise HTTPException(404, "Match not found")
    if not reason.strip():
        raise HTTPException(422, "A reason is mandatory when overriding a ranking")
    if not 1 <= new_rank <= 100:
        raise HTTPException(422, "new_rank must be between 1 and 100")
    old_rank = m.rank
    m.overridden = True
    m.override_reason = reason.strip()
    m.rank = new_rank
    db.commit()
    audit(db, user, "MATCHING_RANK_OVERRIDDEN", "startup_match", m.id,
          old_value={"rank": old_rank}, new_value={"rank": new_rank}, reason=reason.strip())
    return Message(message=f"Ranking overridden ({old_rank} → {new_rank}). Audit record created.")

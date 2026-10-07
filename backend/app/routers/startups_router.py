"""Startup registry + explainable matching router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.engines.matching_engine import WEIGHTS, get_matching_engine
from app.models.challenge import Challenge
from app.models.startup import Startup, StartupMatch
from app.models.user import AuditLog, User
from app.schemas.common import Message
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/startups", tags=["startups"])


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

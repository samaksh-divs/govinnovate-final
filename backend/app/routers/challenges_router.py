"""Challenges: CRUD, AI Requirement Assistant, KPI builder, review gates, publish."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.engines.requirements_engine import get_requirements_engine
from app.models.challenge import AiSuggestion, Challenge, Kpi
from app.models.user import User
from app.schemas.challenge import ChallengeIn, ChallengeOut, KpiIn, SuggestionOut
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


def _serialize(c: Challenge, db: Session) -> dict:
    kpis = db.query(Kpi).filter(Kpi.challenge_id == c.id).all()
    return {
        **ChallengeOut.model_validate(c).model_dump(mode="json"),
        "kpis": [kpi_to_dict(k) for k in kpis],
    }


def kpi_to_dict(k: Kpi) -> dict:
    return {"id": k.id, "name": k.name, "description": k.description, "baseline": k.baseline,
            "target": k.target, "unit": k.unit, "measurement_method": k.measurement_method,
            "evidence_source": k.evidence_source, "success_threshold": k.success_threshold,
            "direction": k.direction, "source": k.source}


# --------------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------------

VISIBLE_ROLES = {"government_officer", "administrator", "startup", "expert", "validator",
                 "senior_authority"}


@router.get("")
def list_challenges(status: str | None = None, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Read endpoint. Startups browse published challenges to apply; experts see the
    challenges they evaluate against. Only officers/admins can create or edit
    (enforced separately below) — reading is part of every persona's workflow."""
    if user.role not in VISIBLE_ROLES:
        raise HTTPException(403, "This role cannot browse challenges.")
    q = db.query(Challenge)
    if status:
        q = q.filter(Challenge.status == status)
    return [_serialize(c, db) for c in q.order_by(Challenge.updated_at.desc()).all()]
    q = db.query(Challenge)
    if status:
        q = q.filter(Challenge.status == status)
    return [_serialize(c, db) for c in q.order_by(Challenge.updated_at.desc()).all()]


@router.post("", status_code=201)
def create_challenge(payload: ChallengeIn, db: Session = Depends(get_db),
                     user: User = Depends(require("CHALLENGE_CREATE"))):
    if not payload.title.strip():
        raise HTTPException(422, "Challenge title is required")
    c = Challenge(id=new_id("CH"), **payload.model_dump(), created_by=user.id)
    db.add(c)
    db.commit()
    audit(db, user, "CHALLENGE_CREATED", "challenge", c.id, new_value={"title": c.title})
    return _serialize(c, db)


@router.get("/{challenge_id}")
def get_challenge(challenge_id: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    if user.role not in VISIBLE_ROLES:
        raise HTTPException(403, "This role cannot view challenges.")
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    return _serialize(c, db)


@router.patch("/{challenge_id}")
def update_challenge(challenge_id: str, payload: ChallengeIn, db: Session = Depends(get_db),
                     user: User = Depends(require("CHALLENGE_EDIT"))):
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    if c.status == "PUBLISHED":
        raise HTTPException(409, "Published challenges are immutable. Create a revision instead.")
    old = {"title": c.title}
    for key, value in payload.model_dump().items():
        setattr(c, key, value)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    audit(db, user, "CHALLENGE_UPDATED", "challenge", c.id, old_value=old,
          new_value={"title": c.title})
    return _serialize(c, db)


@router.delete("/{challenge_id}")
def delete_draft(challenge_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require("CHALLENGE_EDIT"))):
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    if c.status != "DRAFT":
        raise HTTPException(409, "Only DRAFT challenges can be deleted")
    db.query(Kpi).filter(Kpi.challenge_id == c.id).delete()
    db.query(AiSuggestion).filter(AiSuggestion.challenge_id == c.id).delete()
    db.delete(c)
    db.commit()
    audit(db, user, "CHALLENGE_DRAFT_DELETED", "challenge", c.id, old_value={"title": c.title})
    return {"message": "Draft deleted"}


# --------------------------------------------------------------------------
# AI Requirement Assistant
# --------------------------------------------------------------------------

@router.post("/{challenge_id}/ai/analyse")
def ai_analyse(challenge_id: str, db: Session = Depends(get_db),
               user: User = Depends(require("AI_ANALYSE"))):
    """Run the rule-based AI Requirement Engine. Produces PENDING suggestions only."""
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    result = get_requirements_engine().generate({
        "problem_statement": c.problem_statement, "current_situation": c.current_situation,
        "expected_outcome": c.expected_outcome, "constraints": c.constraints,
        "department": c.department,
        "sites": (c.pilot_criteria or {}).get("number_of_sites"),
        "users": (c.pilot_criteria or {}).get("target_users"),
    })
    created = []
    for s in result["suggestions"]:
        rec = AiSuggestion(id=new_id("AIS"), challenge_id=c.id,
                           suggestion_type=s["suggestion_type"], category=s["category"],
                           text=s["text"], rationale=s["rationale"],
                           confidence=s["confidence"], extra=s.get("extra", {}))
        db.add(rec)
        created.append(rec)
    db.commit()
    audit(db, user, "AI_ANALYSIS_GENERATED", "challenge", c.id,
          metadata={"suggestions": len(created), "category": result["category"],
                    "engine_version": result["engine_version"]})
    return {"category": result["category"], "category_confidence": result["category_confidence"],
            "engine_version": result["engine_version"], "notice": result["notice"],
            "suggestions": [_suggestion_out(s) for s in created]}


def _suggestion_out(s: AiSuggestion) -> dict:
    return {"id": s.id, "suggestion_type": s.suggestion_type, "category": s.category,
            "text": s.text, "rationale": s.rationale, "confidence": s.confidence,
            "extra": s.extra or {}, "status": s.status, "edited_text": s.edited_text}


@router.get("/{challenge_id}/ai/suggestions")
def list_suggestions(challenge_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require("AI_ANALYSE"))):
    rows = db.query(AiSuggestion).filter(AiSuggestion.challenge_id == challenge_id).all()
    return [_suggestion_out(s) for s in rows]


@router.post("/suggestions/{suggestion_id}/decide")
def decide_suggestion(suggestion_id: str, decision: str, payload: dict | None = None, db: Session = Depends(get_db),
                      user: User = Depends(require("AI_SUGGESTION_DECIDE"))):
    """Officer accepts / edits / rejects one AI suggestion. Required: explicit action."""
    s = db.query(AiSuggestion).filter(AiSuggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(404, "Suggestion not found")
    if decision not in ("ACCEPT", "EDIT", "REJECT"):
        raise HTTPException(422, "decision must be ACCEPT, EDIT or REJECT")
    payload = payload or {}
    edited_text = (payload.get("edited_text") or "").strip()
    if decision == "EDIT" and not edited_text:
        raise HTTPException(422, "edited_text is required when decision is EDIT")

    s.status = "ACCEPTED" if decision == "ACCEPT" else "EDITED" if decision == "EDIT" else "REJECTED"
    if decision == "EDIT":
        s.edited_text = edited_text
    s.decided_by = user.id
    s.decided_at = datetime.now(timezone.utc)

    accepted_text = s.edited_text or s.text
    if s.status in ("ACCEPTED", "EDITED") and s.suggestion_type == "requirement":
        c = db.query(Challenge).filter(Challenge.id == s.challenge_id).first()
        if not c:
            raise HTTPException(404, "Challenge not found")
        reqs = dict(c.requirements or {})
        # Official requirement set = accepted AI requirements + manually added requirements.
        # 1. The accepted suggestion REPLACES its AI-suggestion slot in the bucket: the
        #    pending suggestion that describes the accepted text is no longer emitted as an
        #    official requirement.
        # 2. Rejected AI suggestions stay out of the official set (never added).
        # 3. Every other pending AI suggestion is dropped from the bucket entirely so a
        #    single accept cannot leave a stale / duplicate copy behind.
        # 4. Manual entries are only ever appended; they are never overwritten or removed by
        #    an accept/reject/edit decision.
        # 5. Duplicate copies (identical text) are collapsed to a single official entry.
        # Official requirement set = accepted AI requirements + manually added requirements.
        # Build the official bucket for this category as follows:
        # 1. Start with all existing requirements in the bucket.
        # 2. Remove any PENDING AI suggestions. We detect pending AI suggestions by querying
        #    the ai_suggestions table for entries that are still PENDING and have this
        #    category. Any requirement text that matches a pending suggestion is dropped.
        # 3. Rejected AI suggestions: they stay out of the official set because once they are
        #    rejected they are never added to the official bucket (they are only stored as
        #    AI suggestions, never copied into requirements). If a text collision occurs with a
        #    manual entry, the manual entry is preserved (it was explicitly added by the officer).
        # 4. The accepted suggestion's text is added EXACTLY ONCE to the official bucket,
        #    replacing any existing copy (pending or duplicate) of the same text.
        # 5. Duplicate copies (identical text from earlier bad accepts) are collapsed to one.
        new_bucket = []
        seen = set()

        # Find all PENDING AI suggestions for this category that should be excluded from
        # the official requirement set.
        pending_texts = set()
        for ps in db.query(AiSuggestion).filter(
            AiSuggestion.challenge_id == c.id,
            AiSuggestion.category == s.category,
            AiSuggestion.status == "PENDING",
        ).all():
            pending_texts.add(str(ps.text or "").strip())

        # First pass: keep existing requirements that are NOT pending AI suggestions.
        for entry in reqs.get(s.category, []) or []:
            entry_text = str(entry or "").strip()
            if not entry_text:
                continue
            if entry_text in pending_texts:
                continue  # pending AI suggestion: drop from official set
            # Keep the entry (it's either manual or a previously accepted AI requirement).
            new_bucket.append(entry_text)
            seen.add(entry_text)

        # Second pass: add the accepted text, deduplicated.
        if accepted_text:
            accepted_key = accepted_text.strip()
            if accepted_key and accepted_key not in seen:
                new_bucket.append(accepted_key)
                seen.add(accepted_key)
            elif accepted_key:
                # Already present: deduplicate.
                pass

        reqs[s.category] = new_bucket
        c.requirements = reqs
        c.updated_at = datetime.now(timezone.utc)

    db.commit()
    audit(db, user, f"AI_SUGGESTION_{s.status}", "ai_suggestion", s.id,
          new_value={"text": accepted_text, "status": s.status},
          reason=f"Officer {decision.lower()}d AI suggestion")
    return {"message": f"Suggestion {s.status.lower()}", "suggestion": _suggestion_out(s)}


# --------------------------------------------------------------------------
# KPI builder
# --------------------------------------------------------------------------

@router.post("/{challenge_id}/kpis", status_code=201)
def add_kpi(challenge_id: str, payload: KpiIn, db: Session = Depends(get_db),
            user: User = Depends(require("CHALLENGE_EDIT"))):
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    if not payload.name.strip():
        raise HTTPException(422, "KPI name is required")
    k = Kpi(id=new_id("KPI"), challenge_id=challenge_id, **payload.model_dump(),
            source="OFFICER")
    db.add(k)
    db.commit()
    audit(db, user, "KPI_ADDED", "kpi", k.id, new_value={"name": k.name, "target": k.target})
    return kpi_to_dict(k)


@router.patch("/{challenge_id}/kpis/{kpi_id}")
def update_kpi(challenge_id: str, kpi_id: str, payload: KpiIn, db: Session = Depends(get_db),
               user: User = Depends(require("CHALLENGE_EDIT"))):
    k = db.query(Kpi).filter(Kpi.id == kpi_id, Kpi.challenge_id == challenge_id).first()
    if not k:
        raise HTTPException(404, "KPI not found")
    for key, value in payload.model_dump().items():
        setattr(k, key, value)
    db.commit()
    audit(db, user, "KPI_UPDATED", "kpi", k.id, new_value={"name": k.name, "target": k.target})
    return kpi_to_dict(k)


@router.delete("/{challenge_id}/kpis/{kpi_id}")
def delete_kpi(challenge_id: str, kpi_id: str, db: Session = Depends(get_db),
               user: User = Depends(require("CHALLENGE_EDIT"))):
    k = db.query(Kpi).filter(Kpi.id == kpi_id, Kpi.challenge_id == challenge_id).first()
    if not k:
        raise HTTPException(404, "KPI not found")
    db.delete(k)
    db.commit()
    audit(db, user, "KPI_DELETED", "kpi", kpi_id, old_value={"name": k.name})
    return {"message": "KPI deleted"}


# --------------------------------------------------------------------------
# Review gates + publish
# --------------------------------------------------------------------------

def publish_validation_errors(c: Challenge, db: Session) -> list[str]:
    errors: list[str] = []
    for field, label in (("title", "Title"), ("department", "Department"),
                         ("problem_statement", "Problem statement"),
                         ("expected_outcome", "Expected outcome")):
        if not (getattr(c, field) or "").strip():
            errors.append(f"{label} is required")
    if not (c.requirements or {}).get("functional"):
        errors.append("At least one functional requirement is required (accept AI suggestions or add manually)")
    if not db.query(Kpi).filter(Kpi.challenge_id == c.id).count():
        errors.append("At least one KPI is required")
    pc = c.pilot_criteria or {}
    if not pc.get("duration_weeks"):
        errors.append("Pilot duration is required")
    if not pc.get("budget_max"):
        errors.append("Pilot budget is required")
    if not (c.data_policy or {}).get("ownership"):
        errors.append("Data ownership policy is required")
    if not (c.cybersecurity or {}).get("authentication"):
        errors.append("Cybersecurity authentication requirement is required")
    return errors


@router.get("/{challenge_id}/review")
def review(challenge_id: str, db: Session = Depends(get_db),
           user: User = Depends(require("CHALLENGE_CREATE"))):
    """Gate check + full review payload for the Review & Publish step."""
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    return {"errors": publish_validation_errors(c, db), "challenge": _serialize(c, db)}


@router.post("/{challenge_id}/publish")
def publish(challenge_id: str, db: Session = Depends(get_db),
            user: User = Depends(require("CHALLENGE_PUBLISH"))):
    c = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not c:
        raise HTTPException(404, "Challenge not found")
    if c.status == "PUBLISHED":
        raise HTTPException(409, "Challenge is already published")
    errors = publish_validation_errors(c, db)
    if errors:
        raise HTTPException(422, detail={"message": "Publish blocked by workflow gates", "errors": errors})
    c.status = "PUBLISHED"
    c.published_at = datetime.now(timezone.utc)
    db.commit()
    audit(db, user, "CHALLENGE_PUBLISHED", "challenge", c.id, new_value={"status": "PUBLISHED"})
    return {"message": "Challenge published and available for startup matching", "challenge": _serialize(c, db)}


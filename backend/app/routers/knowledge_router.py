"""Knowledge Centre: lessons (accept/edit/ignore) and similar-pilot recommendations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.engines.knowledge_engine import get_knowledge_engine
from app.models.decision import GovernmentDecision, KnowledgeLesson, SimilarPilot
from app.models.evidence import ValidationPackage, ValidationReport
from app.models.pilot import Milestone, Pilot, PilotKpi
from app.models.user import User
from app.services.audit import audit, new_id

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/lessons")
def list_lessons(status: str | None = None, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    q = db.query(KnowledgeLesson)
    if status:
        q = q.filter(KnowledgeLesson.status == status)
    return [_out(l) for l in q.order_by(KnowledgeLesson.created_at.desc()).all()]


def _out(l: KnowledgeLesson) -> dict:
    return {"id": l.id, "pilot_id": l.pilot_id, "challenge_id": l.challenge_id,
            "title": l.title, "lesson": l.lesson, "edited_lesson": l.edited_lesson,
            "evidence": l.evidence, "recommendation": l.recommendation, "sector": l.sector,
            "problem_type": l.problem_type, "technology": l.technology, "source": l.source,
            "tags": l.tags or [], "status": l.status,
            "decided_by": l.decided_by, "created_at": l.created_at.isoformat()
            if l.created_at else None}


@router.post("/pilots/{pilot_id}/extract", status_code=201)
def extract_lessons(pilot_id: str, db: Session = Depends(get_db),
                    user: User = Depends(require("KNOWLEDGE_DECIDE"))):
    """Run the KnowledgeEngine over a concluded pilot. Lessons stay PENDING."""
    p = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not p:
        raise HTTPException(404, "Pilot not found")
    kpis = db.query(PilotKpi).filter(PilotKpi.pilot_id == pilot_id).all()
    milestones = db.query(Milestone).filter(Milestone.pilot_id == pilot_id).all()
    pkg = db.query(ValidationPackage).filter(ValidationPackage.pilot_id == pilot_id,
                                             ValidationPackage.status == "REPORT_SUBMITTED") \
        .order_by(ValidationPackage.created_at.desc()).first()
    report = db.query(ValidationReport).filter(ValidationReport.package_id == pkg.id) \
        .order_by(ValidationReport.report_version.desc()).first() if pkg else None
    decision = db.query(GovernmentDecision).filter(GovernmentDecision.pilot_id == pilot_id) \
        .order_by(GovernmentDecision.decided_at.desc()).first()

    candidates = get_knowledge_engine().extract_lessons(
        pilot={"id": p.id, "department": p.department, "objectives": p.objectives,
               "startup_name": p.startup_name, "sites": p.sites, "baseline": p.baseline or {}},
        kpis=[{"name": k.name, "claimed_value": k.claimed_value,
               "observed_value": k.observed_value, "status": k.status} for k in kpis],
        validation={"id": pkg.id if pkg else None,
                    "overall_finding": report.overall_finding if report else "",
                    "validated_kpis": (report.validated_kpis if report else {}) or {}} if pkg else None,
        decision={"id": decision.id, "decision": decision.decision} if decision else None,
        milestones=[{"status": m.status} for m in milestones])

    created = []
    for c in candidates:
        l = KnowledgeLesson(id=new_id("KL"), pilot_id=pilot_id, title=c["title"],
                            lesson=c["lesson"], evidence=c["evidence"],
                            recommendation=c["recommendation"], sector=c.get("sector", ""),
                            problem_type=c.get("problem_type", ""),
                            technology=c.get("technology", ""), tags=c.get("tags", []),
                            status="PENDING", source="KNOWLEDGE_ENGINE")
        db.add(l)
        created.append(l)
    db.commit()
    audit(db, user, "KNOWLEDGE_LESSONS_GENERATED", "pilot", pilot_id,
          metadata={"lessons": len(created), "engine_version": "knowledge-engine@1.1"})
    return {"generated": len(created),
            "notice": "Recommendations are never applied automatically. Accept, edit or ignore each one.",
            "lessons": [_out(l) for l in created]}


@router.post("/lessons/{lesson_id}/decide")
def decide_lesson(lesson_id: str, decision: str, edited_lesson: str | None = None,
                  db: Session = Depends(get_db), user: User = Depends(require("KNOWLEDGE_DECIDE"))):
    l = db.query(KnowledgeLesson).filter(KnowledgeLesson.id == lesson_id).first()
    if not l:
        raise HTTPException(404, "Lesson not found")
    if decision not in ("ACCEPT", "EDIT", "IGNORE"):
        raise HTTPException(422, "decision must be ACCEPT, EDIT or IGNORE")
    if decision == "EDIT" and not (edited_lesson or "").strip():
        raise HTTPException(422, "edited_lesson text is required when decision is EDIT")
    l.status = {"ACCEPT": "ACCEPTED", "EDIT": "EDITED", "IGNORE": "IGNORED"}[decision]
    if decision == "EDIT":
        l.edited_lesson = edited_lesson.strip()
    l.decided_by = user.name
    db.commit()
    audit(db, user, f"KNOWLEDGE_LESSON_{l.status}", "knowledge_lesson", l.id,
          new_value={"title": l.title, "status": l.status})
    return {"message": f"Lesson {l.status.lower()}", "lesson": _out(l)}


# ---- similar pilots ----------------------------------------------------------

@router.get("/similar")
def similar(reference_pilot_id: str | None = None, sector: str | None = None,
            problem_type: str | None = None, technology: str | None = None,
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Explainable similar-pilot recommendations from the demo historical corpus."""
    corpus = [_sp_out(s) for s in db.query(SimilarPilot).all()]
    reference = {"id": reference_pilot_id, "sector": sector or "", "problem_type": problem_type or "",
                 "technology": technology or "", "kpi_focus": problem_type or "",
                 "pilot_size": "MEDIUM", "evidence_quality": "MEDIUM", "outcome": ""}
    results = get_knowledge_engine().similar_pilots(reference, corpus, top_n=4)
    return {"results": [{"pilot": r["pilot"], "similarity": r["similarity"],
                         "why_similar": r["why_similar"]} for r in results],
            "note": "Similarity is explainable: each match lists the dimensions that matched."}


def _sp_out(s: SimilarPilot) -> dict:
    return {"id": s.id, "name": s.name, "department": s.department, "sector": s.sector,
            "problem_type": s.problem_type, "technology": s.technology, "kpi_focus": s.kpi_focus,
            "pilot_size": s.pilot_size, "evidence_quality": s.evidence_quality,
            "outcome": s.outcome, "year": s.year, "summary": s.summary,
            "lessons": s.lessons or []}

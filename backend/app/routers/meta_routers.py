"""Analytics, Audit, System Health and Global Search routers."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, engine
from app.core.deps import get_current_user, require
from app.core.security import PERMISSIONS, ROLE_LABELS
from app.models.challenge import AiSuggestion, Challenge, Kpi
from app.models.decision import DecisionRecommendation, GovernmentDecision, KnowledgeLesson
from app.models.evidence import Evidence, ValidationPackage, ValidationReport
from app.models.pilot import Milestone, Pilot, PilotKpi
from app.models.startup import Startup, StartupMatch
from app.models.user import AuditLog, User
from app.services.audit import audit

audit_router = APIRouter(prefix="/api/audit", tags=["audit"])


@audit_router.get("")
def list_audit(entity_type: str | None = None, entity_id: str | None = None,
               action: str | None = None, limit: int = Query(200, le=1000),
               db: Session = Depends(get_db), user: User = Depends(require("AUDIT_VIEW"))):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    rows = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{"id": r.id, "timestamp": r.timestamp.isoformat() if r.timestamp else None,
             "actor": r.actor_name, "role": r.actor_role, "action": r.action,
             "entity_type": r.entity_type, "entity_id": r.entity_id,
             "old_value": r.old_value, "new_value": r.new_value, "reason": r.reason,
             "metadata": r.metadata_, "correlation_id": r.correlation_id} for r in rows]


analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@analytics_router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Pipeline counters. Zero-denominator metrics are returned as N/A, never 0%."""
    challenges = db.query(Challenge).all()
    pilots = db.query(Pilot).all()
    evidence = db.query(Evidence).all()
    recs = db.query(DecisionRecommendation).order_by(DecisionRecommendation.created_at).all()
    decisions = db.query(GovernmentDecision).all()
    lessons = db.query(KnowledgeLesson).all()

    active_challenges = sum(1 for c in challenges if c.status == "PUBLISHED")
    active_pilots = sum(1 for p in pilots if p.status == "ACTIVE")
    completed = [p for p in pilots if p.status in ("CONCLUDED", "DECIDED", "SCALED", "RE_PILOT")]
    pending_validations = db.query(ValidationPackage) \
        .filter(ValidationPackage.status.in_(["PREPARED", "VALIDATOR_ASSIGNED", "IN_VALIDATION"])).count()
    scale_decisions = sum(1 for d in decisions if d.decision == "SCALE")
    repilots = sum(1 for d in decisions if d.decision == "RE_PILOT")

    validated = [e for e in evidence if e.status in ("VALIDATED", "PARTIALLY_VALIDATED")]
    evidence_quality = (round(100 * len(validated) / len(evidence)), len(evidence)) if evidence else (None, 0)

    latest_by_pilot: dict[str, DecisionRecommendation] = {}
    for r in recs:
        latest_by_pilot[r.pilot_id] = r
    recommendation_counts: dict[str, int] = {}
    for r in latest_by_pilot.values():
        recommendation_counts[r.outcome] = recommendation_counts.get(r.outcome, 0) + 1

    recent = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(6).all()
    return {
        "counters": {
            "active_challenges": {"value": active_challenges, "period": "current"},
            "registered_startups": {"value": db.query(Startup).count(), "period": "current"},
            "active_pilots": {"value": active_pilots, "period": "current"},
            "completed_pilots": {"value": len(completed), "period": "all time"},
            "pending_validations": {"value": pending_validations, "period": "current"},
            "scale_decisions": {"value": scale_decisions, "period": "all time"},
            "re_pilots": {"value": repilots, "period": "all time"},
            "knowledge_lessons": {"value": len(lessons), "period": "all time"},
            "procurement_ready": {"value": sum(1 for p in pilots if p.status == "SCALED"),
                                  "period": "current"},
        },
        "evidence_quality": {
            "display": f"{evidence_quality[0]}%" if evidence_quality[0] is not None else "N/A",
            "numerator": len(validated), "denominator": evidence_quality[1],
            "definition": "share of evidence items validated (VALIDATED or PARTIALLY_VALIDATED)",
            "limitations": ["Integrity (SHA-256) is not truth; this measures review progress only"],
        },
        "recommendation_distribution": recommendation_counts,
        "bottlenecks": _bottlenecks(db, challenges, pilots),
        "recent_activity": [{"action": r.action, "actor": r.actor_name, "entity": r.entity_id,
                             "at": r.timestamp.isoformat() if r.timestamp else None}
                            for r in recent],
        "disclaimer": "All metrics derived from platform records only; sample sizes shown. "
                      "No external data sources are used.",
    }


def _bottlenecks(db: Session, challenges, pilots):
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # SQLite stores naive UTC
    out = []
    for c in challenges:
        if c.status == "DRAFT" and (c.updated_at or now) < now - timedelta(days=7):
            out.append({"stage": "Challenge", "item": c.title or c.id,
                        "issue": "Draft unpublished for over 7 days"})
    for p in pilots:
        if p.status == "ACTIVE":
            overdue = db.query(Milestone).filter(Milestone.pilot_id == p.id,
                                                 Milestone.status.in_(["NOT_STARTED", "IN_PROGRESS"])).count()
            if overdue:
                out.append({"stage": "Pilot", "item": p.name,
                            "issue": f"{overdue} milestone(s) not yet accepted"})
        if p.status == "CONCLUDED":
            out.append({"stage": "Decision", "item": p.name,
                        "issue": "Awaiting decision intelligence / government decision"})
    return out[:8]


system_router = APIRouter(prefix="/api/system", tags=["system"])


@system_router.get("/health")
def health(db: Session = Depends(get_db), user: User = Depends(require("SYSTEM_HEALTH"))):
    """System health for the Administrator console. Honest statuses only."""
    components = []
    db_ok, db_error = True, None
    try:
        db.execute(text("SELECT 1"))
        last_audit = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
        last_op = last_audit.timestamp.isoformat() if last_audit else None
    except Exception as exc:  # pragma: no cover
        db_ok, db_error, last_op = False, str(exc), None
    components.append({"component": "Database", "status": "UP" if db_ok else "DOWN",
                       "detail": engine.url.drivername, "error": db_error})

    components.append({"component": "API", "status": "UP", "detail": f"{settings.APP_NAME} "
                                                                    f"v{settings.VERSION}"})
    components.append({"component": "AI Engine",
                       "status": "UP",
                       "detail": "Rule-based engines: " + settings.ENGINE_VERSIONS})
    # Government data provider subsystem: report real import state, never fake liveness.
    try:
        from app.models.govdata import GovernmentDataset
        ds_count = db.query(GovernmentDataset).count()
        last_refresh = None
        try:
            from app.models.govdata import DataRefreshLog
            lr = db.query(DataRefreshLog).order_by(DataRefreshLog.at.desc()).first()
            last_refresh = lr.at.isoformat() if lr and lr.at else None
        except Exception:
            pass
        components.append({"component": "Government Data Providers",
                           "status": "UP" if ds_count else "NOT_CONFIGURED",
                           "detail": (f"{ds_count} public dataset(s) as versioned snapshots; "
                                      f"live API providers not configured in this build"
                                      + (f"; last refresh {last_refresh}" if last_refresh else "")),
                           "last_refresh": last_refresh})
    except Exception as exc:  # pragma: no cover
        components.append({"component": "Government Data Providers", "status": "DEGRADED",
                           "detail": "gov-data layer not initialized", "error": str(exc)})
    uploads_ok = True
    try:
        import os
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        upload_detail = f"{settings.UPLOAD_DIR} writable"
    except Exception as exc:  # pragma: no cover
        uploads_ok, upload_detail = False, str(exc)
    components.append({"component": "Evidence Storage", "status": "UP" if uploads_ok else "DOWN",
                       "detail": upload_detail})
    components.append({"component": "Background Jobs",
                       "status": "NOT_CONFIGURED",
                       "detail": "No background workers in the demo build; actions run synchronously."})
    warnings = []
    if settings.SECRET_KEY.startswith("demo-only"):
        warnings.append("SECRET_KEY is a demo default — rotate before any real deployment.")
    if settings.DATABASE_URL.startswith("sqlite"):
        warnings.append("SQLite in use — switch DATABASE_URL to PostgreSQL for production.")
    return {"status": "UP" if db_ok and uploads_ok else "DEGRADED",
            "components": components, "last_successful_operation": last_op,
            "warnings": warnings,
            "errors": [] if db_ok else ["Database unreachable"],
            "demo_notice": "Health data reflects the local demo deployment only."}


search_router = APIRouter(prefix="/api/search", tags=["search"])


@search_router.get("")
def global_search(q: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Global search across challenges, startups, pilots, evidence, decisions, knowledge."""
    ql = (q or "").lower()
    if len(ql) < 2:
        return {"results": [], "notice": "Type at least 2 characters."}
    results = []

    def add(kind: str, id_: str, title: str, subtitle: str):
        results.append({"kind": kind, "id": id_, "title": title, "subtitle": subtitle})

    for c in db.query(Challenge).all():
        if ql in (c.title or "").lower() or ql in (c.problem_statement or "").lower():
            add("challenge", c.id, c.title or c.id, f"{c.department} · {c.status}")
    for s in db.query(Startup).all():
        if ql in (s.name or "").lower() or ql in (s.sector or "").lower() or \
                ql in (s.description or "").lower():
            add("startup", s.id, s.name, f"{s.sector} · {s.hq_location}")
    for p in db.query(Pilot).all():
        if ql in (p.name or "").lower() or ql in (p.startup_name or "").lower():
            add("pilot", p.id, p.name, f"{p.startup_name} · {p.status}")
    for e in db.query(Evidence).all():
        if ql in (e.title or "").lower() or ql in (e.description or "").lower():
            add("evidence", e.id, e.title, f"{e.evidence_type} · {e.status}")
    for d in db.query(GovernmentDecision).all():
        if ql in (d.decision or "").lower() or ql in (d.reason or "").lower():
            add("decision", d.pilot_id, f"{d.decision} ({d.decision_type})",
                f"Pilot {d.pilot_id} · by {d.decided_by_name}")
    for k in db.query(KnowledgeLesson).all():
        if ql in (k.title or "").lower() or ql in (k.lesson or "").lower():
            add("knowledge", k.id, k.title, k.sector or "General")
    # government public datasets — result type GOVERNMENT DATA
    try:
        from app.models.govdata import GovernmentDataset
        for g in db.query(GovernmentDataset).all():
            if ql in (g.title or "").lower() or ql in (g.domain or "").lower():
                add("govdata", g.id, g.title,
                    f"{g.data_type} · {g.status} · v{g.current_version}")
    except Exception:
        pass
    return {"results": results[:20], "count": len(results)}

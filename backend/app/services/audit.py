"""Shared audit service: every significant action lands here, append-only."""
import uuid
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import AuditLog, User


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def audit(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    old_value=None,
    new_value=None,
    reason: str | None = None,
    metadata: dict | None = None,
    corr_id: str | None = None,
) -> AuditLog:
    """Write an immutable audit record. Call after the mutating action succeeds."""
    record = AuditLog(
        actor_id=user.id,
        actor_name=user.name,
        actor_role=user.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        metadata_=metadata or {},
        correlation_id=corr_id or correlation_id(),
    )
    db.add(record)
    db.commit()
    return record


def actor(user: User = Depends(get_current_user)) -> User:
    """Convenience alias for endpoints that only need the resolved actor."""
    return user


__all__ = ["audit", "actor", "new_id", "utcnow_iso", "correlation_id", "get_db"]

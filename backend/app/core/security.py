"""JWT creation/verification, password hashing, and the RBAC permission matrix.

Server-side authorization is the single source of truth. The frontend role
switcher is only a demo convenience; every API enforces these checks itself.
"""
import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLES = [
    "government_officer",
    "startup",
    "expert",
    "validator",
    "senior_authority",
    "administrator",
]

ROLE_LABELS = {
    "government_officer": "Government Officer",
    "startup": "Startup",
    "expert": "Expert Evaluator",
    "validator": "Independent Validator",
    "senior_authority": "Senior Government Authority",
    "administrator": "Administrator",
}

# Permission matrix. Every protected endpoint references one of these codes.
PERMISSIONS: dict[str, set[str]] = {
    "CHALLENGE_CREATE": {"government_officer", "administrator"},
    "CHALLENGE_EDIT": {"government_officer", "administrator"},
    "CHALLENGE_PUBLISH": {"government_officer", "administrator"},
    "AI_ANALYSE": {"government_officer", "administrator"},
    "AI_SUGGESTION_DECIDE": {"government_officer", "administrator"},
    "MATCH_RUN": {"government_officer", "administrator"},
    "MATCH_OVERRIDE": {"government_officer", "administrator"},
    "EVALUATION_SUBMIT": {"expert"},
    "COI_DECLARE": {"expert", "validator"},
    "EVALUATION_ASSIGN": {"government_officer", "administrator"},
    "SHORTLIST_DECISION": {"government_officer", "administrator"},
    "PILOT_CREATE": {"government_officer", "administrator"},
    "PILOT_APPROVE": {"government_officer", "administrator"},
    "PILOT_TRANSITION": {"government_officer", "administrator", "startup"},
    "MILESTONE_UPDATE": {"government_officer", "administrator", "startup"},
    "EVIDENCE_SUBMIT": {"startup", "government_officer", "administrator"},
    "EVIDENCE_REVIEW": {"government_officer", "administrator"},
    "EVIDENCE_OBSERVE": {"government_officer", "administrator", "validator"},
    "VALIDATION_ASSIGN": {"government_officer", "administrator"},
    "VALIDATION_SUBMIT": {"validator"},
    "DECISION_REQUEST": {"government_officer", "administrator"},
    "GOVERNMENT_DECISION": {"senior_authority", "administrator"},
    "SCALE_PLAN": {"government_officer", "administrator"},
    "SCALE_APPROVE": {"senior_authority", "administrator"},
    "PROCUREMENT_GENERATE": {"government_officer", "administrator"},
    "REPILOT_PLAN": {"government_officer", "administrator"},
    "KNOWLEDGE_DECIDE": {"government_officer", "administrator"},
    "USER_MANAGE": {"administrator"},
    "DEMO_SEED": {"administrator", "government_officer"},
    "AUDIT_VIEW": {"government_officer", "senior_authority", "administrator"},
    "SYSTEM_HEALTH": {"administrator", "government_officer"},
}


def can(role: str, permission: str) -> bool:
    return role in PERMISSIONS.get(permission, set())


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, name: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "name": name, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

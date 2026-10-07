"""FastAPI dependencies: current user, authentication, RBAC and object-level authorization."""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import PERMISSIONS, can, decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the JWT bearer token to a user. Demo token bypass is explicit."""
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        # Demo mode convenience: X-Demo-Role header may impersonate a seeded role.
        demo_role = request.headers.get("X-Demo-Role", "")
        if demo_role:
            user = db.query(User).filter(User.role == demo_role).first()
            if not user:
                raise HTTPException(status_code=401, detail=f"Unknown demo role '{demo_role}'")
            request.state.demo_role = demo_role
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token or X-Demo-Role header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if payload.get("role") != user.role:
        raise HTTPException(status_code=401, detail="Token role mismatch")
    return user


def require(permission: str):
    """Guard any endpoint with a permission code from the RBAC matrix."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not can(user.role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: '{permission}' is not allowed for role '{user.role}'.",
            )
        return user

    return dependency


def require_any(*permissions: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not any(can(user.role, p) for p in permissions):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: none of {list(permissions)} allowed for role '{user.role}'.",
            )
        return user

    return dependency


def ensure_object_access(user: User, owner_id: str | None, department: str | None = None) -> None:
    """Object-level authorization: startups may only touch their own objects."""
    if user.role == "startup" and owner_id and user.id != owner_id:
        raise HTTPException(status_code=403, detail="You can only access your own records.")

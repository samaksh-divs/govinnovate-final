"""Auth endpoints. Demo accounts are seeded with a documented password."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import ROLE_LABELS, create_access_token, verify_password
from app.models.user import Department, User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(u: User, db: Session) -> dict:
    dept = db.query(Department).filter(Department.id == u.department_id).first()
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role,
            "role_label": ROLE_LABELS.get(u.role, u.role), "organization": u.organization,
            "department": dept.name if dept else None}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(user.id, user.role, user.name)
    return TokenResponse(access_token=token, user=user_out(user, db))


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_out(user, db)


@router.get("/roles")
def roles():
    """Catalog of roles for the demo role switcher."""
    return [{"id": r, "label": ROLE_LABELS[r]} for r in ROLE_LABELS]

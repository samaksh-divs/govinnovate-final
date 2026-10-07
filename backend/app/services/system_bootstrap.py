"""First-run bootstrap: seed the demo dataset automatically when the DB is empty."""
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.seed import seed


def ensure_seeded() -> None:
    db: Session = SessionLocal()
    try:
        seed(db, force=False)
    finally:
        db.close()

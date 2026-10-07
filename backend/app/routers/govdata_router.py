"""Government public-data API: sources, datasets, provenance, ecosystem & problem landscape.

Read endpoints are open to any authenticated user (contextual intelligence).
Refresh/mutating operations are Administrator-only and never overwrite history.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require
from app.models.govdata import (DataRefreshLog, DataSource, DatasetVersion,
                                GovernmentDataset)
from app.models.user import User
from app.services.audit import audit
from app.services.govdata import PROVIDERS, run_all_imports

router = APIRouter(prefix="/api/government-data", tags=["government-data"])


def _iso(dt):
    return dt.isoformat() if dt else None


def _provenance(ds: GovernmentDataset, src: DataSource | None) -> dict:
    return {
        "source": src.organization if src else (ds.source_id or "Unknown"),
        "source_name": src.name if src else ds.source_id,
        "source_url": src.source_url if src else None,
        "dataset": ds.title,
        "dataset_id": ds.id,
        "data_type": ds.data_type,
        "last_updated": _iso(ds.last_updated),
        "retrieved": _iso(ds.retrieved_at),
        "coverage": ds.coverage_note,
        "status": ds.status,           # SNAPSHOT | IMPORTED | LIVE — never pretend live
        "license_note": src.license_note if src else None,
    }


@router.get("/sources")
def list_sources(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(DataSource).order_by(DataSource.name).all()
    return [{"id": s.id, "name": s.name, "organization": s.organization, "domain": s.domain,
             "geography": s.geography, "provider_type": s.provider_type,
             "source_url": s.source_url, "is_live_api": bool(s.is_live_api),
             "license_note": s.license_note,
             "datasets": db.query(GovernmentDataset).filter_by(source_id=s.id).count()}
            for s in rows]


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(GovernmentDataset).filter_by(is_active=True).all()
    srcs = {s.id: s for s in db.query(DataSource).all()}
    out = []
    for ds in rows:
        src = srcs.get(ds.source_id)
        out.append({
            "id": ds.id, "title": ds.title, "source_id": ds.source_id,
            "source_organization": src.organization if src else ds.source_id,
            "domain": ds.domain, "geography": ds.geography, "data_type": ds.data_type,
            "description": ds.description, "update_frequency": ds.update_frequency,
            "last_updated": _iso(ds.last_updated), "retrieved_at": _iso(ds.retrieved_at),
            "records": ds.record_count, "status": ds.status,
            "current_version": ds.current_version, "coverage_note": ds.coverage_note,
            "source_url": src.source_url if src else None,
            "provenance": _provenance(ds, src),
        })
    return out


@router.get("/refresh-status")
def refresh_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Recent refresh/import activity for the Data Source Centre."""
    logs = db.query(DataRefreshLog).order_by(DataRefreshLog.at.desc()).limit(30).all()
    return [{"id": l.id, "dataset_id": l.dataset_id, "provider": l.provider,
             "outcome": l.outcome, "detail": l.detail, "at": _iso(l.at),
             "duration_ms": l.duration_ms} for l in logs]


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    ds = db.get(GovernmentDataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    src = db.get(DataSource, ds.source_id)
    versions = db.query(DatasetVersion).filter_by(dataset_id=dataset_id) \
        .order_by(DatasetVersion.version.desc()).all()
    return {
        **_provenance(ds, src),
        "description": ds.description, "update_frequency": ds.update_frequency,
        "records": ds.record_count, "current_version": ds.current_version,
        "record_count": ds.record_count,
        "versions": [{"version": v.version, "records": v.record_count,
                      "retrieved_at": _iso(v.retrieved_at), "retrieved_by": v.retrieved_by,
                      "checksum": v.checksum, "notes": v.notes} for v in versions],
        "payload": versions[0].payload if versions else None,
    }


@router.get("/datasets/{dataset_id}/metadata")
def dataset_metadata(dataset_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    ds = db.get(GovernmentDataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    src = db.get(DataSource, ds.source_id)
    versions = db.query(DatasetVersion).filter_by(dataset_id=dataset_id) \
        .order_by(DatasetVersion.version.desc()).all()
    return {"provenance": _provenance(ds, src), "description": ds.description,
            "update_frequency": ds.update_frequency, "coverage_note": ds.coverage_note,
            "versions": [{"version": v.version, "records": v.record_count,
                          "retrieved_at": _iso(v.retrieved_at), "checksum": v.checksum,
                          "notes": v.notes} for v in versions],
            "integrity_note": "Checksums verify snapshot integrity only — not the truth of the "
                              "underlying figures."}


@router.get("/ecosystem")
def ecosystem(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Maharashtra Innovation Landscape card data, each value fully cited."""
    from app.services.govdata_seed_views import ecosystem_view
    return ecosystem_view(db)


@router.get("/sectors")
def sectors(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.govdata_seed_views import sectors_view
    return sectors_view(db)


@router.get("/geography")
def geography(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.govdata_seed_views import geography_view
    return geography_view(db)


@router.get("/problems")
def problems(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.govdata_seed_views import problems_view
    return problems_view(db)


@router.post("/refresh")
def refresh_all(db: Session = Depends(get_db), user: User = Depends(require("USER_MANAGE"))):
    """Administrator-only re-import. Creates new versions; history is never overwritten."""
    imported = run_all_imports(db)
    audit(db, user, "GOV_DATA_REFRESH", "government_dataset", "all",
          metadata={"imported": imported["imported"]})
    return {"ok": True, "imported": imported["imported"],
            "note": "Providers are static snapshots in this build; identical content is skipped "
                    "(content-hash). Live API providers can be registered without UI changes."}


@router.get("/providers")
def providers(user: User = Depends(get_current_user)):
    return [{"class": p.__name__, "provider": p.provider_name, "source_id": p.source_id}
            for p in PROVIDERS]

"""Dashboard views over the government public-data layer.

Every view returns data + provenance so the frontend can render
source / last-updated / retrieved / status beside every figure.
Nothing here invents numbers — absence is surfaced as DATA NOT AVAILABLE.
"""
from sqlalchemy.orm import Session

from app.models.govdata import DataSource, DatasetVersion, GovernmentDataset


def _payload(db: Session, dataset_id: str):
    v = db.query(DatasetVersion).filter_by(dataset_id=dataset_id) \
        .order_by(DatasetVersion.version.desc()).first()
    return (v.payload if v else None), v


def _prov(ds: GovernmentDataset | None, db: Session) -> dict | None:
    if ds is None:
        return None
    src = db.get(DataSource, ds.source_id)
    return {
        "source": src.organization if src else ds.source_id,
        "source_name": src.name if src else ds.source_id,
        "source_url": src.source_url if src else None,
        "dataset": ds.title,
        "dataset_id": ds.id,
        "data_type": ds.data_type,
        "last_updated": ds.last_updated.isoformat() if ds.last_updated else None,
        "retrieved": ds.retrieved_at.isoformat() if ds.retrieved_at else None,
        "coverage": ds.coverage_note,
        "status": ds.status,
    }


def ecosystem_view(db: Session) -> dict:
    """Maharashtra Innovation Landscape: headline public figures + policy context."""
    payload, _ = _payload(db, "ds-dpiit-maharashtra-summary")
    policy, _ = _payload(db, "ds-msins-policy-2025")
    state_rows, _ = _payload(db, "ds-dpiit-state-wise")
    state_rows = state_rows or []
    mh = next((r for r in state_rows if r.get("state") == "Maharashtra"), None)

    def card(value, qualifier=None, source=None, available=True, note=None):
        return {"value": value if available else None,
                "display": ("DATA NOT AVAILABLE" if not available or value is None
                            else (qualifier or f"{value:,}")),
                "available": available, "note": note, "source": source}

    def prov_of(dataset_id):
        ds = db.get(GovernmentDataset, dataset_id)
        return _prov(ds, db) if ds else None

    s = (payload or {})
    p = (policy or {}).get("targets", {})
    return {
        "data_status": "GOVERNMENT_PUBLIC_DATA",
        "notice": "Figures below come from published Government of India / Government of "
                  "Maharashtra sources. Where no authoritative figure exists, the card shows "
                  "DATA NOT AVAILABLE rather than an estimate.",
        "cards": [
            {"key": "recognized_startups", "label": "DPIIT-Recognized Startups",
             **card(s.get("recognized_startups_maharashtra", {}).get("value"),
                    s.get("recognized_startups_maharashtra", {}).get("qualifier"),
                    s.get("recognized_startups_maharashtra", {}).get("source")),
             "sub": f"Rank #{s.get('maharashtra_rank', {}).get('value', '—')} among all states" if s.get("maharashtra_rank") else None,
             "provenance": prov_of("ds-dpiit-maharashtra-summary")},
            {"key": "india_total", "label": "India — Recognized Startups",
             **card(s.get("india_total_recognized", {}).get("value"),
                    s.get("india_total_recognized", {}).get("qualifier"),
                    s.get("india_total_recognized", {}).get("source")),
             "sub": None,
             "provenance": prov_of("ds-dpiit-maharashtra-summary")},
            {"key": "employment", "label": "Direct Jobs via Startups (India)",
             **card(s.get("direct_employment_india", {}).get("value"),
                    s.get("direct_employment_india", {}).get("qualifier"),
                    s.get("direct_employment_india", {}).get("source")),
             "sub": "DPIIT decade data (all India)",
             "provenance": prov_of("ds-dpiit-maharashtra-summary")},
            {"key": "women_directors", "label": "Startups with Woman Director (India)",
             **card(s.get("startups_with_woman_director_india", {}).get("value"),
                    s.get("startups_with_woman_director_india", {}).get("qualifier"),
                    s.get("startups_with_woman_director_india", {}).get("source")),
             "sub": "DPIIT decade data (all India)",
             "provenance": prov_of("ds-dpiit-maharashtra-summary")},
            {"key": "policy_pilot_orders", "label": "Govt Pilot Work Orders (Policy)",
             **card(True, p.get("government_pilot_work_orders", "DATA NOT AVAILABLE"),
                    "Maharashtra Startup, Entrepreneurship & Innovation Policy 2025",
                    available=bool(p.get("government_pilot_work_orders"))),
             "sub": "Maharashtra Startup Week · 50 startups/year",
             "provenance": prov_of("ds-msins-policy-2025")},
            {"key": "incubators_2018", "label": "Incubators Funded (2018 Policy)",
             **card(True, "16 incubators (state-wide network)",
                    "MSInS public portal"),
             "sub": "Current live incubator count: DATA NOT AVAILABLE",
             "provenance": prov_of("ds-msins-ecosystem-programs")},
        ],
        "accelerators_note": "Total accelerator count: DATA NOT AVAILABLE — MSInS does not "
                             "publish a single authoritative figure.",
        "maharashtra_rank": s.get("maharashtra_rank", {}).get("value"),
        "state_leaders": [{"state": r.get("state"), "startups": r.get("startups")}
                          for r in state_rows[:6]],
        "provenance": [prov_of("ds-dpiit-maharashtra-summary"),
                       prov_of("ds-dpiit-state-wise"),
                       prov_of("ds-msins-policy-2025")],
    }


def sectors_view(db: Session) -> dict:
    """National DPIIT sector distribution (clearly scoped — not Maharashtra-only)."""
    rows, _ = _payload(db, "ds-dpiit-sector-national")
    rows = rows or []
    return {
        "data_status": "GOVERNMENT_PUBLIC_DATA",
        "title": "Startup Ecosystem by Sector",
        "subtitle": "Sector distribution of DPIIT-recognized startups (India, 2017-2021 window).",
        "coverage_note": "Source dataset is national and time-boxed (2017-2021). A "
                         "Maharashtra-only sector split is not available in this public dataset; "
                         "none is estimated.",
        "sectors": [{"sector": r["sector"], "share_percent": r["share_percent"]} for r in rows],
        "provenance": _prov(db.get(GovernmentDataset, "ds-dpiit-sector-national"), db),
    }


def geography_view(db: Session) -> dict:
    """State-ranking view. District-level data is NOT in the source dataset — say so."""
    rows, _ = _payload(db, "ds-dpiit-state-wise")
    rows = rows or []
    return {
        "data_status": "GOVERNMENT_PUBLIC_DATA",
        "title": "Maharashtra Innovation Footprint",
        "subtitle": "State-wise DPIIT startup counts (top states).",
        "district_note": "District-level coverage unavailable in source dataset. Rankings below "
                         "are state-level DPIIT counts.",
        "states": rows[:6],
        "provenance": _prov(db.get(GovernmentDataset, "ds-dpiit-state-wise"), db),
    }


def problems_view(db: Session) -> dict:
    """Government Problem Landscape: public indicators where they exist, explicit gaps elsewhere."""
    payload, _ = _payload(db, "ds-ogd-problem-landscape")
    items = []
    for key, row in (payload or {}).items():
        available = row.get("source") is not None and not str(row.get("value", "")).startswith("DATA NOT")
        items.append({
            "key": key,
            "problem_area": row.get("problem_area"),
            "indicator": row.get("indicator"),
            "value": row.get("value"),
            "scope": row.get("scope"),
            "source": row.get("source"),
            "innovation_opportunity": row.get("innovation_opportunity"),
            "available": available,
            "display": row.get("value") if available else "DATA NOT AVAILABLE",
        })
    order = ["water", "agriculture", "public_health", "education", "urban_infrastructure",
             "waste_management", "mobility", "energy", "environment", "rural_development",
             "citizen_services"]
    items.sort(key=lambda r: order.index(r["key"]) if r["key"] in order else 99)
    return {
        "data_status": "GOVERNMENT_PUBLIC_DATA",
        "title": "Government Problem Landscape",
        "subtitle": "Public service-delivery indicators that frame problem areas for innovation "
                    "discovery. Only authoritatively sourced indicators are shown as values.",
        "notice": "Water indicator is a national Jal Jeevan Mission figure — the platform does "
                  "not claim Maharashtra-specific values where the source does not provide them.",
        "problems": items,
        "provenance": _prov(db.get(GovernmentDataset, "ds-ogd-problem-landscape"), db),
    }

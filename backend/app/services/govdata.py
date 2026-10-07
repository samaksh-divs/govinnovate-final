"""GovernmentDataProvider abstraction — pluggable ingestion for public datasets.

Implementations ship static snapshots today (clearly labeled), with the same
interface an API-backed provider (OGD/MSInS/DPIIT live APIs) would implement.
The architecture allows live APIs to replace static imports without touching
frontend or dashboard code.
"""
from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.govdata import DataRefreshLog, DataSource, DatasetVersion, GovernmentDataset

logger = logging.getLogger("govinnovate.govdata")


def _canonical_checksum(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class GovernmentDataProvider(ABC):
    """One provider instance owns a set of datasets (source_id prefix)."""
    source_id: str = ""
    provider_name: str = ""

    @abstractmethod
    def datasets(self) -> list[dict]:
        """Return dataset descriptors with `payload` (the snapshot content)."""

    def import_all(self, db: Session) -> list[dict]:
        """Import/upsert datasets as NEW immutable versions. Never overwrite history."""
        results = []
        src = db.get(DataSource, self.source_id)
        if not src:
            logger.warning("provider %s missing DataSource row; skipping", self.source_id)
            return results
        for ds in self.datasets():
            descriptor = {k: v for k, v in ds.items() if k != "payload"}
            # SQLite DateTime columns need real datetime objects, not ISO strings.
            if isinstance(descriptor.get("last_updated"), str):
                try:
                    from datetime import date
                    descriptor["last_updated"] = datetime.combine(
                        date.fromisoformat(descriptor["last_updated"]), datetime.min.time())
                except ValueError:
                    descriptor["last_updated"] = None
            payload = ds["payload"]
            row = db.get(GovernmentDataset, ds["id"])
            import time
            t0 = time.time()
            try:
                if not row:
                    row = GovernmentDataset(id=ds["id"], source_id=self.source_id)
                    db.add(row)
                for k, v in descriptor.items():
                    if k != "id" and hasattr(row, k):
                        setattr(row, k, v)
                # versioned insert
                prev = db.query(DatasetVersion).filter_by(dataset_id=ds["id"]) \
                    .order_by(DatasetVersion.version.desc()).first()
                version = (prev.version + 1) if prev else 1
                # skip identical re-imports (content-hash) — still log the refresh attempt
                checksum = _canonical_checksum(payload)
                if prev and prev.checksum == checksum:
                    db.add(DataRefreshLog(dataset_id=ds["id"], provider=self.provider_name,
                                          outcome="SKIPPED",
                                          detail=f"content unchanged (v{version - 1})",
                                          duration_ms=int((time.time() - t0) * 1000)))
                    continue
                db.add(DatasetVersion(
                    dataset_id=ds["id"], version=version, payload=payload,
                    record_count=len(payload) if isinstance(payload, list) else 1,
                    retrieved_at=datetime.utcnow(), retrieved_by=self.provider_name,
                    source_url=ds.get("source_url"), checksum=checksum,
                    notes=ds.get("import_note")))
                row.current_version = version
                row.record_count = len(payload) if isinstance(payload, list) else 1
                row.retrieved_at = datetime.utcnow()
                row.status = ds.get("status", "SNAPSHOT")
                db.add(DataRefreshLog(dataset_id=ds["id"], provider=self.provider_name,
                                      outcome="SUCCESS" if row.status != "UNAVAILABLE" else "SNAPSHOT_ONLY",
                                      detail=f"imported v{version} ({row.record_count} records)",
                                      duration_ms=int((time.time() - t0) * 1000)))
                results.append({"dataset": ds["id"], "version": version,
                                "records": row.record_count, "status": row.status})
            except Exception as exc:  # pragma: no cover
                db.add(DataRefreshLog(dataset_id=ds["id"], provider=self.provider_name,
                                      outcome="FAILED", detail=str(exc)[:500],
                                      duration_ms=int((time.time() - t0) * 1000)))
                logger.exception("import failed for %s", ds["id"])
        db.commit()
        return results


# ---------------------------------------------------------------------------
# REAL, PUBLICLY DOCUMENTED FIGURES — every number carries a citation below.
# Nothing here is invented; where a figure is unavailable the dataset says so.
# ---------------------------------------------------------------------------

class DPIITStartupDataProvider(GovernmentDataProvider):
    source_id = "src-dpiit"
    provider_name = "DPIITDataProvider"
    _DS = [
        {
            "id": "ds-dpiit-state-wise",
            "title": "DPIIT-Recognized Startups by State/UT",
            "domain": "startup-ecosystem", "geography": "India",
            "data_type": "GOVERNMENT_PUBLIC_DATA",
            "description": "State-wise count of startups recognized by the Department for "
                           "Promotion of Industry and Internal Trade (DPIIT), Govt of India. "
                           "Maharashtra leads all states.",
            "update_frequency": "Periodic (DPIIT dashboard / PIB releases)",
            "last_updated": "2026-04-18",   # PIB release date (FY2025-26 figures)
            "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019",
            "import_note": "Snapshot transcribed from PIB release PRID 2253019 (Apr 2026) "
                           "and DPIIT data reported Jan 2026 (The Federal). Top 6 states shown.",
            "status": "SNAPSHOT",
            "coverage_note": "State-level only. District-level coverage unavailable in source dataset.",
            "payload": [
                {"state": "Maharashtra", "startups": 38660, "rank": 1},
                {"state": "Karnataka", "startups": 21163, "rank": 2},
                {"state": "Uttar Pradesh", "startups": 20163, "rank": 3},
                {"state": "Delhi", "startups": 19913, "rank": 4},
                {"state": "Gujarat", "startups": 17691, "rank": 5},
                {"state": "Tamil Nadu", "startups": 13780, "rank": 6},
            ],
        },
        {
            "id": "ds-dpiit-maharashtra-summary",
            "title": "Maharashtra Startup Ecosystem Summary (DPIIT)",
            "domain": "startup-ecosystem", "geography": "Maharashtra",
            "data_type": "GOVERNMENT_PUBLIC_DATA",
            "description": "Headline indicators for Maharashtra's DPIIT-recognized startup "
                           "ecosystem: recognized startups, national share, employment "
                           "generated, women-director startups (national), India total.",
            "update_frequency": "Periodic (PIB / DPIIT)",
            "last_updated": "2026-04-18",
            "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019",
            "import_note": "Values as publicly reported: PIB FY26 release (38,660+ Maharashtra; "
                           "2.23 lakh+ India; 4,13,900+ jobs MS column) and DPIIT decade data "
                           "(99,640 startups with ≥1 woman director, India; 12.4 lakh direct jobs).",
            "status": "SNAPSHOT",
            "payload": {
                "recognized_startups_maharashtra": {"value": 38660, "qualifier": "38,660+ (FY 2025-26)",
                                                    "source": "PIB release PRID 2253019, Apr 2026"},
                "india_total_recognized": {"value": 223000, "qualifier": "2.23 lakh+",
                                           "source": "PIB release PRID 2253019, Apr 2026"},
                "national_share_percent": {"value": 17.3, "qualifier": "≈17% of national total",
                                           "source": "computed from DPIIT state data (38,660 / 223,000)"},
                "maharashtra_rank": {"value": 1, "qualifier": "highest among all states",
                                     "source": "DPIIT state-wise data, Jan 2026"},
                "startups_with_woman_director_india": {"value": 99640, "qualifier": "≈99,640 (India)",
                                                       "source": "DPIIT decade data, Jan 2026"},
                "direct_employment_india": {"value": 1240000, "qualifier": "12.4 lakh direct jobs (India)",
                                            "source": "DPIIT decade data, Jan 2026"},
            },
        },
        {
            "id": "ds-dpiit-sector-national",
            "title": "Recognized Startups by Sector (India, DPIIT)",
            "domain": "startup-ecosystem", "geography": "India",
            "data_type": "GOVERNMENT_PUBLIC_DATA",
            "description": "Sector distribution of DPIIT-recognized startups nationally "
                           "(2017-2021 window published by DPIIT; IT Services leads).",
            "update_frequency": "Historical series (2017-2021)",
            "last_updated": "2022-12-13",
            "source_url": "https://factly.in/data-close-to-30-of-startups-recognized-by-the-government-are-into-it-services-healthcare-life-sciences-and-education/",
            "import_note": "Published DPIIT sector shares (59,787 startups, 2017-2021): "
                           "IT Services ~13%, Healthcare & Life Sciences 9.2%, Education 6.8%, "
                           "remainder distributed across 56 sectors.",
            "status": "SNAPSHOT",
            "coverage_note": "National distribution (2017-2021). Maharashtra-only sector split "
                             "not present in this public dataset.",
            "payload": [
                {"sector": "IT Services", "share_percent": 13.0, "window": "2017-2021"},
                {"sector": "Healthcare & Life Sciences", "share_percent": 9.2, "window": "2017-2021"},
                {"sector": "Education", "share_percent": 6.8, "window": "2017-2021"},
                {"sector": "Professional & Commercial Services", "share_percent": 6.5, "window": "2017-2021"},
                {"sector": "Agriculture", "share_percent": 5.8, "window": "2017-2021"},
                {"sector": "Food & Beverages", "share_percent": 5.2, "window": "2017-2021"},
                {"sector": "All other sectors (50+)", "share_percent": 53.5, "window": "2017-2021"},
            ],
        },
    ]

    def datasets(self) -> list[dict]:
        return self._DS


class MSInSPolicyDataProvider(GovernmentDataProvider):
    """Maharashtra State Innovation Society — official policy & program facts."""
    source_id = "src-msins"
    provider_name = "MSInSDataProvider"
    _DS = [
        {
            "id": "ds-msins-policy-2025",
            "title": "Maharashtra Startup, Entrepreneurship & Innovation Policy 2025",
            "domain": "policy", "geography": "Maharashtra",
            "data_type": "GOVERNMENT_PUBLIC_DATA",
            "description": "Official state policy targets and instruments: 50,000 startups by 2030, "
                           "1.25 lakh entrepreneurs supported, ₹500 Cr Maha-Fund (₹5-10 lakh loans "
                           "at 3%), ₹25 lakh government pilot work orders via Maharashtra Startup "
                           "Week (50 startups/year), incubation support up to ₹5 Cr per centre.",
            "update_frequency": "Per policy revision",
            "last_updated": "2025-09-11",
            "source_url": "https://msins.in/assets/Maharashtra-Startup-Entrepreneurship-_-Innovation-Policy-2025-C5OBUYrd.pdf",
            "import_note": "Transcribed from the official MSInS policy PDF (msins.in) and its "
                           "published summaries.",
            "status": "SNAPSHOT",
            "payload": {
                "policy_name": "Maharashtra Startup, Entrepreneurship & Innovation Policy 2025",
                "nodal_agency": "Maharashtra State Innovation Society (MSInS), est. 2017",
                "targets": {
                    "startups_by_2030": 50000,
                    "entrepreneurs_supported": 125000,
                    "maha_fund_corpus_cr": 500,
                    "maha_fund_loans": "₹5-10 lakh at 3% interest to 25,000 early-stage entrepreneurs",
                    "government_pilot_work_orders": "₹25 lakh per work order, 50 startups/year via Maharashtra Startup Week",
                    "incubation_support_per_centre": "Up to ₹5 crore",
                    "innovation_city": "300-acre Maharashtra Innovation City",
                },
                "relevance_to_govinnovate": "The policy's ₹25 lakh government pilot work-order "
                                            "mechanism is the statutory basis for pilot-based "
                                            "innovation procurement — GovInnovate provides the "
                                            "evidence-gated workflow around it.",
            },
        },
        {
            "id": "ds-msins-ecosystem-programs",
            "title": "MSInS Ecosystem Programs & Incubation Network",
            "domain": "policy", "geography": "Maharashtra",
            "data_type": "GOVERNMENT_PUBLIC_DATA",
            "description": "Publicly documented MSInS ecosystem facts: nodal agency role, "
                           "state-wide incubator network funding, startup helpline, Seed Fund Scheme.",
            "update_frequency": "As published on msins.in",
            "last_updated": "2026-01-04",
            "source_url": "https://msins.in/",
            "import_note": "From msins.in public pages: 2018 policy funded a state-wide network "
                           "of 16 startup incubators; MSInS Seed Fund up to ₹10 lakh; helpline "
                           "with MCCIA. Current incubator/accelerator totals are NOT published "
                           "as a single authoritative number — shown as unavailable rather than estimated.",
            "status": "SNAPSHOT",
            "coverage_note": "Total live incubator/accelerator counts are not published by MSInS "
                             "as a single authoritative figure; DATA NOT AVAILABLE shown where applicable.",
            "payload": {
                "nodal_agency": "Maharashtra State Innovation Society (MSInS)",
                "established": 2017,
                "incubators_funded_2018_policy": {"value": 16, "qualifier": "state-wide network funded under the 2018 policy"},
                "seed_fund_scheme": "MSInS Seed Fund Scheme — up to ₹10 lakh per startup",
                "startup_helpline": "In partnership with MCCIA (publicly announced Jan 2026)",
                "current_incubator_count": "DATA NOT AVAILABLE — no single authoritative public figure",
                "accelerator_count": "DATA NOT AVAILABLE — no single authoritative public figure",
            },
        },
    ]

    def datasets(self) -> list[dict]:
        return self._DS


class OGDProblemLandscapeProvider(GovernmentDataProvider):
    """Government problem-landscape indicators from public-domain domain sources.

    Water indicator is genuine public sector data (Jal Jeevan Mission / Ministry of
    Jal Shakti). Others are explicitly marked DATA NOT AVAILABLE in this build.
    """
    source_id = "src-ogd"
    provider_name = "OGDDataProvider"
    _DS = [
        {
            "id": "ds-ogd-problem-landscape",
            "title": "Government Problem Landscape — Public Service Indicators",
            "domain": "problems", "geography": "Maharashtra",
            "data_type": "GOVERNMENT_PUBLIC_DATA",
            "description": "Publicly reported service-delivery indicators that frame government "
                           "problem areas for innovation discovery. Only indicators with "
                           "authoritative public sources are populated; others are explicitly "
                           "marked unavailable.",
            "update_frequency": "As per parent national programs",
            "last_updated": "2026-08-25",
            "source_url": "https://ejalshakti.gov.in/",
            "import_note": "Non-revenue water figure: Jal Jeevan Mission / Ministry of Jal Shakti "
                           "public bulletin (Aug 2026): average non-revenue water in India ≈ 40% "
                           "of production. Maharashtra-specific NRW: DATA NOT AVAILABLE in this snapshot.",
            "status": "SNAPSHOT",
            "coverage_note": "NRW figure is a national average, not Maharashtra-specific. "
                             "District-level coverage unavailable in source dataset.",
            "payload": {
                "water": {
                    "problem_area": "Water",
                    "indicator": "Non-revenue water (leakage + commercial losses)",
                    "value": "≈40% of water production",
                    "scope": "India average (Jal Jeevan Mission public bulletin, Aug 2026)",
                    "source": "Ministry of Jal Shakti — Jal Jeevan Mission (ejalshakti.gov.in)",
                    "innovation_opportunity": "Smart metering, leakage detection, pressure "
                                              "management, NRW analytics",
                },
                "agriculture": {"problem_area": "Agriculture", "indicator": "—",
                                "value": "DATA NOT AVAILABLE in current snapshot",
                                "source": None, "innovation_opportunity": "Soil health analytics, "
                                "advisory systems, post-harvest logistics"},
                "public_health": {"problem_area": "Public Health", "indicator": "—",
                                  "value": "DATA NOT AVAILABLE in current snapshot",
                                  "source": None, "innovation_opportunity": "Facility analytics, "
                                  "supply-chain traceability, telemedicine"},
                "education": {"problem_area": "Education", "indicator": "—",
                              "value": "DATA NOT AVAILABLE in current snapshot",
                              "source": None, "innovation_opportunity": "Learning outcomes, "
                              "school operations, teacher deployment"},
                "urban_infrastructure": {"problem_area": "Urban Infrastructure", "indicator": "—",
                                         "value": "DATA NOT AVAILABLE in current snapshot",
                                         "source": None, "innovation_opportunity": "Asset "
                                         "monitoring, project tracking, utility GIS"},
                "waste_management": {"problem_area": "Waste Management", "indicator": "—",
                                     "value": "DATA NOT AVAILABLE in current snapshot",
                                     "source": None, "innovation_opportunity": "Route optimization, "
                                     "waste segregation tracking, landfill analytics"},
                "mobility": {"problem_area": "Mobility", "indicator": "—",
                             "value": "DATA NOT AVAILABLE in current snapshot",
                             "source": None, "innovation_opportunity": "Fleet telemetry, "
                             "passenger information, traffic analytics"},
                "energy": {"problem_area": "Energy", "indicator": "—",
                           "value": "DATA NOT AVAILABLE in current snapshot",
                           "source": None, "innovation_opportunity": "Distribution losses, "
                           "rooftop solar monitoring, demand response"},
                "environment": {"problem_area": "Environment", "indicator": "—",
                                "value": "DATA NOT AVAILABLE in current snapshot",
                                "source": None, "innovation_opportunity": "Air/water quality "
                                "sensing, compliance monitoring"},
                "rural_development": {"problem_area": "Rural Development", "indicator": "—",
                                      "value": "DATA NOT AVAILABLE in current snapshot",
                                      "source": None, "innovation_opportunity": "Asset "
                                      "verification, service delivery tracking"},
                "citizen_services": {"problem_area": "Citizen Services", "indicator": "—",
                                     "value": "DATA NOT AVAILABLE in current snapshot",
                                     "source": None, "innovation_opportunity": "Grievance "
                                     "triage, service-status automation"},
            },
        },
    ]

    def datasets(self) -> list[dict]:
        return self._DS


PROVIDERS: list[type[GovernmentDataProvider]] = [
    DPIITStartupDataProvider, MSInSPolicyDataProvider, OGDProblemLandscapeProvider,
]


def run_all_imports(db: Session) -> dict:
    """Import every registered provider (idempotent, content-hash versioned)."""
    out = []
    for p in PROVIDERS:
        out.extend(p().import_all(db))
    return {"imported": out}


def ensure_govdata_seeded(db: Session | None = None) -> None:
    """Idempotent bootstrap of data sources + datasets (called at app startup)."""
    own = db is None
    if own:
        from app.core.database import SessionLocal
        db = SessionLocal()
    try:
        sources = [
            {"id": "src-dpiit", "name": "DPIIT / Startup India (via PIB releases & DPIIT data)",
             "organization": "Department for Promotion of Industry and Internal Trade, Govt of India",
             "domain": "startup-ecosystem", "geography": "India",
             "provider_type": "DPIIT", "is_live_api": False,
             "source_url": "https://www.data.gov.in/catalog/startup-recognized-dpiit",
             "license_note": "Government of India public data; Open Government Data policy.",
             "contact_note": "data.gov.in catalog: 'Startup recognized by DPIIT'"},
            {"id": "src-msins", "name": "Maharashtra State Innovation Society (MSInS)",
             "organization": "Government of Maharashtra — MSInS",
             "domain": "innovation-policy", "geography": "Maharashtra",
             "provider_type": "MSINS", "is_live_api": False,
             "source_url": "https://msins.in/",
             "license_note": "Official Government of Maharashtra publications.",
             "contact_note": "Policy PDF + public portal content"},
            {"id": "src-ogd", "name": "Open Government Data / Jal Jeevan Mission",
             "organization": "Ministry of Jal Shakti via data.gov.in ecosystem",
             "domain": "public-service-indicators", "geography": "India",
             "provider_type": "OGD", "is_live_api": False,
             "source_url": "https://ejalshakti.gov.in/",
             "license_note": "Government of India public data.",
             "contact_note": "Public bulletins; OGD catalog mirrors"},
        ]
        for s in sources:
            if not db.get(DataSource, s["id"]):
                db.add(DataSource(**s))
        db.commit()
        run_all_imports(db)
    finally:
        if own:
            db.close()

"""Demo data seeder.

Every record here is FICTIONAL and marked is_demo=True. The UI must display
DEMO DATA wherever these records appear. Nothing in this file represents a real
company, person or government dataset.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.core.security import hash_password
from app.models.challenge import Challenge, Kpi
from app.models.decision import (DecisionRecommendation, GovernmentDecision,
                                 KnowledgeLesson, ProcurementPackage, RepilotPlan,
                                 ScaleUpPlan, SimilarPilot)
from app.models.evidence import (Evidence, ValidationFinding, ValidationPackage,
                                 ValidatorAssignment, ValidationReport)
from app.models.evaluation import (CoiDeclaration, Evaluation, EvaluationAggregate,
                                   ExpertAssignment)
from app.models.pilot import Milestone, PaymentPlan, Pilot, PilotKpi
from app.models.startup import Startup, StartupMatch
from app.models.user import Department, User

DEMO_PASSWORD = "govinnovate-demo"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    return utcnow() - timedelta(days=n)


SECTORS = [
    ("Water Management", ["water", "leakage", "pipeline", "metering"]),
    ("Agriculture", ["crop", "soil", "farmer", "irrigation"]),
    ("Healthcare", ["health", "patient", "clinic", "diagnostics"]),
    ("Urban Mobility", ["traffic", "transport", "parking", "roads"]),
    ("Energy", ["power", "grid", "streetlight", "solar"]),
    ("Waste Management", ["waste", "segregation", "recycling", "sanitation"]),
    ("Education", ["school", "learning", "student", "attendance"]),
    ("Public Safety", ["emergency", "surveillance", "disaster", "complaint"]),
    ("GovTech", ["grievance", "records", "service", "compliance"]),
]

_STARTUP_NAMES = [
    "AquaSense Technologies", "JalDrishti Analytics", "FlowGuard Systems", "NeerTrack Solutions",
    "HydroGrid Labs", "AgraSense IoT", "KisanVision Agrotech", "SoilSarthi Data Labs",
    "CropPulse Analytics", "KrishiNetra Systems", "ArogyaFlow Health", "SehatSathi Care",
    "MediReach Diagnostics", "PulsePhc Technologies", "NagarYatra Mobility", "TrafficMirror AI",
    "RouteSetu Labs", "ParkVaahan Systems", "UrjaMitra Energy", "GridSight Analytics",
    "Streetlamp Networks", "SolarSetu Energy", "SwachhaTrack Systems", "WasteWise Analytics",
    "SortNeta Robotics", "CleanPath Solutions", "ShikshaSetu Edtech", "VidyaLens Analytics",
    "Pathshala Pulse", "GuruTrack Systems", "SurakshaNet Safety", "AlertSetu Response",
    "DisasterDrishti Labs", "NagarVani Grievance", "RecordRoom AI", "SevaSetu Platform",
    "ComplianceKart Systems", "BhumiReg Land Data", "JalShakti Metering", "PaniPath Analytics",
    "SmartNala Monitoring", "VrukshaSense Environment",
]


def _startup_records() -> list[dict]:
    records = []
    for i, name in enumerate(_STARTUP_NAMES):
        sector, keywords = SECTORS[i % len(SECTORS)]
        verified = i % 4 == 0  # every 4th startup has an independently verified pilot
        pilots = []
        if i % 3 != 2:
            pilots.append({"name": f"{sector} pilot — Pimpri-Chinchwad (demo)",
                           "sector": sector, "duration": "10 weeks",
                           "target": "20%", "observed": "17.5%", "verified": verified})
        if i % 5 == 1:
            pilots.append({"name": f"{sector} instrumentation trial — Nashik (demo)",
                           "sector": sector, "duration": "6 weeks",
                           "target": "15%", "observed": "14%", "verified": False})
        records.append({
            "id": f"ST-{i + 1:03d}",
            "name": name,
            "sector": sector,
            "description": f"[FICTIONAL DEMO STARTUP] {name} builds {keywords[0]}-focused technology "
                           f"for municipal departments. Data shown is synthetic and for evaluation "
                           f"demonstration only.",
            "technology": [f"{kw.capitalize()} IoT" for kw in keywords[:2]] + ["Mobile App", "Dashboards"],
            "problem_areas": keywords + [sector],
            "hq_location": ["Pune", "Mumbai", "Nashik", "Nagpur", "Aurangabad", "Kolhapur"][i % 6]
                           + ", Maharashtra",
            "founded_year": str(2016 + (i % 8)),
            "team_size": 8 + (i * 3) % 40,
            "stage": ["Prototype", "Early Revenue", "Growth", "Scale-ready"][i % 4],
            "dpiit_registered": i % 7 != 5,
            "experience_years": 1 + (i % 7),
            "previous_pilots": pilots,
            "evidence_summary": {"submissions": len(pilots) * 3,
                                 "independently_verified": verified,
                                 "note": "Integrity checksums prove file integrity, not truth."},
            "eligibility": {"dpiit_registered": i % 7 != 5,
                            "certifications": i % 3 != 1,
                            "financial_compliance": i % 4 != 3},
            "scalability": {"score": 40 + (i * 7) % 55, "multi_city": i % 2 == 0},
            "risk_profile": {"overall": ["LOW", "MEDIUM", "MEDIUM", "HIGH"][i % 4],
                             "notes": "Synthetic risk profile for demo evaluation."},
            "relevant_projects": [f"{sector} dashboard for a municipal corporation (demo)"],
            "pricing": f"₹{(i % 5 + 2) * 2},00,000 – ₹{(i % 5 + 4) * 3},00,000 (pilot range)",
        })
    return records


DEPARTMENTS = [
    ("D-WATER", "Municipal Water Department", "WTR"),
    ("D-UD", "Urban Development Department", "UDD"),
    ("D-AGRI", "Agriculture Department", "AGR"),
    ("D-HEALTH", "Public Health Department", "PHD"),
    ("D-TRANSPORT", "Transport Department", "TRN"),
]


def seed(db: Session, force: bool = False) -> dict:
    """Idempotent seed. Use force=True (admin) to rebuild the demo dataset."""
    # Ensure the schema exists before any query (first run on a fresh database).
    Base.metadata.create_all(bind=engine)
    existing = db.query(User).count()
    if existing and not force:
        return {"seeded": False, "reason": "Database already contains data"}

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # ---- departments & users -------------------------------------------------
    for dept_id, name, code in DEPARTMENTS:
        db.add(Department(id=dept_id, name=name, code=code))
    db.flush()

    users = [
        ("U-OFF1", "arjun.kulkarni@demo.gov.in", "Arjun Kulkarni", "government_officer",
         "Municipal Water Department", "D-WATER", "Water Operations Cell"),
        ("U-SEN1", "meera.deshmukh@demo.gov.in", "Meera Deshmukh", "senior_authority",
         "Urban Development Department", "D-UD", "Joint Secretary (IAS Desk)"),
        ("U-START1", "founder@aquasense.demo.in", "Priya Nair", "startup",
         "AquaSense Technologies", None, "Founder & CEO"),
        ("U-EXP1", "r.kelkar@demo-expert.in", "Prof. R. Kelkar", "expert",
         "IIT Bombay (demo)", None, "Environmental Engineering"),
        ("U-EXP2", "s.patil@demo-expert.in", "Er. S. N. Patil", "expert",
         "MCGM Hydraulic Dept (demo)", None, "Chief Hydraulic Engineer"),
        ("U-EXP3", "a.joshi@demo-expert.in", "Dr. A. Joshi", "expert",
         "VJTI Mumbai (demo)", None, "Sensor Systems"),
        ("U-VAL1", "v.deshpande@demo-validator.in", "V. Deshpande", "validator",
         "Independent Water Audit Collective (demo)", None, "Lead Validator"),
        ("U-VAL2", "s.iyer@demo-validator.in", "S. Iyer", "validator",
         "Cert-In Empanelled Auditor (demo)", None, "Cybersecurity Validator"),
        ("U-ADMIN", "admin@demo.gov.in", "System Administrator", "administrator",
         "State Portal Services", None, "Platform Administrator"),
    ]
    for uid, email, name, role, org, dept, _title in users:
        db.add(User(id=uid, email=email, name=name, role=role, organization=org,
                    department_id=dept, password_hash=hash_password(DEMO_PASSWORD),
                    startup_id="ST-001" if role == "startup" else None))
    db.flush()

    # ---- startup registry ------------------------------------------------------
    for rec in _startup_records():
        db.add(Startup(is_demo=True, **rec))
    db.flush()

    # ---- the demo challenge -----------------------------------------------------
    ch = Challenge(
        id="CH-WTR-001", title="AI-Based Municipal Water Leakage Detection & Reduction",
        department="Municipal Water Department", problem_category="Water Management",
        problem_statement="Nashik Municipal Corporation loses an estimated 28–32% of treated water "
                          "to undetected pipeline leakage. Detection today depends on citizen "
                          "complaints and manual survey, taking 3–10 days per confirmed leak.",
        current_situation="Night-flow analysis is done manually on spreadsheet exports from 12 "
                          "district meters; there is no acoustic sensing on distribution mains.",
        affected_population="Approx. 4.6 lakh residents of Nashik city (demo figure)",
        existing_process="Complaint intake → manual valve operation survey → excavation trial",
        current_limitations="No continuous monitoring; high non-revenue water; slow localisation",
        expected_outcome="A monitored pilot achieving ≥20% leakage reduction across pilot zones "
                         "with instrumented evidence",
        geographic_scope="Nashik Municipal Corporation — 3 pilot zones (demo)",
        constraints="No disruption to supply during pilot; all data stays in Maharashtra SDC",
        priority="HIGH", status="PUBLISHED", budget_min=600000, budget_max=1200000,
        created_by="U-OFF1", published_at=days_ago(40),
        requirements={
            "functional": ["Real-time leakage alerting with site-level localisation",
                           "Night-flow analysis automated across pilot zones",
                           "Integration with existing district meter data"],
            "technical": ["REST APIs for district meter integration",
                          "Hosting on Maharashtra SDC with data residency in India",
                          "99.5% uptime with monitored incident response"],
            "security": ["Role-based access control and audit logs for all actions",
                         "TLS 1.2+ in transit, AES-256 at rest",
                         "Third-party security testing before scale"],
            "data": ["Government owns all pilot-generated data",
                     "Raw telemetry export in open formats at any time",
                     "Data residency within Indian jurisdictions"],
        },
        pilot_criteria={"duration_weeks": 12, "number_of_sites": 3, "target_users": "Water ops staff",
                        "budget_max": 1000000,
                        "success_conditions": "Validated ≥20% leakage reduction with instrumented "
                                              "evidence and completed cybersecurity review"},
        data_policy={"ownership": "Government of Maharashtra owns all pilot data",
                     "residency": "Maharashtra SDC (Pune)", "retention": "7 years"},
        ip_policy={"pre_existing": "Startup retains pre-existing IP",
                   "new_ip": "Department receives perpetual licence for pilot use"},
        cybersecurity={"authentication": "SSO + RBAC", "encryption": "TLS 1.2+ / AES-256",
                       "testing": "VAPT before scale", "audit_logging": "Immutable audit logs"},
        risks=[{"risk": "Sensor calibration drift", "probability": 3, "impact": 3},
               {"risk": "Field staff adoption", "probability": 2, "impact": 4}],
    )
    db.add(ch)
    db.add(Kpi(id="KPI-001", challenge_id="CH-WTR-001", name="Leakage Reduction",
               description="Reduction in non-revenue water across pilot zones",
               baseline="12%", target="20%", unit="%", direction="reduce",
               measurement_method="Smart meter flow comparison across pilot sites",
               evidence_source="Municipal water telemetry", success_threshold=">= 18%",
               source="OFFICER"))
    db.add(Kpi(id="KPI-002", challenge_id="CH-WTR-001", name="Leak Detection Time",
               description="Time from leak onset to field confirmation",
               baseline="72 hours", target="24 hours", unit="hours", direction="reduce",
               measurement_method="Timestamp difference between event and confirmation",
               evidence_source="Detection log with field confirmations", success_threshold="<= 36 hours",
               source="OFFICER"))
    db.add(Kpi(id="KPI-003", challenge_id="CH-WTR-001", name="System Uptime",
               description="Platform availability during pilot",
               baseline="N/A", target="95%", unit="%", direction="increase",
               measurement_method="Uptime monitoring probes",
               evidence_source="Platform telemetry", success_threshold=">= 92%",
               source="OFFICER"))

    # a second published challenge for discovery breadth
    db.add(Challenge(
        id="CH-AGR-001", title="Soil Health Monitoring for Smallholder Farms",
        department="Agriculture Department", problem_category="Agriculture",
        problem_statement="Soil testing turnaround is 3+ weeks; farmers over-apply fertiliser "
                          "without local data.",
        expected_outcome="Reduce fertiliser overuse by 15% with village-level soil analytics",
        geographic_scope="4 demo districts", priority="MEDIUM", status="PUBLISHED",
        budget_min=300000, budget_max=900000, created_by="U-OFF1", published_at=days_ago(20),
        requirements={"functional": ["Village-level soil health dashboards"],
                      "security": ["Role-based access control"]},
        pilot_criteria={"duration_weeks": 8, "budget_max": 700000},
        data_policy={"ownership": "Government owns pilot data"},
        cybersecurity={"authentication": "OTP login"},
    ))

    # ---- demo pilot 1: the RE-PILOT story --------------------------------------
    aqua = "ST-001"
    p1 = Pilot(id="P-WTR-001", name="Smart Leakage Detection Pilot", department="Municipal Water Department",
               challenge_id="CH-WTR-001", startup_id=aqua, startup_name="AquaSense Technologies",
               officer_id="U-OFF1", status="CONCLUDED", duration_weeks=12, budget=1000000,
               objectives="Reduce non-revenue water in 3 Nashik pilot zones via acoustic leakage detection",
               expected_outcome="≥20% validated leakage reduction across pilot zones",
               sites=3, target_users="Water operations field staff",
               geographic_scope="Nashik — Satpur, Ambad, Panchavati zones (demo)",
               success_criteria="Validated ≥20% leakage reduction with instrumented evidence",
               payment_conditions="Milestone-linked payments only after evidence acceptance (simulated)",
               baseline={"metric": "Non-revenue water", "value": "12%", "status": "VALIDATED",
                         "source": "District meter night-flow analysis",
                         "validated_at": days_ago(70).isoformat(), "sites_covered": 3},
               data_ip={"ownership": "Government owns all pilot data",
                        "usage_rights": "Perpetual licence for department use",
                        "residency": "Maharashtra SDC (Pune)"},
               cybersecurity={"checklist": {"sso_enabled": True, "encryption_at_rest": True,
                                            "vapt_completed": False, "audit_logs": True},
                              "review_completed": False},
               created_at=days_ago(75), updated_at=days_ago(3))
    db.add(p1)
    db.add(PaymentPlan(id="PAY-001", pilot_id="P-WTR-001", total_budget=1000000, validates_to_100=True))
    db.add_all([
        PilotKpi(id="PK-001", pilot_id="P-WTR-001", name="Leakage Reduction",
                 description="Reduction in non-revenue water", baseline="12%", target="20%", unit="%",
                 measurement_method="Smart meter flow comparison", evidence_source="Municipal water telemetry",
                 success_threshold=">= 18%", direction="reduce", status="TARGET_NOT_ACHIEVED",
                 claimed_value="21%", observed_value="19%",
                 progress_notes=[{"note": "Instrumented observation across 3 zones", "by": "V. Deshpande",
                                  "role": "validator", "at": days_ago(5).isoformat()}]),
        PilotKpi(id="PK-002", pilot_id="P-WTR-001", name="Leak Detection Time",
                 baseline="72 hours", target="24 hours", unit="hours",
                 measurement_method="Event-to-confirmation timestamps", evidence_source="Detection logs",
                 success_threshold="<= 36 hours", direction="reduce", status="TARGET_ACHIEVED",
                 claimed_value="18 hours", observed_value="22 hours"),
        PilotKpi(id="PK-003", pilot_id="P-WTR-001", name="System Uptime",
                 baseline="N/A", target="95%", unit="%", measurement_method="Uptime probes",
                 evidence_source="Platform telemetry", success_threshold=">= 92%",
                 direction="increase", status="TARGET_ACHIEVED", claimed_value="97.2%",
                 observed_value="96.4%"),
    ])
    db.add_all([
        Milestone(id="MS-001", pilot_id="P-WTR-001", name="Setup & Sensor Installation",
                  description="Install acoustic nodes across 3 zones", start_date="Week 1",
                  end_date="Week 2", deliverable="142 nodes live", kpi_dependency="System Uptime",
                  payment_percentage=25, status="ACCEPTED", payment_status="RELEASED",
                  accepted_at=days_ago(60)),
        Milestone(id="MS-002", pilot_id="P-WTR-001", name="Baseline Validation",
                  description="Night-flow baseline across pilot zones", start_date="Week 3",
                  end_date="Week 4", deliverable="Signed baseline report",
                  kpi_dependency="Leakage Reduction", payment_percentage=25,
                  status="ACCEPTED", payment_status="RELEASED", accepted_at=days_ago(55)),
        Milestone(id="MS-003", pilot_id="P-WTR-001", name="Live Detection Operations",
                  description="Operate detection for 8 weeks", start_date="Week 5",
                  end_date="Week 12", deliverable="Detection logs + field confirmations",
                  kpi_dependency="Leakage Reduction", payment_percentage=30,
                  status="ACCEPTED", payment_status="APPROVED", accepted_at=days_ago(12)),
        Milestone(id="MS-004", pilot_id="P-WTR-001", name="Cybersecurity Review Closure",
                  description="Close VAPT findings and certify review", start_date="Week 10",
                  end_date="Week 12", deliverable="Completed security review",
                  kpi_dependency="System Uptime", payment_percentage=20,
                  status="SUBMITTED", payment_status="NOT_ELIGIBLE"),
    ])

    # ---- demo pilot 2: the SCALE story ------------------------------------------
    p2 = Pilot(id="P-AGR-001", name="Village Soil Intelligence Pilot", department="Agriculture Department",
               challenge_id="CH-AGR-001", startup_id="ST-008", startup_name="SoilSarthi Data Labs",
               officer_id="U-OFF1", status="SCALED", duration_weeks=8, budget=700000,
               objectives="Reduce fertiliser overuse with village-level soil analytics",
               expected_outcome="≥15% fertiliser reduction with validated soil data",
               sites=6, target_users="Agriculture extension officers",
               geographic_scope="4 demo districts", success_criteria="Validated ≥15% input reduction",
               payment_conditions="Simulated milestone payments",
               baseline={"metric": "Fertiliser usage per hectare", "value": "52 kg/ha",
                         "status": "VALIDATED", "source": "Department input records",
                         "validated_at": days_ago(50).isoformat(), "sites_covered": 6},
               data_ip={"ownership": "Government owns pilot data",
                        "usage_rights": "Department licence"},
               cybersecurity={"checklist": {"sso_enabled": True, "encryption_at_rest": True,
                                            "vapt_completed": True, "audit_logs": True},
                              "review_completed": True},
               created_at=days_ago(55), updated_at=days_ago(2))
    db.add(p2)
    db.add(PaymentPlan(id="PAY-002", pilot_id="P-AGR-001", total_budget=700000, validates_to_100=True))
    db.add(PilotKpi(id="PK-101", pilot_id="P-AGR-001", name="Fertiliser Reduction",
                    baseline="52 kg/ha", target="15%", unit="%", measurement_method="Input records vs baseline",
                    evidence_source="Department input ledgers", success_threshold=">= 12%",
                    direction="reduce", status="TARGET_ACHIEVED", claimed_value="19%",
                    observed_value="17.6%"))
    db.add_all([
        Milestone(id="MS-101", pilot_id="P-AGR-001", name="Deployment", payment_percentage=40,
                  status="ACCEPTED", payment_status="RELEASED", accepted_at=days_ago(40)),
        Milestone(id="MS-102", pilot_id="P-AGR-001", name="Measured Operations",
                  payment_percentage=60, status="ACCEPTED", payment_status="RELEASED",
                  accepted_at=days_ago(15)),
    ])

    # ---- evidence + validation for pilot 1 (the claim → evidence → validation chain)
    ev = [
        Evidence(id="EV-001", pilot_id="P-WTR-001", kpi_id="PK-001", evidence_type="TELEMETRY",
                 title="Zone flow telemetry export — full pilot",
                 description="1.4M data points from district meters across 3 zones",
                 submitted_by="U-START1", submitted_by_name="Priya Nair",
                 submission_date=days_ago(14), file_name="zone_flow_telemetry.csv",
                 file_size=2411724, mime_type="text/csv",
                 sha256="9f82c41a7be3d51c88a2f7c6e0a4b9d1c3a4f2e1d0b8a796c5d4e3f2a1b0c9d8",
                 storage_path="(demo) object-store://evidence/9f82c41a",
                 version=1, status="VALIDATED", claimed_value="21%"),
        Evidence(id="EV-002", pilot_id="P-WTR-001", kpi_id="PK-001", evidence_type="REPORT",
                 title="Startup performance report — leakage reduction",
                 description="Startup analysis claiming 21% reduction", submitted_by="U-START1",
                 submitted_by_name="Priya Nair", submission_date=days_ago(13),
                 file_name="performance_report_q2.pdf", file_size=640512, mime_type="application/pdf",
                 sha256="a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
                 storage_path="(demo) object-store://evidence/a1b2c3d4",
                 version=1, status="VALIDATED", claimed_value="21%"),
        Evidence(id="EV-003", pilot_id="P-WTR-001", kpi_id="PK-002", evidence_type="LOG",
                 title="Detection event logs with field confirmations",
                 description="Event timestamps and field crew confirmations",
                 submitted_by="U-START1", submitted_by_name="Priya Nair",
                 submission_date=days_ago(12), file_name="detection_events.json", file_size=182044,
                 mime_type="application/json",
                 sha256="b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2",
                 storage_path="(demo) object-store://evidence/b2c3d4e5",
                 version=1, status="VALIDATED", claimed_value="18 hours"),
        Evidence(id="EV-004", pilot_id="P-WTR-001", kpi_id=None, evidence_type="CERTIFICATE",
                 title="VAPT report — interim",
                 description="Interim security assessment; two findings open",
                 submitted_by="U-START1", submitted_by_name="Priya Nair",
                 submission_date=days_ago(10), file_name="vapt_interim.pdf", file_size=482100,
                 mime_type="application/pdf",
                 sha256="c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3",
                 storage_path="(demo) object-store://evidence/c3d4e5f6",
                 version=1, status="ACCEPTED_FOR_MONITORING", claimed_value=""),
    ]
    db.add_all(ev)

    pkg = ValidationPackage(id="VP-001", pilot_id="P-WTR-001", status="REPORT_SUBMITTED",
                            evidence_ids=["EV-001", "EV-002", "EV-003"],
                            created_at=days_ago(9))
    db.add(pkg)
    db.add(ValidatorAssignment(id="VA-001", package_id="VP-001", validator_id="U-VAL1",
                               validator_name="V. Deshpande", coi_status="NO_CONFLICT",
                               status="SUBMITTED", assigned_at=days_ago(9)))
    db.add(CoiDeclaration(id="COI-VAL-001", assignment_id="VA-001", expert_id="U-VAL1",
                          status="NO_CONFLICT", declared_at=days_ago(9)))
    db.add_all([
        ValidationFinding(id="VF-001", package_id="VP-001", kpi_id="PK-001",
                          claimed="21%", observed="19%", validated_value="18%",
                          target="≥ 18% threshold / 20% target", finding="PARTIALLY_SUPPORTED",
                          explanation="Validated reduction is 18% across instrumented zones — "
                                      "supports a real reduction but below the 20% target and the "
                                      "21% claim. Described factually; no allegation implied.",
                          evidence_ids=["EV-001", "EV-002"]),
        ValidationFinding(id="VF-002", package_id="VP-001", kpi_id="PK-002",
                          claimed="18 hours", observed="22 hours", validated_value="22 hours",
                          target="≤ 36 hours", finding="SUPPORTED",
                          explanation="Detection time comfortably within threshold.",
                          evidence_ids=["EV-003"]),
    ])
    db.add(ValidationReport(id="VR-001", package_id="VP-001", pilot_id="P-WTR-001",
                            validator_id="U-VAL1",
                            summary="Independent analysis of instrumented telemetry supports a real "
                                    "reduction, validated at 18% — below the 20% target and the 21% "
                                    "startup claim. Cybersecurity review remains open.",
                            overall_finding="PARTIALLY_SUPPORTED",
                            validated_kpis={"Leakage Reduction": "18%", "Leak Detection Time": "22 hours"},
                            report_version=1,
                            sha256="d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4",
                            created_at=days_ago(6)))
    db.add(DecisionRecommendation(
        id="DR-001", pilot_id="P-WTR-001", outcome="RE_PILOT", confidence=0.78,
        reasons=["Leakage reduction validated at 18% — near but below the ≥18% success threshold and 20% target",
                 "Cybersecurity review pending; required before any scale decision",
                 "Baseline covered only 3 sites, limiting decision confidence"],
        supporting_evidence=["Leak Detection Time validated at 22 hours (threshold ≤36)",
                             "System uptime validated at 96.4%"],
        missing_evidence=["Completed cybersecurity review", "Wider-site baseline data coverage"],
        risk_flags=["Claim/observation gap on Leakage Reduction: claimed 21% vs observed 19% "
                    "(described objectively; verification, not allegation)"],
        factor_scores={"kpi_performance": 50, "evidence_confidence": 75, "validation_confidence": 65,
                       "impact": 50, "feasibility": 75, "readiness": 90, "cost_effectiveness": 75,
                       "scalability": 80, "cybersecurity": 30, "data_quality": 85, "risk": 65,
                       "sustainability": 60},
        engine_version="decision-engine@1.4", created_at=days_ago(5)))
    db.add(GovernmentDecision(id="GD-001", pilot_id="P-WTR-001", recommendation_id="DR-001",
                               ai_outcome="RE_PILOT", decision="RE_PILOT", decision_type="ALIGNED",
                               reason="Direction is promising and two of three KPIs validated, but the "
                                      "headline KPI sits below threshold and the baseline covers only "
                                      "3 sites. Expand to 10 sites, improve baseline/data coverage, "
                                      "and complete the cybersecurity review before reconsidering.",
                               decided_by="U-SEN1", decided_by_name="Meera Deshmukh",
                               decided_at=days_ago(4)))
    db.add_all([
        KnowledgeLesson(id="KL-001", pilot_id="P-WTR-001", title="Baseline quality limits decision confidence",
                        lesson="Baseline dataset covered only 3 sites, so zone-level variance could not "
                               "be separated from the measured improvement.",
                        evidence="Pilot P-WTR-001 baseline record: 3 sites, validated.",
                        recommendation="Expand baseline data collection across more sites before the "
                                       "next pilot or scale decision.",
                        sector="Municipal Water Department", problem_type="Leakage detection",
                        technology="Acoustic IoT", tags=["baseline", "data-coverage"],
                        status="ACCEPTED", decided_by="Arjun Kulkarni", created_at=days_ago(3)),
        KnowledgeLesson(id="KL-002", pilot_id="P-WTR-001", title="Claim calibration gap on Leakage Reduction",
                        lesson="Startup claimed 21% while field observation measured 19% and independent "
                               "validation confirmed 18%. Future KPIs should define measurement methods "
                               "precisely and set expectations for claim variance.",
                        evidence="Pilot KPI record PK-001; validation finding VF-001.",
                        recommendation="Require instrumented measurement and pre-agreed data formats in "
                                       "pilot agreements.",
                        sector="Municipal Water Department", problem_type="Leakage detection",
                        technology="Acoustic IoT", tags=["claim-vs-observed", "kpi-definition"],
                        status="PENDING", created_at=days_ago(3)),
    ])

    # ---- pre-staged follow-on branches ------------------------------------------
    # RE-PILOT branch: plan created from the recorded government decision.
    db.add(RepilotPlan(
        id="RP-DEMO-001", pilot_id="P-WTR-001", decision_id="GD-001", status="PLANNED",
        carried_forward={
            "previous_kpi_results": [
                {"name": "Leakage Reduction", "target": "20%", "claimed": "21%",
                 "observed": "19%", "status": "TARGET_NOT_ACHIEVED"},
                {"name": "Leak Detection Time", "target": "24 hours", "claimed": "18 hours",
                 "observed": "22 hours", "status": "TARGET_ACHIEVED"},
                {"name": "System Uptime", "target": "95%", "claimed": "97.2%",
                 "observed": "96.4%", "status": "TARGET_ACHIEVED"}],
            "lessons": [{"title": "Baseline quality limits decision confidence",
                         "lesson": "Baseline dataset covered only 3 sites."}],
            "evidence_gaps": ["Completed cybersecurity review", "Wider-site baseline data coverage"],
            "validation_risk_flags": ["Claim/observation gap on Leakage Reduction"],
            "previous_scope": {"sites": 3, "budget": 1000000, "duration_weeks": 12}},
        scope_changes={"sites": {"from": 3, "to": 10, "reason": "Expand baseline/data coverage"},
                       "duration_weeks": {"from": 12, "to": 12,
                                          "reason": "Same controlled duration for comparability"},
                       "budget": {"from": 1000000, "to": 1600000,
                                  "reason": "Expanded site coverage and instrumentation"}},
        required_changes=["Expand from 3 sites to 10 sites",
                          "Improve baseline/data coverage",
                          "Complete cybersecurity review"],
        created_at=days_ago(4)))

    # SCALE branch: soil pilot approved for scale with a procurement package.
    db.add(ScaleUpPlan(
        id="SU-DEMO-001", pilot_id="P-AGR-001", decision_id=None, status="APPROVED",
        pilot_scope={"sites": 6, "users": "Agriculture extension officers", "budget": 700000,
                     "duration_weeks": 8, "geographic_scope": "4 demo districts"},
        scale_scope={"sites": 30, "users": "District-wide rollout", "budget": 4200000,
                     "infrastructure": "Redundant hosting at Maharashtra SDC",
                     "geographic_scope": "State-wide (phased by district)"},
        new_kpis=["Scale-phase uptime ≥ 99.5%", "Cost per site within sanctioned budget"],
        operational_risks=["Hardware supply chain at scale", "Field-staff adoption"],
        cybersecurity_plan={"review": "Full re-assessment for expanded footprint",
                            "certification": "CERT-In audit before district rollout"},
        support_requirements=["Program management office", "Training program", "24×7 helpdesk"],
        reviewed_by="U-SEN1", reviewed_at=days_ago(1), created_at=days_ago(2)))
    db.add(ProcurementPackage(
        id="PP-DEMO-001", scaleup_id="SU-DEMO-001", pilot_id="P-AGR-001",
        status="DRAFT_NOT_LEGALLY_BINDING",
        content={
            "requirements_summary": {"functional": ["Village-level soil health dashboards"]},
            "validated_kpis": [{"name": "Fertiliser Reduction", "target": "15%",
                                "validated": "17.6%", "threshold": ">= 12%"}],
            "pilot_evidence_summary": {"budget": 700000, "duration_weeks": 8, "sites": 6,
                                       "validation": "SUPPORTED"},
            "validation_findings": {"Fertiliser Reduction": "17.6%"},
            "risks": ["Hardware supply chain at scale", "Field-staff adoption"],
            "cybersecurity_requirements": {"review": "Full re-assessment",
                                           "certification": "CERT-In audit"},
            "implementation_scope": {"sites": 30, "budget": 4200000},
            "lessons_learned": []},
        generated_by="U-OFF1", generated_at=days_ago(1)))

    # ---- knowledge corpus (historical demo pilots for similarity) ----------------
    corpus = [
        ("Amravati NRW Analytics", "Municipal Water Department", "Water Management",
         "non-revenue water analytics", "Metering IoT", "leakage reduction", "6 sites",
         "HIGH", "SCALE", "2024", "Meter-data analytics pilot validated at 21% reduction; scaled."),
        ("PCMC Acoustic Trial", "Municipal Water Department", "Water Management",
         "acoustic leak detection", "Acoustic IoT", "leakage reduction", "4 sites",
         "MEDIUM", "RE_PILOT", "2023", "Acoustic sensors showed promise but baseline coverage was thin."),
        ("Pune Soil Mapping", "Agriculture Department", "Agriculture",
         "village soil analytics", "Remote Sensing", "input reduction", "12 villages",
         "HIGH", "SCALE", "2024", "Soil mapping reduced fertiliser overuse across 12 villages."),
        ("Nagpur Streetlight Retrofit", "Urban Development Department", "Energy",
         "streetlight energy reduction", "Smart Controls", "energy reduction", "9 wards",
         "HIGH", "SCALE", "2023", "Streetlight controls cut energy use 24% and scaled city-wide."),
        ("Kalyan Grievance Triage", "Urban Development Department", "GovTech",
         "grievance triage automation", "NLP", "response time", "city-wide",
         "MEDIUM", "REJECT", "2024", "NLP triage did not beat manual routing in controlled testing."),
    ]
    for i, (name, dept, sector, ptype, tech, kpi, size, quality, outcome, year, summary) in enumerate(corpus):
        db.add(SimilarPilot(id=f"SP-{i + 1:02d}", name=name + " (demo)", department=dept,
                            sector=sector, problem_type=ptype, technology=tech, kpi_focus=kpi,
                            pilot_size=size, evidence_quality=quality, outcome=outcome,
                            year=year, summary=summary))

    # ---- a few expert assignments + evaluations for demo richness ----------------
    # The demo story walks Government Officer -> Expert Evaluator -> Government Officer.
    # One authoritative evaluator (Prof. R. Kelkar, U-EXP1) holds one open assignment for
    # AquaSense on the water challenge, sitting at AWAITING_COI. This is what makes the
    # specialist workspace show real work when the role is switched to evaluator.
    # Remove any pre-existing demo records so re-running the seed does not duplicate.
    # AquaSense's application on the water challenge. In production this row is
    # created by the matching engine when an officer runs matching; the demo seed
    # materializes the engine's result directly so the Startup persona sees the
    # application from day one (same shared record, not a copy).
    db.query(StartupMatch).filter_by(challenge_id="CH-WTR-001", startup_id=aqua).delete()
    db.add(StartupMatch(
        id="M-001", challenge_id="CH-WTR-001", startup_id=aqua,
        match_score=84, component_scores={"problemFit": 92, "technologyFit": 88, "experience": 85,
                                          "evidence": 78, "eligibility": 100, "scalability": 82,
                                          "risk": 85},
        explanations={"why_matched": ["Problem-area overlap on: leakage, water, metering",
                                      "Technology relevance: acoustic sensing, IoT telemetry",
                                      "2 prior pilot(s) in a related domain"],
                      "limitations": ["No independently verified pilot outcome on record"],
                      "note": "Demo materialization of the matching engine's result."},
        evidence_confidence="MEDIUM", eligibility_status="ELIGIBLE", rank=1,
        run_version="matching-engine@1.3 (demo)"))

    db.query(ExpertAssignment).filter_by(challenge_id="CH-WTR-001", startup_id=aqua,
                                         expert_id="U-EXP1").delete()
    db.query(CoiDeclaration).filter_by(assignment_id="ASG-001", expert_id="U-EXP1").delete()
    db.query(Evaluation).filter_by(assignment_id="ASG-001", expert_id="U-EXP1").delete()
    db.query(EvaluationAggregate).filter_by(challenge_id="CH-WTR-001", startup_id=aqua).delete()
    aqua = "ST-001"
    asg = ExpertAssignment(
        id="ASG-001", challenge_id="CH-WTR-001", startup_id=aqua,
        expert_id="U-EXP1", status="AWAITING_COI", assigned_at=days_ago(30)
    )
    db.add(asg)
    db.add(CoiDeclaration(
        id="COI-001", assignment_id="ASG-001", expert_id="U-EXP1",
        status="NO_CONFLICT", declared_at=days_ago(29)
    ))
    kelkar_scores = {
        "problem_fit": {"score": 9, "justification": "Directly addresses municipal leakage detection."},
        "technical_feasibility": {"score": 8, "justification": "Acoustic sensing is proven and low-risk."},
        "relevant_experience": {"score": 8, "justification": "Two municipal pilots in the same domain."},
        "evidence_quality": {"score": 8, "justification": "Independently verified telemetry is available."},
        "pilot_readiness": {"score": 8, "justification": "Hardware is installed and ready."},
        "scalability": {"score": 8, "justification": "Per-node cost falls with scale."},
        "value_for_money": {"score": 8, "justification": "Mid-range pilot pricing."},
        "risk_compliance": {"score": 8, "justification": "Cybersecurity review is the only open item."},
    }
    kelkar_total = round(sum(scores["score"] * w["weight"] for scores, w in zip(
        kelkar_scores.values(), CRITERIA_WEIGHTS)) / 100, 1)
    db.add(Evaluation(
        id="EVAL-001", assignment_id="ASG-001", challenge_id="CH-WTR-001",
        startup_id=aqua, expert_id="U-EXP1", version=1, scores=kelkar_scores,
        weighted_total=kelkar_total,
        recommendation="RECOMMEND_FOR_PILOT",
        final_comments=(
            "The solution is relevant to municipal leakage detection and suitable for controlled "
            "pilot testing. Additional evidence is required before wider deployment."
        ),
        created_at=days_ago(28)
    ))
    db.add(EvaluationAggregate(
        id="AGG-001", challenge_id="CH-WTR-001", startup_id=aqua,
        evaluation_count=1, average=kelkar_total, median=kelkar_total,
        minimum=kelkar_total, maximum=kelkar_total, stddev=0.0,
        criterion_disagreement={}, disagreement_flag=False,
        recommendation="RECOMMENDED_FOR_PILOT"
    ))

    db.commit()

    # Workflow reseed drops all tables — re-import the government public-data
    # snapshots so ecosystem intelligence survives a demo reset.
    try:
        from app.services.govdata import ensure_govdata_seeded
        ensure_govdata_seeded(db)
    except Exception:  # pragma: no cover
        pass

    return {"seeded": True, "users": len(users), "startups": len(_STARTUP_NAMES),
            "challenges": 2, "pilots": 2, "evidence": len(ev), "repilot_plans": 1,
            "scaleup_plans": 1, "procurement_packages": 1,
            "demo_password": DEMO_PASSWORD,
            "notice": "All seeded records are fictional demo data. UI must display DEMO DATA."}


CRITERIA_WEIGHTS = [
    {"key": "problem_fit", "label": "Problem Fit", "weight": 20},
    {"key": "technical_feasibility", "label": "Technical Feasibility", "weight": 15},
    {"key": "relevant_experience", "label": "Relevant Experience", "weight": 15},
    {"key": "evidence_quality", "label": "Evidence Quality", "weight": 15},
    {"key": "pilot_readiness", "label": "Pilot Readiness", "weight": 10},
    {"key": "scalability", "label": "Scalability", "weight": 10},
    {"key": "value_for_money", "label": "Value for Money", "weight": 5},
    {"key": "risk_compliance", "label": "Risk & Compliance", "weight": 10},
]

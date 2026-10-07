"""AIRequirementEngine — rule-based, explainable requirement generation.

Deterministic keyword/rules engine. Clean interface so an LLM service can be
substituted later (see ARCHITECTURE.md). Confidence values are heuristic, never
claimed as model accuracy. Nothing generated here becomes official until an
officer explicitly accepts it.
"""

CATEGORY_RULES = {
    "Water Management": ["water", "leakage", "pipeline", "drainage", "sewage", "supply", "meter", "borewell", "irrigation"],
    "Healthcare": ["health", "patient", "hospital", "clinic", "medicine", "diagnosis", "tb", "vaccination", "phc"],
    "Agriculture": ["crop", "farmer", "soil", "agriculture", "harvest", "mandi", "irrigation", "fertilizer", "pest"],
    "Urban Mobility": ["traffic", "transport", "bus", "parking", "mobility", "road", "commute", "pothole"],
    "Education": ["school", "student", "teacher", "education", "learning", "attendance", "classroom"],
    "Energy": ["energy", "power", "electricity", "streetlight", "solar", "grid", "transformer", "outage"],
    "Waste Management": ["waste", "garbage", "segregation", "landfill", "recycling", "sanitation"],
    "Public Safety": ["safety", "emergency", "disaster", "flood", "fire", "surveillance", "complaint"],
    "General Governance": [],
}

REQUIREMENT_TEMPLATES = {
    "functional": [
        ("Real-time monitoring dashboard for field deployments with site-level drill-down", "system capability"),
        ("Automated data capture from field devices with offline-first sync", "operational requirement"),
        ("Configurable alerting workflow with escalation to department officers", "workflow requirement"),
        ("Role-based workflows for field staff, supervisors and administrators", "workflow requirement"),
        ("REST API integration with the department's existing systems", "integration requirement"),
    ],
    "technical": [
        ("Interoperability via documented, versioned open REST APIs (JSON over HTTPS)", "interoperability"),
        ("Hostable on/compatible with Maharashtra SDC or MeitY-empanelled cloud with data residency in India", "infrastructure"),
        ("Support at least {sites} concurrent sites and {users} users with <3s page interactions", "performance"),
        ("99.5% monthly uptime SLA with monitored incident response", "reliability"),
        ("Mobile-responsive PWA or Android app for field operations", "infrastructure"),
    ],
    "security": [
        ("Authentication with OTP/SSO integration and role-based access control", "access control"),
        ("TLS 1.2+ in transit and AES-256 at rest for all collected data", "encryption"),
        ("Immutable audit logs for all administrative and data-access actions", "audit logs"),
        ("Annual/third-party security testing (VAPT) with findings remediated before scale", "cybersecurity compliance"),
        ("Principle-of-least-privilege access with quarterly access reviews", "access control"),
    ],
    "data": [
        ("Government owns all department and citizen data generated during the pilot", "data ownership"),
        ("Raw data export in open formats (CSV/JSON) available to the department at any time", "data access"),
        ("Data retention for a minimum of 7 years post-pilot, then certified deletion on request", "data retention"),
        ("Personal data processed per DPDP Act 2023 with minimisation and consent where applicable", "data privacy"),
        ("Data stored only within Indian jurisdictions (data residency)", "data residency"),
    ],
}

KPI_TEMPLATES = {
    "Water Management": [
        {"name": "Leakage Reduction", "baseline": "12%", "target": "20%", "unit": "%", "direction": "reduce",
         "measurement_method": "Smart meter flow comparison across pilot sites", "evidence_source": "Municipal water telemetry",
         "success_threshold": ">= 18%", "rationale": "Directly measures the operational loss the challenge describes.",
         "confidence": 0.9},
        {"name": "Leak Detection Time", "baseline": "72 hours", "target": "24 hours", "unit": "hours", "direction": "reduce",
         "measurement_method": "Timestamp difference between event occurrence and field confirmation",
         "evidence_source": "Detection log with field confirmation records", "success_threshold": "<= 36 hours",
         "rationale": "Captures the responsiveness benefit beyond raw loss reduction.", "confidence": 0.75},
    ],
    "default": [
        {"name": "Service Delivery Time Reduction", "baseline": "Define at baseline validation", "target": "30%", "unit": "%",
         "direction": "reduce", "measurement_method": "Process timestamp analysis", "evidence_source": "Department process logs",
         "success_threshold": ">= 25%", "rationale": "Generic efficiency outcome; officer must localise it.",
         "confidence": 0.5},
        {"name": "System Adoption Rate", "baseline": "0%", "target": "70%", "unit": "%", "direction": "increase",
         "measurement_method": "Active usage analytics", "evidence_source": "Application telemetry",
         "success_threshold": ">= 60%", "rationale": "Technology fails without adoption; measurable from system logs.",
         "confidence": 0.6},
    ],
}


class AIRequirementEngine:
    """Deterministic, explainable requirement suggestion engine."""

    VERSION = "requirements-engine@1.2"

    def detect_category(self, text: str) -> tuple[str, float]:
        lower = (text or "").lower()
        best, best_hits = "General Governance", 0
        for category, keywords in CATEGORY_RULES.items():
            hits = sum(1 for k in keywords if k in lower)
            if hits > best_hits:
                best, best_hits = category, hits
        confidence = min(0.9, 0.45 + best_hits * 0.1) if best_hits else 0.35
        return best, round(confidence, 2)

    def generate(self, problem: dict) -> dict:
        """problem: {problem_statement, current_situation, expected_outcome, constraints,
                     department, sites, users}. Returns suggestions (status PENDING)."""
        blob = " ".join(str(problem.get(k, "")) for k in
                        ("problem_statement", "current_situation", "expected_outcome", "constraints", "department"))
        category, cat_conf = self.detect_category(blob)
        sites = problem.get("sites") or "the defined pilot"
        users = problem.get("users") or "the defined user group"

        suggestions: list[dict] = []
        for req_type, templates in REQUIREMENT_TEMPLATES.items():
            for text, tag in templates:
                suggestions.append({
                    "suggestion_type": "requirement",
                    "category": req_type,
                    "text": text.format(sites=sites, users=users),
                    "rationale": f"Standard {req_type} expectation for {category.lower()} deployments ({tag}).",
                    "confidence": 0.72 if req_type in ("security", "data") else 0.65,
                })

        kpis = KPI_TEMPLATES.get(category, KPI_TEMPLATES["default"])
        for kpi in kpis[:3]:
            suggestions.append({
                "suggestion_type": "kpi",
                "category": "kpi",
                "text": kpi["name"],
                "rationale": kpi["rationale"],
                "confidence": kpi["confidence"],
                "extra": {k: v for k, v in kpi.items() if k not in ("name", "rationale", "confidence")},
            })

        return {
            "category": category,
            "category_confidence": cat_conf,
            "suggestions": suggestions,
            "engine_version": self.VERSION,
            "notice": "Rule-based suggestions. An officer must accept, edit or reject each one; "
                      "nothing is automatically added to the official requirement set.",
        }


def get_requirements_engine() -> AIRequirementEngine:
    return AIRequirementEngine()

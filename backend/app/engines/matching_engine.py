"""MatchingEngine — explainable weighted matching.

Weights are mandated by the product spec. Match Score (suitability) is kept
strictly separate from Evidence Confidence (how well claims are supported).
"""
WEIGHTS = {
    "problemFit": 25,
    "technologyFit": 20,
    "experience": 15,
    "evidence": 15,
    "eligibility": 10,
    "scalability": 10,
    "risk": 5,
}


def _text(blob: str) -> set[str]:
    stop = {"the", "and", "for", "with", "of", "in", "to", "a", "an", "on", "at", "is", "are"}
    return {w for w in "".join(c if c.isalnum() else " " for c in blob.lower()).split() if w not in stop and len(w) > 3}


def _kw_overlap(a: list[str], b: list[str]) -> set[str]:
    """Keyword overlap that also handles multi-word keys (e.g. 'water management')."""
    aw, bw = set(), set()
    for phrase in a + b:
        aw.update(_text(phrase))
    for phrase in b:
        bw.update(_text(phrase))
    return aw & bw


def evidence_confidence(startup: dict) -> str:
    """HIGH only when a prior pilot was independently verified. Integrity ≠ truth."""
    pilots = startup.get("previous_pilots") or []
    verified = [p for p in pilots if str(p.get("verified", "")).lower() in ("true", "yes", "verified", "independently validated")]
    if verified:
        return "HIGH"
    if pilots or (startup.get("evidence_summary") or {}).get("submissions"):
        return "MEDIUM"
    return "LOW"


def eligibility_status(startup: dict) -> str:
    el = startup.get("eligibility") or {}
    if el.get("dpiit_registered") and el.get("certifications") and el.get("financial_compliance"):
        return "ELIGIBLE"
    if el.get("dpiit_registered") or (el.get("certifications") or el.get("financial_compliance")):
        return "PARTIALLY_ELIGIBLE"
    if any(v for v in el.values()):
        return "INCOMPLETE"
    return "NOT_ELIGIBLE"


class MatchingEngine:
    VERSION = "matching-engine@1.3"

    def score_startup(self, startup: dict, challenge: dict) -> dict:
        # ---- component scores (0-100), each explainable --------------------------
        chal_words = _text(" ".join([challenge.get("title", ""), challenge.get("problem_statement", ""),
                                     challenge.get("problem_category", ""), challenge.get("expected_outcome", ""),
                                     challenge.get("department", "")]))
        sector_words = _text(startup.get("sector", "") + " " + " ".join(startup.get("problem_areas") or []))
        overlap = chal_words & sector_words
        problem_fit = min(100, 40 + 12 * len(overlap)) if overlap else 25

        tech_words = _text(" ".join(startup.get("technology") or []))
        tech_overlap = chal_words & tech_words
        technology_fit = min(100, 45 + 14 * len(tech_overlap)) if tech_overlap else 30

        pilots = startup.get("previous_pilots") or []
        relevant = [p for p in pilots
                    if _text(str(p.get("name", "")) + " " + str(p.get("sector", ""))) & (chal_words | sector_words)]
        experience = min(100, 25 + 15 * len(relevant) + 5 * min(startup.get("experience_years", 0), 8))

        verified = [p for p in pilots if str(p.get("verified", "")).lower() in ("true", "yes", "verified")]
        evidence = min(100, 35 + 30 * len(verified) + 10 * min(len(pilots), 3))

        el = startup.get("eligibility") or {}
        checks = sum(1 for k in ("dpiit_registered", "certifications", "financial_compliance") if el.get(k))
        eligibility = {3: 100, 2: 80, 1: 55, 0: 20}[checks]

        sc = startup.get("scalability") or {}
        scalability = min(100, 40 + int(sc.get("score", 40)) * 0.5 + (15 if sc.get("multi_city") else 0))

        risk = startup.get("risk_profile") or {}
        risk_score = {"LOW": 90, "MEDIUM": 65, "HIGH": 35}.get(str(risk.get("overall", "MEDIUM")).upper(), 50)

        components = {
            "problemFit": round(problem_fit),
            "technologyFit": round(technology_fit),
            "experience": round(experience),
            "evidence": round(evidence),
            "eligibility": round(eligibility),
            "scalability": round(scalability),
            "risk": round(risk_score),
        }
        total = round(sum(components[k] * WEIGHTS[k] for k in WEIGHTS) / 100)

        # ---- explanations --------------------------------------------------------
        reasons, limitations = [], []
        if overlap:
            reasons.append(f"Problem-area overlap on: {', '.join(sorted(overlap)[:5])}")
        if tech_overlap:
            reasons.append(f"Technology relevance: {', '.join(sorted(tech_overlap)[:4])}")
        if relevant:
            reasons.append(f"{len(relevant)} prior pilot(s) in a related domain")
        if verified:
            reasons.append(f"{len(verified)} pilot outcome(s) independently verified")
        if not overlap:
            limitations.append("Weak problem-area overlap with this challenge")
        if not verified:
            limitations.append("No independently verified pilot outcome on record")
        el_status = eligibility_status(startup)
        if el_status != "ELIGIBLE":
            limitations.append(f"Eligibility status is {el_status.replace('_', ' ').title()}")

        return {
            "match_score": total,
            "component_scores": components,
            "weights": WEIGHTS,
            "evidence_confidence": evidence_confidence(startup),
            "eligibility_status": el_status,
            "explanations": {
                "why_matched": reasons or ["General capability alignment; no strong domain overlap detected"],
                "limitations": limitations or ["No significant limitations identified from registry data"],
                "note": "Match Score measures suitability, not proof of performance. "
                        "Evidence Confidence separately reflects how strongly past claims were supported.",
            },
            "engine_version": self.VERSION,
        }


def get_matching_engine() -> MatchingEngine:
    return MatchingEngine()

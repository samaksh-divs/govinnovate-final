"""DecisionEngine — explainable recommendation with hard abstention.

Rules:
- Scale requires the validated KPI to clear the success threshold AND
  independent validation to SUPPORT the outcome AND cybersecurity review done.
- If required evidence/validation is missing, the engine MUST abstain with
  INSUFFICIENT_EVIDENCE rather than invent a conclusion.
- Output is a recommendation only. It never becomes a government decision
  without an explicit human action recorded separately.
"""
from statistics import mean

ENGINE_VERSION = "decision-engine@1.4"

FACTOR_LABELS = {
    "kpi_performance": "KPI performance vs threshold",
    "evidence_confidence": "Evidence confidence",
    "validation_confidence": "Independent validation confidence",
    "impact": "Impact (validated delta vs target)",
    "feasibility": "Feasibility (milestone delivery)",
    "readiness": "Operational readiness",
    "cost_effectiveness": "Cost effectiveness",
    "scalability": "Scalability signals",
    "cybersecurity": "Cybersecurity review",
    "data_quality": "Data quality / coverage",
    "risk": "Risk posture",
    "sustainability": "Sustainability of outcome",
}


def _num(value):
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _threshold_value(threshold: str):
    if not threshold:
        return None
    digits = "".join(ch for ch in threshold if (ch.isdigit() or ch == "."))
    try:
        return float(digits)
    except ValueError:
        return None


def _kpi_achieved(kpi: dict) -> bool | None:
    """Compare observed value to success threshold respecting KPI direction."""
    observed, threshold = _num(kpi.get("observed_value")), _threshold_value(kpi.get("success_threshold") or kpi.get("target"))
    if observed is None or threshold is None:
        return None
    return observed >= threshold if kpi.get("direction") == "increase" else observed <= threshold


def evaluate(pilot: dict, pilot_kpis: list[dict], validation: dict | None,
             milestones: list[dict], evidence: list[dict]) -> dict:
    """Produce an explainable recommendation. Abstains when evidence is insufficient."""
    reasons: list[str] = []
    supporting: list[str] = []
    missing: list[str] = []
    risk_flags: list[str] = []

    validated_kpis = (validation or {}).get("validated_kpis") or {}
    overall_finding = (validation or {}).get("overall_finding", "")

    # ---------- factor scores --------------------------------------------------
    achieved = [k for k in pilot_kpis if _kpi_achieved(k) is True]
    not_achieved = [k for k in pilot_kpis if _kpi_achieved(k) is False]
    unknown = [k for k in pilot_kpis if _kpi_achieved(k) is None]
    kpi_score = 100 * len(achieved) / len(pilot_kpis) if pilot_kpis else 0

    if achieved:
        supporting.append("Success threshold cleared for: " + ", ".join(k["name"] for k in achieved))
    if not_achieved:
        risk_flags.append("Success threshold not cleared for: " + ", ".join(k["name"] for k in not_achieved))
    if unknown:
        missing.append("Measurable observed value missing for: " + ", ".join(k["name"] for k in unknown))

    high_conf_evidence = [e for e in evidence if e.get("status") in ("VALIDATED", "PARTIALLY_VALIDATED", "READY_FOR_VALIDATION")]
    evidence_score = 100 * len(high_conf_evidence) / len(evidence) if evidence else 0
    if not evidence:
        missing.append("No pilot evidence submitted at all")

    validation_score = {"SUPPORTED": 90, "PARTIALLY_SUPPORTED": 65, "NOT_SUPPORTED": 15,
                        "INSUFFICIENT_EVIDENCE": 10, "CONTRADICTORY_EVIDENCE": 10,
                        "UNVERIFIABLE": 20}.get(overall_finding, 0)
    if not validation:
        missing.append("Independent validation not completed")
    elif overall_finding == "SUPPORTED":
        supporting.append(f"Independent validation supports the outcome ({len(validated_kpis)} KPI(s) validated)")
    elif overall_finding in ("NOT_SUPPORTED", "CONTRADICTORY_EVIDENCE"):
        risk_flags.append("Independent validation did not support the claimed outcome")

    accepted = [m for m in milestones if m.get("status") == "ACCEPTED"]
    milestone_ratio = len(accepted) / len(milestones) if milestones else 0
    feasibility_score = round(milestone_ratio * 100)
    if milestones and milestone_ratio < 0.8:
        missing.append(f"Only {len(accepted)}/{len(milestones)} milestones accepted")

    sec = pilot.get("cybersecurity") or {}
    sec_reviewed = sec.get("review_completed") is True
    cybersecurity_score = 90 if sec_reviewed else 30
    if not sec_reviewed:
        missing.append("Cybersecurity review not completed")

    baseline_ok = (pilot.get("baseline") or {}).get("status") == "VALIDATED"
    data_quality_score = 85 if baseline_ok else 40
    if not baseline_ok:
        missing.append("Baseline not validated by the department")

    claims_gaps = []
    for k in pilot_kpis:
        claimed, observed = _num(k.get("claimed_value")), _num(k.get("observed_value"))
        if claimed is not None and observed is not None and abs(claimed - observed) > 3:
            claims_gaps.append(f"{k['name']}: claimed {k.get('claimed_value')} vs observed {k.get('observed_value')}")
    if claims_gaps:
        risk_flags.append("Claim/observation gaps on " + ", ".join(claims_gaps) +
                          " (described objectively; verification, not allegation)")

    factor_scores = {
        "kpi_performance": round(kpi_score),
        "evidence_confidence": round(evidence_score),
        "validation_confidence": round(validation_score),
        "impact": round(kpi_score),
        "feasibility": feasibility_score,
        "readiness": 90 if pilot.get("status") in ("CONCLUDED", "DECIDED", "SCALED") else 60,
        "cost_effectiveness": 75,
        "scalability": 80 if (pilot.get("sites") or 0) >= 3 else 55,
        "cybersecurity": cybersecurity_score,
        "data_quality": data_quality_score,
        "risk": 85 - 20 * len(risk_flags) if risk_flags else 85,
        "sustainability": 70 if evidence_score >= 60 else 50,
    }

    # ---------- hard gates: abstention ---------------------------------------
    core_kpis = [k for k in pilot_kpis if k.get("success_threshold") or k.get("target")]
    has_measurable = any(_kpi_achieved(k) is not None for k in core_kpis) if core_kpis else False
    if not pilot_kpis or not has_measurable:
        return _abstain("No measurable observed KPI result is available.",
                        ["Submit observed KPI measurements with evidence"], missing, risk_flags, factor_scores)
    if not validation:
        return _abstain("Independent validation has not been completed for this pilot.",
                        ["Complete the validation workflow (validator assignment, COI, findings, report)"],
                        missing, risk_flags, factor_scores)
    if not baseline_ok:
        return _abstain("Pilot baseline was never validated, so improvement cannot be computed reliably.",
                        ["Validate the baseline dataset"], missing, risk_flags, factor_scores)
    if len(high_conf_evidence) < max(1, len(pilot_kpis)):
        return _abstain(
            f"Evidence coverage is incomplete: {len(high_conf_evidence)} reviewable item(s) for "
            f"{len(pilot_kpis)} KPI(s).",
            ["Submit and review evidence for every KPI before requesting a decision"],
            missing, risk_flags, factor_scores)

    # ---------- recommendation ------------------------------------------------
    all_clear = len(not_achieved) == 0 and overall_finding == "SUPPORTED" and sec_reviewed
    if all_clear:
        outcome, confidence = "SCALE", 0.9
        reasons.append("All measurable KPIs cleared their success thresholds")
        reasons.append("Independent validation supports the outcome")
        reasons.append("Cybersecurity review completed")
    elif overall_finding in ("NOT_SUPPORTED", "CONTRADICTORY_EVIDENCE"):
        outcome, confidence = "REJECT", 0.7
        reasons.append("Independent validation does not support the claimed outcome")
        reasons.append("Re-running without fundamental changes is unlikely to change the result")
    elif not_achieved and not achieved:
        outcome, confidence = "REJECT", 0.65
        reasons.append("No KPI cleared its success threshold")
    else:
        outcome, confidence = "RE_PILOT", 0.75
        if not_achieved:
            reasons.append("Some KPIs are near but below their success thresholds — "
                           "a controlled re-pilot with corrected scope can close the gap")
        if not sec_reviewed:
            reasons.append("Cybersecurity review pending; required before any scale decision")
        reasons.append("Evidence supports continued evaluation rather than termination")

    confidence = round(min(0.95, max(0.5, confidence - 0.05 * len(missing) + 0.03 * len(supporting))), 2)
    return {
        "outcome": outcome,
        "confidence": confidence,
        "reasons": reasons,
        "supporting_evidence": supporting,
        "missing_evidence": missing,
        "risk_flags": risk_flags,
        "factor_scores": factor_scores,
        "factor_labels": FACTOR_LABELS,
        "engine_version": ENGINE_VERSION,
        "timestamp": None,  # stamped by router
        "disclaimer": "AI recommendation only. It does not constitute a government decision; "
                      "an authorized authority must decide, and overrides require a recorded reason.",
    }


def _abstain(core_reason: str, actions: list[str], missing: list[str],
             risk_flags: list[str], factor_scores: dict) -> dict:
    return {
        "outcome": "INSUFFICIENT_EVIDENCE",
        "confidence": 0.0,
        "reasons": [core_reason,
                    "The engine abstains rather than inventing a conclusion from incomplete data."],
        "supporting_evidence": [],
        "missing_evidence": sorted(set(missing + actions)),
        "risk_flags": risk_flags,
        "factor_scores": factor_scores,
        "factor_labels": FACTOR_LABELS,
        "engine_version": ENGINE_VERSION,
        "timestamp": None,
        "disclaimer": "INSUFFICIENT EVIDENCE is a valid outcome. AI recommendation ≠ government decision.",
    }


def get_decision_engine():
    class _E:
        VERSION = ENGINE_VERSION
        evaluate = staticmethod(evaluate)
    return _E()

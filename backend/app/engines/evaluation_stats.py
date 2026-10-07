"""Multi-expert aggregation statistics (average, median, min, max, stddev, disagreement)."""
import statistics


def weighted_total(scores: dict, criteria: list[dict]) -> float:
    total = 0.0
    for c in criteria:
        entry = scores.get(c["key"]) or {}
        total += float(entry.get("score", 0)) * c["weight"] / 100.0
    return round(total, 1)


def aggregate_evaluations(evaluations: list[dict], criteria: list[dict]) -> dict:
    """evaluations: [{scores, weighted_total, expert_id}] -> stats per startup."""
    totals = [e["weighted_total"] for e in evaluations if e.get("weighted_total") is not None]
    if not totals:
        return {"evaluation_count": 0, "average": None, "median": None, "minimum": None,
                "maximum": None, "stddev": None, "criterion_disagreement": {},
                "disagreement_flag": False, "consensus": "NOT STARTED"}

    criterion_disagreement = {}
    for c in criteria:
        values = [float((e.get("scores") or {}).get(c["key"], {}).get("score", 0)) for e in evaluations]
        spread = round(max(values) - min(values), 1) if values else 0
        if spread >= 30:
            criterion_disagreement[c["label"]] = spread

    stddev = round(statistics.pstdev(totals), 1) if len(totals) > 1 else 0.0
    spread_total = round(max(totals) - min(totals), 1) if len(totals) > 1 else 0.0
    flag = stddev >= 12 or spread_total >= 30
    consensus = ("HIGH EVALUATOR DISAGREEMENT" if flag
                 else "STRONG CONSENSUS" if stddev <= 7 else "MODERATE CONSENSUS")
    return {
        "evaluation_count": len(totals),
        "average": round(sum(totals) / len(totals), 1),
        "median": round(statistics.median(totals), 1),
        "minimum": round(min(totals), 1),
        "maximum": round(max(totals), 1),
        "stddev": stddev,
        "criterion_disagreement": criterion_disagreement,
        "disagreement_flag": flag,
        "consensus": consensus,
    }


RECOMMENDATION_RULES = [
    # (condition fn over aggregate dict, recommendation string)
    (lambda a: a["evaluation_count"] == 0, "AWAITING_EVALUATION"),
    (lambda a: a.get("disagreement_flag"), "NEEDS_PANEL_REVIEW"),
    (lambda a: (a["average"] or 0) >= 75 and a["stddev"] <= 15, "RECOMMENDED_FOR_PILOT"),
    (lambda a: (a["average"] or 0) >= 60, "CONDITIONAL — REVIEW REQUIRED"),
    (lambda a: True, "NOT_RECOMMENDED"),
]

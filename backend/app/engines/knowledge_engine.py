"""KnowledgeEngine — evidence-backed lesson extraction and similar-pilot similarity.

Generated lessons stay PENDING until an officer accepts/edits/ignores them.
Similarity is explainable: it names which dimensions matched.
"""
from app.engines.decision_engine import _num


class KnowledgeEngine:
    VERSION = "knowledge-engine@1.1"

    def extract_lessons(self, pilot: dict, kpis: list[dict], validation: dict | None,
                        decision: dict | None, milestones: list[dict]) -> list[dict]:
        """Rule-based lessons from a concluded pilot. Each candidate is PENDING."""
        lessons: list[dict] = []
        sector = pilot.get("department", "")
        base = {"pilot_id": pilot.get("id"), "sector": sector,
                "problem_type": pilot.get("objectives", "")[:120],
                "technology": pilot.get("startup_name", "")}

        validated = (validation or {}).get("validated_kpis") or {}
        overall = (validation or {}).get("overall_finding", "")

        for k in kpis:
            claimed, observed = _num(k.get("claimed_value")), _num(k.get("observed_value"))
            if claimed is not None and observed is not None and abs(claimed - observed) > 2:
                lessons.append({
                    **base,
                    "title": f"Claim calibration gap on {k['name']}",
                    "lesson": f"Startup claimed {k.get('claimed_value')} but field observation measured "
                              f"{k.get('observed_value')} for {k['name']}. Future challenge KPIs should define "
                              "measurement methods precisely and set expectations for claim variance.",
                    "evidence": f"Pilot {pilot.get('id')} KPI record; validation finding: {overall or 'pending'}.",
                    "recommendation": "Require instrumented measurement and pre-agreed data formats in pilot agreements.",
                    "tags": ["claim-vs-observed", "kpi-definition"],
                })
            if (k.get("status") in ("TARGET_NOT_ACHIEVED", "AT_RISK") or
                    (validated and str(validated.get(k["name"], "")).strip() and
                     _num(validated.get(k["name"])) is not None)):
                pass  # handled by other rules

        baseline = pilot.get("baseline") or {}
        sites = pilot.get("sites") or 0
        if baseline and (baseline.get("status") != "VALIDATED" or sites <= 3):
            lessons.append({
                **base,
                "title": "Baseline quality limits decision confidence",
                "lesson": f"Baseline dataset covered only {sites} site(s) and its validated status was "
                          f"{baseline.get('status', 'NOT VALIDATED')}. Decisions made on narrow baselines "
                          "carry higher uncertainty.",
                "evidence": f"Pilot {pilot.get('id')} baseline record: {baseline}.",
                "recommendation": "Expand baseline data collection across more sites before the next pilot or scale decision.",
                "tags": ["baseline", "data-coverage"],
            })

        if (validation or {}).get("overall_finding") == "PARTIALLY_SUPPORTED":
            lessons.append({
                **base,
                "title": "Partial validation narrows what can be claimed",
                "lesson": "Independent validation supported parts of the outcome but not all. Distinguish "
                          "which KPIs were validated when communicating pilot results.",
                "evidence": f"Validation report {(validation or {}).get('id', '')} findings.",
                "recommendation": "Break multi-part outcomes into separately validated KPIs in future pilots.",
                "tags": ["validation"],
            })

        pending_milestones = [m for m in milestones if m.get("status") not in ("ACCEPTED",)]
        if milestones and len(pending_milestones) > len(milestones) / 2:
            lessons.append({
                **base,
                "title": "Milestone delivery was slower than planned",
                "lesson": f"{len(pending_milestones)} of {len(milestones)} milestones were not accepted on schedule.",
                "evidence": "Pilot milestone ledger.",
                "recommendation": "Add interim milestone gates with evidence checkpoints instead of end-loaded deliverables.",
                "tags": ["delivery", "milestones"],
            })

        if decision and decision.get("decision") == "RE_PILOT":
            lessons.append({
                **base,
                "title": "Re-pilot chosen to close evidence gaps",
                "lesson": "The authority chose a controlled re-pilot instead of scale or termination, indicating "
                          "the direction was promising but evidence/scope was not yet decision-grade.",
                "evidence": f"Government decision {decision.get('id')} (reason recorded).",
                "recommendation": "Carry forward KPI results and expand scope where the previous pilot was too narrow.",
                "tags": ["re-pilot", "decision"],
            })

        if not lessons:
            lessons.append({
                **base,
                "title": "Pilot completed within expected parameters",
                "lesson": "Pilot completed without triggering exception rules. Record officer observations to "
                          "enrich the knowledge base beyond automated extraction.",
                "evidence": "No exception conditions matched in the automated review.",
                "recommendation": "Encourage officers to append qualitative lessons after each pilot.",
                "tags": ["general"],
            })
        return lessons

    def similar_pilots(self, reference: dict, corpus: list[dict], top_n: int = 4) -> list[dict]:
        """Explainable similarity across problem type, sector, technology, KPI, size, evidence, outcome."""
        scored = []
        ref_tech = set((reference.get("technology") or "").lower().split(", "))
        ref_words = set((reference.get("problem_type") or "").lower().replace(",", " ").split())
        for item in corpus:
            if item.get("id") == reference.get("id"):
                continue
            reasons, score = [], 0
            if item.get("sector") and item["sector"].lower() == (reference.get("sector") or "").lower():
                score += 25
                reasons.append(f"same sector ({item['sector']})")
            item_tech = set((item.get("technology") or "").lower().replace(",", " ").split())
            tech_hits = ref_tech & item_tech
            if tech_hits:
                score += 20
                reasons.append(f"shared technology: {', '.join(sorted(tech_hits))}")
            item_words = set((item.get("problem_type") or "").lower().replace(",", " ").split())
            word_hits = ref_words & item_words - {"and", "the", "for", "of"}
            if word_hits:
                score += 20
                reasons.append(f"similar problem keywords: {', '.join(sorted(word_hits)[:4])}")
            if item.get("kpi_focus") and item["kpi_focus"].lower() in (reference.get("kpi_focus") or "").lower():
                score += 15
                reasons.append(f"same KPI focus ({item['kpi_focus']})")
            if item.get("pilot_size") == reference.get("pilot_size"):
                score += 10
                reasons.append(f"comparable pilot size ({item['pilot_size']})")
            if item.get("evidence_quality") == reference.get("evidence_quality"):
                score += 5
                reasons.append(f"similar evidence quality ({item['evidence_quality']})")
            if item.get("outcome") and reference.get("outcome") and item["outcome"] == reference["outcome"]:
                score += 5
                reasons.append(f"same outcome ({item['outcome']})")
            if score >= 25:
                scored.append({"pilot": item, "similarity": min(100, score),
                               "why_similar": reasons or ["general domain proximity"]})
        scored.sort(key=lambda s: s["similarity"], reverse=True)
        return scored[:top_n]


def get_knowledge_engine() -> KnowledgeEngine:
    return KnowledgeEngine()

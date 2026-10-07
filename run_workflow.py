"""Run the full 8-minute SIH workflow on the seeded challenge CH-WTR-001."""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
DEMO = "govinnovate-demo"

def req(method, path, token=None, payload=None, role=None):
    body = None
    hd = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        hd["Content-Type"] = "application/json"
    if token:
        hd["Authorization"] = "Bearer " + token
    if role:
        hd["X-Demo-Role"] = role
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=hd)
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return None, str(e)

def login(role):
    st, d = req("POST", "/api/auth/login", payload={
        "email": EMAIL[role], "password": DEMO})
    return d.get("access_token") if st == 200 else None

EMAIL = {
    "government_officer": "arjun.kulkarni@demo.gov.in",
    "expert": "r.kelkar@demo-expert.in",
    "validator": "v.deshpande@demo-validator.in",
    "senior_authority": "meera.deshmukh@demo.gov.in",
}

CHALLENGE_ID = "CH-WTR-001"

def dump_challenge(role="government_officer"):
    st, d = req("GET", "/api/challenges/" + CHALLENGE_ID, role=role)
    c = d if isinstance(d, dict) else {}
    import json
    print("  title:", json.dumps(c.get("title")))
    print("  dept:", json.dumps(c.get("department")))
    print("  pc:", json.dumps(c.get("pilot_criteria")))
    print("  data_policy:", json.dumps(c.get("data_policy")))
    print("  cyber:", json.dumps(c.get("cybersecurity")))
    print("  risks:", json.dumps(c.get("risks")))
    print("  requirements:", json.dumps(c.get("requirements")))
    print("  kpis:", [k.get("name") for k in c.get("kpis", [])])
    print("  status:", c.get("status"))

def main():
    tok = login("government_officer")
    print("=== STAGE 1: PROBLEM (seeded CH-WTR-001) ===")
    dump_challenge()

    print("=== STAGE 2: AI REQUIREMENTS ===")
    tok2 = login("government_officer")
    st, d = req("POST", "/api/challenges/" + CHALLENGE_ID + "/ai/analyse", token=tok2)
    print("  ai analyse:", st, "suggestions:", len(d.get("suggestions", [])))
    # accept first two functional
    for s in d.get("suggestions", []):
        cat, txt = s.get("category"), s.get("text", "")
        if cat == "functional" and ("real-time monitoring" in txt or "configurable leakage" in txt):
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=ACCEPT",
                        token=tok2, payload={})
            print("  accept", txt[:55], ":", st)
    # reject offline-first
    for s in d.get("suggestions", []):
        if "offline-first" in s.get("text", ""):
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=REJECT",
                        token=tok2, payload={})
            print("  reject offline-first:", st)
            break
    st, d = req("GET", "/api/challenges/" + CHALLENGE_ID,        role="government_officer")
    c = d if isinstance(d, dict) else {}
    print("  official funcs:", c.get("requirements", {}).get("functional"))

    print("=== STAGE 3: KPI BUILDER ===")
    st, d = req("POST", "/api/challenges/" + CHALLENGE_ID + "/kpis", token=tok2, payload={
        "name": "Leakage Detection Time", "baseline": "48", "target": "12", "unit": "Hours",
        "measurement_method": "Verified comparison between leakage event/report time and system detection time.",
        "evidence_source": "Municipal maintenance records + platform monitoring logs", "success_threshold": "<=18"})
    print("  kpi1:", st)
    st, d = req("POST", "/api/challenges/" + CHALLENGE_ID + "/kpis", token=tok2, payload={
        "name": "Leakage Reduction", "baseline": "0%", "target": "30", "unit": "%",
        "measurement_method": "Compare verified pre-pilot and pilot-period leakage measurements.",
        "evidence_source": "Municipal maintenance records + platform monitoring logs", "success_threshold": ">=25"})
    print("  kpi2:", st)
    st, d = req("GET", "/api/challenges/" + CHALLENGE_ID,        role="government_officer")
    c = d if isinstance(d, dict) else {}
    print("  kpis:", [k.get("name") for k in c.get("kpis", [])])

    print("=== STAGE 4: PILOT CRITERIA ===")
    st, d = req("PATCH", "/api/challenges/" + CHALLENGE_ID, token=tok2, payload={
        "pilot_criteria": {"duration_weeks": 60, "budget_max": 1000000, "number_of_sites": 3,
                           "target_users": "3 selected municipal wards",
                           "geographic_scope": "3 selected municipal wards",
                           "success_conditions": "Validate leakage detection time and reduce water loss",
                           "payment_conditions": "paid on milestone completion"}})
    print("  patch:", st)
    dump_challenge()

    print("=== STAGE 5: DATA/IP/SECURITY ===")
    st, d = req("PATCH", "/api/challenges/" + CHALLENGE_ID, token=tok2, payload={
        "data_policy": {"ownership": "Municipal pipeline records, leakage reports and pilot monitoring data.",
                        "access": "Authorized pilot participants only."},
        "ip_policy": {"pre_existing": "Startup retains pre-existing IP.",
                      "new_ip": "Pilot-specific outputs governed through pilot agreement."},
        "cybersecurity": {"authentication": "Cybersecurity review required before live deployment.",
                          "encryption": "TLS 1.2+"},
        "risks": [{"risk": "False alerts", "probability": 3, "impact": 3},
                  {"risk": "Incomplete baseline data", "probability": 3, "impact": 3},
                  {"risk": "System integration risk", "probability": 2, "impact": 3}]})
    print("  patch:", st)
    dump_challenge()

    print("=== STAGE 6: REVIEW ===")
    st, d = req("GET", "/api/challenges/" + CHALLENGE_ID + "/review", token=tok2, role="government_officer")
    print("  review:", st, d if not isinstance(d, dict) else d.get("errors"))

    print("=== STAGE 7: PUBLISH ===")
    st, d = req("POST", "/api/challenges/" + CHALLENGE_ID + "/publish", token=tok2, role="government_officer")
    print("  publish:", st)
    dump_challenge()

    print("=== STAGE 8: MATCHING ===")
    st, d = req("POST", "/api/matching/" + CHALLENGE_ID + "/run", token=tok2, role="government_officer")
    print("  run matching:", st)
    st, d = req("GET", "/api/matching/" + CHALLENGE_ID)
    matches = d if isinstance(d, list) else []
    aqua = [m for m in matches if m.get("startup", {}).get("id") == "ST-001"]
    print("  Aquasense matches:", len(aqua))

    print("=== STAGE 9: EXPERT EVALUATOR + COI ===")
    tok3 = login("expert")
    st, d = req("GET", "/api/evaluations/assignments?challenge_id=" + CHALLENGE_ID, token=tok3)
    asg = None
    for a in (d if isinstance(d, list) else []):
        if a.get("startup_id") == "ST-001":
            asg = a
            break
    print("  assignments:", asg is not None)
    if asg is None:
        st, d = req("POST", "/api/evaluations/assign", token=tok2, payload={
            "challenge_id": CHALLENGE_ID, "startup_id": "ST-001", "expert_id": "U-EXP1"},
            role="government_officer")
        print("  assign expert:", st)
    if asg:
        a_id = asg.get("id")
        print("  assignment status:", asg.get("status"))
        st, d = req("POST", "/api/evaluations/assignments/" + a_id + "/coi", token=tok3,
                    payload={"status": "NO_CONFLICT"}, role="expert")
        print("  coi:", st, d if not isinstance(d, dict) else d.get("status"))
        st, d = req("POST", "/api/evaluations/assignments/" + a_id + "/evaluation", token=tok3,
                    payload={"scores": {"problem_fit": 9, "technical_feasibility": 8, "relevant_experience": 8,
                                        "evidence_quality": 8, "pilot_readiness": 8, "scalability": 8,
                                        "value_for_money": 8, "risk_compliance": 8},
                             "recommendation": "RECOMMEND_FOR_PILOT",
                             "final_comments": "The solution is relevant to municipal leakage detection and suitable for controlled pilot testing. Additional evidence is required before wider deployment."},
                    role="expert")
        print("  eval:", st)
        st, d = req("GET", "/api/evaluations/assignments/" + a_id, token=tok3)
        print("  assignment after eval:", d if not isinstance(d, dict) else d.get("status"))

    print("=== STAGE 10: PILOT CREATION ===")
    tok4 = login("official")
    st, d = req("POST", "/api/pilots", token=tok4, payload={
        "name": "Pilot 01 — AquaSense Technologies", "startup_id": "ST-001",
        "challenge_id": CHALLENGE_ID, "duration_weeks": 60, "budget": 1000000,
        "objectives": "Validate technology-based monitoring for leakage detection",
        "sites": 3, "target_users": "3 selected municipal wards",
        "geographic_scope": "3 selected municipal wards"},        role="government_officer")
    pid = d.get("id") if isinstance(d, dict) else None
    print("  create pilot:", st, pid)
    st, d = req("GET", "/api/pilots/" + str(pid),        role="government_officer")
    p = d if isinstance(d, dict) else {}
    print("  pilot kpis:", [k.get("name") for k in p.get("kpis", [])])
    print("  pilot milestones:", len(p.get("milestones", [])))

    print("=== STAGE 11: PILOT KPI MONITORING ===")
    for k in p.get("kpis", []):
        obs = "17" if k.get("name") == "Leakage Detection Time" else "18"
        st, d = req("POST", "/api/pilots/" + str(pid) + "/kpis/" + str(k.get("id")) + "/observation",
                    token=tok4, payload={"observed_value": obs, "status": "TARGET_ACHIEVED"},        role="government_officer")
        print("  obs", k.get("name"), obs, ":", st)
    st, d = req("GET", "/api/pilots/" + str(pid),        role="government_officer")
    p = d if isinstance(d, dict) else {}
    for k in p.get("kpis", []):
        print("  ", k.get("name"), "observed:", k.get("observed_value"))

    print("=== STAGE 12: MILESTONES ===")
    st, d = req("GET", "/api/pilots/" + str(pid),        role="government_officer")
    p = d if isinstance(d, dict) else {}
    ms = p.get("milestones", [])
    print("  milestones:", len(ms), "total:", sum(m.get("payment_percentage", 0) for m in ms))
    for m in ms:
        if m.get("payment_percentage") in (10, 20, 25):
            st, d = req("PATCH", "/api/pilots/" + str(pid) + "/milestones/" + str(m.get("id")) + "/status",
                        token=tok4, payload={"status": "ACCEPTED"},        role="government_officer")
            print("  milestone", m.get("name"), ":", st)
    st, d = req("GET", "/api/pilots/" + str(pid),        role="government_officer")
    p = d if isinstance(d, dict) else {}
    print("  accepted:", sum(1 for m in p.get("milestones", []) if m.get("status") == "ACCEPTED"), "/", len(ms))

    print("=== STAGE 13: EVIDENCE ===")
    st, d = req("POST", "/api/evidence", token=tok4, payload={
        "pilot_id": pid, "evidence_type": "REPORT", "title": "21% reduction claim",
        "description": "Startup claim of 21% reduction", "claimed_value": "21%"},        role="government_officer")
    print("  evidence1:", st)
    st, d = req("POST", "/api/evidence", token=tok4, payload={
        "pilot_id": pid, "evidence_type": "REPORT", "title": "19% observed result",
        "description": "Observed 19% reduction", "claimed_value": "19%"},        role="government_officer")
    print("  evidence2:", st)
    st, d = req("GET", "/api/evidence?pilot_id=" + str(pid),        role="government_officer")
    ev = d if isinstance(d, list) else []
    print("  evidence rows:", len(ev))

    print("=== STAGE 14: VALIDATION ===")
    tok5 = login("validator")
    st, d = req("GET", "/api/validation/packages?pilot_id=" + str(pid), token=tok5, role="senior")
    pkgs = d if isinstance(d, list) else []
    pkg = pkgs[0] if pkgs else None
    print("  packages:", [p.get("id") for p in pkgs])
    if pkg:
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/assign?validator_id=" + EMAIL["validator"], token=tok2,        role="government_officer")
        print("  assign validator:", st)
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/start", token=tok5, role="validator")
        print("  start validation:", st)
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/findings", token=tok5,
                    payload={"claimed": "21%", "observed": "19%", "validated_value": "18%",
                             "target": ">=25%", "finding": "PARTIALLY_SUPPORTED",
                             "explanation": "Evidence supports measurable improvement, but the predefined scale success threshold has not been achieved."}, role="validator")
        print("  finding:", st)
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/report", token=tok5,
                    payload={"summary": "Independent analysis supports a real improvement at 18%, below the 25% target.",
                             "overall_finding": "PARTIALLY_SUPPORTED",
                             "validated_kpis": {"Leakage Detection Time": "17h", "Leakage Reduction": "18%"}}, role="validator")
        print("  report:", st)

    print("=== STAGE 15: SENIOR AUTHORITY DECISION ===")
    tok6 = login("senior")
    st, d = req("POST", "/api/decisions/" + str(pid) + "/recommendation", token=tok6, role="senior")
    print("  generate rec:", st, d.get("outcome") if isinstance(d, dict) else d)
    st, d = req("POST", "/api/decisions/" + str(pid) + "/government-decision", token=tok6,
                payload={"decision": "RE_PILOT",
                         "reason": "Pilot demonstrates measurable improvement, but current evidence does not satisfy the predefined scale threshold.",
                         "override": False}, role="senior")
    print("  gov decision:", st)

main()

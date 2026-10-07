"""Test full 8-minute workflow from a fresh DRAFT challenge, with proper auth."""
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

def main():
    tok = login("government_officer")
    # 1. CREATE CHALLENGE (DRAFT)
    p = {
        "title": "AI-Based Municipal Water Leakage Detection",
        "department": "Municipal Water Department",
        "problem_category": "Water Management",
        "priority": "HIGH",
        "problem_statement": "Department has limited visibility into leakage across municipal pipelines, causing water loss and delayed maintenance.",
        "current_situation": "Leakage is mainly identified through citizen complaints and manual inspection.",
        "current_limitations": "Manual inspection is slow and the department cannot identify leakage locations quickly.",
        "expected_outcome": "Reduce water loss and identify leakage locations faster using technology-based monitoring.",
        "geographic_scope": "Selected Municipal Wards in Maharashtra",
        "existing_process": "Leakage is mainly identified through citizen complaints and manual inspection.",
        "constraints": "",
        "budget_min": 600000, "budget_max": 1000000,
    }
    st, d = req("POST", "/api/challenges", token=tok, payload=p)
    cid = d.get("id")
    print("1. create challenge:", st, cid)
    # verify fields persisted
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print("   title:", c.get("title"))
    print("   dept:", c.get("department"))
    print("   pc:", c.get("pilot_criteria"))
    print("   data_policy:", c.get("data_policy"))
    print("   cyber:", c.get("cybersecurity"))
    print("   status:", c.get("status"))

    # 2. AI REQUIREMENTS
    st, d = req("POST", "/api/challenges/" + cid + "/ai/analyse", token=tok)
    print("2. ai analyse:", st)
    sugs = d.get("suggestions", []) if isinstance(d, list) else []
    print("   suggestions:", len(sugs))
    for s in sugs:
        txt = s.get("text", "")
        if "real-time monitoring" in txt:
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=ACCEPT",
                        token=tok, payload={})
            print("   accept real-time monitoring:", st)
        elif "configurable leakage" in txt:
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=ACCEPT",
                        token=tok, payload={})
            print("   accept configurable alerting:", st)
        elif "offline-first" in txt:
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=REJECT",
                        token=tok, payload={})
            print("   reject offline-first:", st)
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print("   official funcs:", c.get("requirements", {}).get("functional"))

    # 3. KPI BUILDER
    st, d = req("POST", "/api/challenges/" + cid + "/kpis", token=tok, payload={
        "name": "Leakage Detection Time", "baseline": "48", "target": "12", "unit": "Hours",
        "measurement_method": "Verified comparison between leakage event/report time and system detection time.",
        "evidence_source": "Municipal maintenance records + platform monitoring logs", "success_threshold": "<=18"})
    print("3. kpi1:", st)
    st, d = req("POST", "/api/challenges/" + cid + "/kpis", token=tok, payload={
        "name": "Leakage Reduction", "baseline": "0%", "target": "30", "unit": "%",
        "measurement_method": "Compare verified pre-pilot and pilot-period leakage measurements.",
        "evidence_source": "Municipal maintenance records + platform monitoring logs", "success_threshold": ">=25"})
    print("   kpi2:", st)
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print("   kpis:", [k.get("name") for k in c.get("kpis", [])])

    # 4. PILOT CRITERIA
    st, d = req("PATCH", "/api/challenges/" + cid, token=tok, payload={
        "pilot_criteria": {"duration_weeks": 60, "budget_max": 1000000, "number_of_sites": 3,
                           "target_users": "3 selected municipal wards",
                           "geographic_scope": "3 selected municipal wards",
                           "success_conditions": "Validate leakage detection time and reduce water loss",
                           "payment_conditions": "paid on milestones"}})
    print("4. patch pilot criteria:", st)
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print("   pc:", c.get("pilot_criteria"))

    # 5. DATA/IP/SECURITY
    st, d = req("PATCH", "/api/challenges/" + cid, token=tok, payload={
        "data_policy": {"ownership": "Municipal pipeline records, leakage reports and pilot monitoring data.",
                        "access": "Authorized pilot participants only."},
        "ip_policy": {"pre_existing": "Startup retains pre-existing IP.",
                      "new_ip": "Pilot-specific outputs governed through pilot agreement."},
        "cybersecurity": {"authentication": "Cybersecurity review required before live deployment.",
                          "encryption": "TLS 1.2+"},
        "risks": [{"risk": "False alerts", "probability": 3, "impact": 3},
                  {"risk": "Incomplete baseline data", "probability": 3, "impact": 3},
                  {"risk": "System integration risk", "probability": 2, "impact": 3}]})
    print("5. patch data/ip/security:", st)
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print("   cyber:", c.get("cybersecurity"))
    print("   data_policy:", c.get("data_policy"))

    # 6. REVIEW
    st, d = req("GET", "/api/challenges/" + cid + "/review", token=tok)
    print("6. review:", st, d if not isinstance(d, dict) else d.get("errors"))

    # 7. PUBLISH
    st, d = req("POST", "/api/challenges/" + cid + "/publish", token=tok)
    print("7. publish:", st)
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print("   status:", c.get("status"))

    # 8. MATCHING
    st, d = req("POST", "/api/matching/" + cid + "/run", token=tok)
    print("8. run matching:", st)
    st, d = req("GET", "/api/matching/" + cid, token=tok)
    matches = d if isinstance(d, list) else []
    aqua = [m for m in matches if m.get("startup", {}).get("id") == "ST-001"]
    print("   Aquasense matches:", len(aqua), "total matches:", len(matches))

    # 9. EXPERT EVALUATOR + COI
    tok2 = login("expert")
    st, d = req("GET", "/api/evaluations/assignments?challenge_id=" + cid, token=tok2)
    asg = None
    for a in (d if isinstance(d, list) else []):
        if a.get("startup_id") == "ST-001":
            asg = a
            break
    print("9. assignment for ST-001:", asg is not None)
    if asg is None:
        st, d = req("POST", "/api/evaluations/assign", token=tok, payload={
            "challenge_id": cid, "startup_id": "ST-001", "expert_id": "U-EXP1"}, role="government_officer")
        print("   assign expert:", st)
    if asg:
        a_id = asg.get("id")
        print("   assignment status:", asg.get("status"))
        st, d = req("POST", "/api/evaluations/assignments/" + a_id + "/coi", token=tok2,
                    payload={"status": "NO_CONFLICT"}, role="expert")
        print("   COI:", st, d if not isinstance(d, dict) else d.get("status"))
        st, d = req("POST", "/api/evaluations/assignments/" + a_id + "/evaluation", token=tok2,
                    payload={"scores": {"problem_fit": 9, "technical_feasibility": 8, "relevant_experience": 8,
                                        "evidence_quality": 8, "pilot_readiness": 8, "scalability": 8,
                                        "value_for_money": 8, "risk_compliance": 8},
                             "recommendation": "RECOMMEND_FOR_PILOT",
                             "final_comments": "The solution is relevant to municipal leakage detection and suitable for controlled pilot testing. Additional evidence is required before wider deployment."},
                    role="expert")
        print("   eval:", st)
        st, d = req("GET", "/api/evaluations/assignments/" + a_id, token=tok2)
        print("   assignment after eval:", d if not isinstance(d, dict) else d.get("status"))

    # 10. PILOT CREATION
    tok3 = login("government_officer")
    st, d = req("POST", "/api/pilots", token=tok3, payload={
        "name": "Pilot 01 — AquaSense Technologies", "startup_id": "ST-001",
        "challenge_id": cid, "duration_weeks": 60, "budget": 1000000,
        "objectives": "Validate technology-based monitoring for leakage detection",
        "sites": 3, "target_users": "3 selected municipal wards",
        "geographic_scope": "3 selected municipal wards"}, role="government_officer")
    pid = d.get("id") if isinstance(d, dict) else None
    print("10. create pilot:", st, pid)
    st, d = req("GET", "/api/pilots/" + str(pid), role="government_officer")
    p = d if isinstance(d, dict) else {}
    print("    pilot kpis:", [k.get("name") for k in p.get("kpis", [])])
    print("    pilot milestones:", len(p.get("milestones", [])))

    # 11. PILOT KPI MONITORING
    for k in p.get("kpis", []):
        obs = "17" if k.get("name") == "Leakage Detection Time" else "18"
        st, d = req("POST", "/api/pilots/" + str(pid) + "/kpis/" + str(k.get("id")) + "/observation",
                    token=tok3, payload={"observed_value": obs, "status": "TARGET_ACHIEVED"}, role="government_officer")
        print("    obs", k.get("name"), obs, ":", st)
    st, d = req("GET", "/api/pilots/" + str(pid), role="government_officer")
    p = d if isinstance(d, dict) else {}
    for k in p.get("kpis", []):
        print("    ", k.get("name"), "observed:", k.get("observed_value"))

    # 12. MILESTONES
    st, d = req("GET", "/api/pilots/" + str(pid), role="government_officer")
    p = d if isinstance(d, dict) else {}
    ms = p.get("milestones", [])
    print("12. milestones:", len(ms), "total:", sum(m.get("payment_percentage", 0) for m in ms))
    for m in ms:
        if m.get("payment_percentage") in (10, 20, 25):
            st, d = req("PATCH", "/api/pilots/" + str(pid) + "/milestones/" + str(m.get("id")) + "/status",
                        token=tok3, payload={"status": "ACCEPTED"}, role="government_officer")
            print("    milestone", m.get("name"), ":", st)

    # 13. EVIDENCE
    st, d = req("POST", "/api/evidence", token=tok3, payload={
        "pilot_id": pid, "evidence_type": "REPORT", "title": "21% reduction claim",
        "description": "Startup claim of 21% reduction", "claimed_value": "21%"}, role="government_officer")
    print("13. evidence1:", st)
    st, d = req("POST", "/api/evidence", token=tok3, payload={
        "pilot_id": pid, "evidence_type": "REPORT", "title": "19% observed result",
        "description": "Observed 19% reduction", "claimed_value": "19%"}, role="government_officer")
    print("    evidence2:", st)

    # 14. VALIDATION
    tok4 = login("validator")
    st, d = req("GET", "/api/validation/packages?pilot_id=" + str(pid), token=tok4, role="senior_authority")
    pkgs = d if isinstance(d, list) else []
    pkg = pkgs[0] if pkgs else None
    print("14. packages:", [p.get("id") for p in pkgs])
    if pkg:
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/assign?validator_id=" + EMAIL["validator"], token=tok3, role="government_officer")
        print("    assign validator:", st)
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/start", token=tok4, role="validator")
        print("    start validation:", st)
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/findings", token=tok4,
                    payload={"claimed": "21%", "observed": "19%", "validated_value": "18%",
                             "target": ">=25%", "finding": "PARTIALLY_SUPPORTED",
                             "explanation": "Evidence supports measurable improvement, but the predefined scale success threshold has not been achieved."}, role="validator")
        print("    finding:", st)
        st, d = req("POST", "/api/validation/packages/" + str(pkg.get("id")) + "/report", token=tok4,
                    payload={"summary": "Independent analysis supports a real improvement at 18%, below the 25% target.",
                             "overall_finding": "PARTIALLY_SUPPORTED",
                             "validated_kpis": {"Leakage Detection Time": "17h", "Leakage Reduction": "18%"}}, role="validator")
        print("    report:", st)

    # 15. SENIOR AUTHORITY DECISION
    tok5 = login("senior_authority")
    st, d = req("POST", "/api/decisions/" + str(pid) + "/recommendation", token=tok5, role="senior_authority")
    print("15. generate rec:", st, d.get("outcome") if isinstance(d, dict) else d)
    st, d = req("POST", "/api/decisions/" + str(pid) + "/government-decision", token=tok5,
                payload={"decision": "RE_PILOT",
                         "reason": "Pilot demonstrates measurable improvement, but current evidence does not satisfy the predefined scale threshold.",
                         "override": False}, role="senior_authority")
    print("    gov decision:", st)

main()

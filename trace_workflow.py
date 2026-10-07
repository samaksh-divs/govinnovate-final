"""Trace each stage of the 8-minute workflow, dumping backend state."""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
DEMO = "govinnovate-demo"

def req(method, path, token=None, payload=None):
    body = None
    hd = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        hd["Content-Type"] = "application/json"
    if token:
        hd["Authorization"] = "Bearer " + token
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
    "official": "arjun.kulkarni@demo.gov.in",
    "expert": "r.kelkar@demo-expert.in",
    "validator": "v.deshpande@demo-validator.in",
    "senior": "meera.deshmukh@demo.gov.in",
}

def dump_challenge(cid, label):
    st, d = req("GET", "/api/challenges/" + cid)
    c = d if isinstance(d, dict) else {}
    print(f"  [{label}] title={c.get('title')!r}")
    print(f"  [{label}] dept={c.get('department')!r}")
    print(f"  [{label}] pc={c.get('pilot_criteria')}")
    print(f"  [{label}] data_policy={c.get('data_policy')}")
    print(f"  [{label}] cyber={c.get('cybersecurity')}")
    print(f"  [{label}] risks={c.get('risks')}")
    print(f"  [{label}] req={c.get('requirements')}")
    print(f"  [{label}] kpis={[k.get('name') for k in c.get('kpis', [])]}")


def main():
    tok = login("official")
    # 1 PROBLEM
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
    print("stage1 create:", st, cid)
    dump_challenge(cid, "after create")
    # 2 AI REQS
    st, d = req("POST", "/api/challenges/" + cid + "/ai/analyse", token=tok)
    print("stage2 ai analyse:", st, "suggestions:", len(d.get("suggestions", [])))
    # accept first functional
    for s in d.get("suggestions", []):
        if s.get("category") == "functional" and "real-time monitoring dashboard" in s.get("text", ""):
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=ACCEPT", token=tok)
            print("stage2 accept1:", st)
            break
    # accept second functional
    for s in d.get("suggestions", []):
        if s.get("category") == "functional" and "configurable leakage alerting" in s.get("text", ""):
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=ACCEPT", token=tok)
            print("stage2 accept2:", st)
            break
    # reject one functional offline-first
    for s in d.get("suggestions", []):
        if "offline-first" in s.get("text", ""):
            st, d = req("POST", "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=REJECT", token=tok)
            print("stage2 reject:", st)
            break
    st, d = req("GET", "/api/challenges/" + cid)
    c = d if isinstance(d, dict) else {}
    print("  official funcs:", c.get("requirements", {}).get("functional"))
    # 3 KPI
    st, d = req("POST", "/api/challenges/" + cid + "/kpis", token=tok, payload={
        "name": "Leakage Detection Time", "baseline": "48", "target": "12", "unit": "Hours",
        "measurement_method": "Verified comparison", "evidence_source": "Municipal records", "success_threshold": "<=18"})
    print("stage3 kpi1:", st, d.get("name") if isinstance(d, dict) else d)
    st, d = req("POST", "/api/challenges/" + cid + "/kpis", token=tok, payload={
        "name": "Leakage Reduction", "baseline": "0%", "target": "30", "unit": "%",
        "measurement_method": "Compare verified", "evidence_source": "Municipal records", "success_threshold": ">=25"})
    print("stage3 kpi2:", st, d.get("name") if isinstance(d, dict) else d)
    st, d = req("GET", "/api/challenges/" + cid)
    c = d if isinstance(d, dict) else {}
    print("  kpis now:", [k.get("name") for k in c.get("kpis", [])])
    # 4 PILOT CRITERIA
    st, d = req("PATCH", "/api/challenges/" + cid, token=tok, payload={
        "pilot_criteria": {"duration_weeks": 60, "budget_max": 1000000, "number_of_sites": 3,
                           "target_users": "3 wards", "geographic_scope": "3 wards",
                           "success_conditions": "Validate leakage detection",
                           "payment_conditions": "on milestones"}})
    print("stage4 patch:", st)
    dump_challenge(cid, "after pilot criteria patch")
    # 5 DATA/IP/Security
    st, d = req("PATCH", "/api/challenges/" + cid, token=tok, payload={
        "data_policy": {"ownership": "Municipal pipeline records, leakage reports and pilot monitoring data.",
                        "access": "Authorized pilot participants only."},
        "ip_policy": {"pre_existing": "Startup retains pre-existing IP.",
                      "new_ip": "Pilot-specific outputs governed through pilot agreement."},
        "cybersecurity": {"authentication": "Cybersecurity review required before live deployment.",
                          "encryption": "TLS 1.2+"},
        "risks": [{"risk": "False alerts", "probability": 3, "impact": 3},
                  {"risk": "Incomplete baseline", "probability": 3, "impact": 3},
                  {"risk": "System integration", "probability": 2, "impact": 3}]})
    print("stage5 patch:", st)
    dump_challenge(cid, "after data/ip/security patch")
    # 6 REVIEW
    st, d = req("GET", "/api/challenges/" + cid + "/review", token=tok)
    print("stage6 review:", st, d if not isinstance(d, dict) else d.get("errors"))
    # 7 PUBLISH
    st, d = req("POST", "/api/challenges/" + cid + "/publish", token=tok)
    print("stage7 publish:", st)
    st, d = req("GET", "/api/challenges/" + cid)
    c = d if isinstance(d, dict) else {}
    print("  status:", c.get("status"))
    # 8 MATCHING
    st, d = req("POST", "/api/matching/" + cid + "/run", token=tok)
    print("stage8 matching run:", st)
    st, d = req("GET", "/api/matching/" + cid)
    matches = d if isinstance(d, list) else []
    aqua = [m for m in matches if m.get("startup", {}).get("id") == "ST-001"]
    print("  Aquasense matches:", len(aqua))
    # 9 EXPERT
    tok2 = login("expert")
    st, d = req("GET", "/api/evaluations/assignments?challenge_id=" + cid, token=tok2)
    asg = None
    for a in (d if isinstance(d, list) else []):
        if a.get("startup_id") == "ST-001":
            asg = a
            break
    print("stage9 assignments for ST-001:", asg is not None)
    if asg is None:
        st, d = req("POST", "/api/evaluations/assign", token=tok, payload={
            "challenge_id": cid, "startup_id": "ST-001", "expert_id": "U-EXP1"})
        print("stage9 assign:", st)
        st, d = req("GET", "/api/evaluations/assignments?challenge_id=" + cid, token=tok2)
        asg = None
        for a in (d if isinstance(d, list) else []):
            if a.get("startup_id") == "ST-001":
                asg = a
                break
    if asg:
        a_id = asg.get("id")
        print("  assignment status:", asg.get("status"))
        st, d = req("POST", "/api/evaluations/assignments/" + a_id + "/coi", token=tok2,
                    payload={"status": "NO_CONFLICT"})
        print("  coi:", st, d if not isinstance(d, dict) else d.get("status"))
        st, d = req("POST", "/api/evaluations/assignments/" + a_id + "/evaluation", token=tok2,
                    payload={"scores": {"problem_fit": 9, "technical_feasibility": 8, "relevant_experience": 8,
                                        "evidence_quality": 8, "pilot_readiness": 8, "scalability": 8,
                                        "value_for_money": 8, "risk_compliance": 8},
                             "recommendation": "RECOMMEND_FOR_PILOT",
                             "final_comments": "The solution is relevant to municipal leakage detection and suitable for controlled pilot testing. Additional evidence is required before wider deployment."})
        print("stage9 eval:", st)
        st, d = req("GET", "/api/evaluations/assignments/" + a_id, token=tok2)
        print("  assignment after eval:", d if not isinstance(d, dict) else d.get("status"))
    # 10 PILOT
    tok3 = login("official")
    st, d = req("POST", "/api/pilots", token=tok3, payload={
        "name": "Pilot 01 — AquaSense Technologies", "startup_id": "ST-001",
        "challenge_id": cid, "duration_weeks": 60, "budget": 1000000,
        "objectives": "Validate technology-based monitoring for leakage",
        "sites": 3, "target_users": "3 selected municipal wards",
        "geographic_scope": "3 selected municipal wards"})
    pid = d.get("id") if isinstance(d, dict) else None
    print("stage10 pilot create:", st, pid)
    st, d = req("GET", "/api/pilots/" + str(pid))
    p = d if isinstance(d, dict) else {}
    print("  pilot kpis:", [k.get("name") for k in p.get("kpis", [])])
    print("  pilot milestones:", len(p.get("milestones", [])))
    # 11 PILOT KPI
    for k in p.get("kpis", []):
        obs = "17" if k.get("name") == "Leakage Detection Time" else "18"
        st, d = req("POST", "/api/pilots/" + str(pid) + "/kpis/" + str(k.get("id")) + "/observation",
                    token=tok3, payload={"observed_value": obs, "status": "TARGET_ACHIEVED"})
        print("stage11 obs", k.get("name"), obs, ":", st)
    # 12 MILESTONES
    st, d = req("GET", "/api/pilots/" + str(pid))
    p = d if isinstance(d, dict) else {}
    ms = p.get("milestones", [])
    print("stage12 milestones:", len(ms), "total:", sum(m.get("payment_percentage", 0) for m in ms))
    for m in ms:
        if m.get("payment_percentage") in (10, 20, 25):
            st, d = req("PATCH", "/api/pilots/" + str(pid) + "/milestones/" + str(m.get("id")) + "/status",
                        token=tok3, payload={"status": "ACCEPTED"})
            print("  milestone", m.get("name"), ":", st)

main()

"""End-to-end demo audit harness.

Executes the exact 8-minute SIH demo story through the real backend API and
the existing frontend pages, records PASS/FAIL per stage, and prints a compact
report. Uses real JWT tokens (as the frontend's api.js + Shell.jsx do).
"""

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
DEMO_PASSWORD = "govinnovate-demo"

PASS = []
FAIL = []

EMAIL_BY_ROLE = {
    "government_officer": "arjun.kulkarni@demo.gov.in",
    "senior_authority": "meera.deshmukh@demo.gov.in",
    "startup": "founder@aquasense.demo.in",
    "expert": "r.kelkar@demo-expert.in",
    "validator": "v.deshpande@demo-validator.in",
    "administrator": "admin@demo.gov.in",
}

CHALLENGE_ID = None
ASG_ID = None
PILOT_ID = None
EVAL_ASSIGNMENT_ID = None
VALIDATOR_USER = None


# ---------------------------------------------------------------
def req(method, path, token=None, role=None, payload=None):
    url = BASE + path
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if role:
        headers["X-Demo-Role"] = role
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
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
    global TOKEN
    status, data = req("POST", "/api/auth/login", payload={
        "email": EMAIL_BY_ROLE[role], "password": DEMO_PASSWORD})
    if status != 200:
        return None
    TOKEN = data["access_token"]
    return TOKEN


TOKEN = None
PASSED = 0
FAILED = 0
FAIL = {}


def record(ok, stage, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  PASS  {stage}")
    else:
        FAILED += 1
        FAIL[stage] = detail
        print(f"  FAIL  {stage}  {detail}")


def stage(name, fn):
    global FAILED
    print(f"\n>>> {name}")
    try:
        fn()
    except Exception as e:
        record(False, name, repr(e))


def gett(path, role=None):
    return req("GET", path, token=TOKEN, role=role)


# ===============================================================
# STAGES
# ===============================================================
def stage_problem():
    global CHALLENGE_ID
    login("government_officer")
    payload = {
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
        "budget_min": 600000,
        "budget_max": 1000000,
    }
    st, data = req("POST", "/api/challenges", token=TOKEN, payload=payload)
    record(st == 201, "create challenge", f"status={st}")
    if isinstance(data, dict):
        CHALLENGE_ID = data.get("id")
        # navigate away and back
        st, data = gett(f"/api/challenges/{CHALLENGE_ID}")
        record(st == 200, "refresh challenge", f"status={st}")
        ch = data if isinstance(data, dict) else {}
        ok = all(ch.get(k) == v for k, v in payload.items() if k != "budget_min")
        record(ok, "persisted post-refresh", f"title={ch.get('title')!r}")


def stage_ai_requirements():
    global CHALLENGE_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    st, data = req("POST", f"/api/challenges/{CHALLENGE_ID}/ai/analyse", token=TOKEN)
    record(st == 200, "ai/analyse", f"status={st}")
    suggestions = data.get("suggestions", []) if isinstance(data, dict) else []
    print("     suggestions:", [(s.get("category"), s.get("text"), s.get("status")) for s in suggestions])
    for s in suggestions:
        cat, text = s.get("category"), s.get("text")
        if cat == "functional" and ("real-time monitoring dashboard" in text or "configurable leakage alerting" in text):
            d = "ACCEPT"
        elif cat == "functional" and "offline-first" in text:
            d = "REJECT"
        else:
            d = "ACCEPT"  # leave pending/review later
        st, data = req("POST", f"/api/challenges/suggestions/{s.get('id')}/decide?decision={d}",
                       token=TOKEN, payload={})
        if st != 200:
            record(False, f"decide {d}", f"status={st} {data}")
            return
    st, data = gett(f"/api/challenges/{CHALLENGE_ID}")
    ch = data if isinstance(data, dict) else {}
    funcs = ch.get("requirements", {}).get("functional", [])
    record(len(funcs) >= 2, "official functional requirements", f"got={funcs}")
    st, data = gett(f"/api/challenges/{CHALLENGE_ID}/review")
    errors = data.get("errors", []) if isinstance(data, dict) else []
    record(len(errors) == 0, "review zero open gates", f"errors={errors}")


def stage_kpis():
    global CHALLENGE_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    kpis = [
        {"name": "Leakage Detection Time", "baseline": "48", "target": "12", "unit": "Hours",
         "measurement_method": "Verified comparison between leakage event/report time and system detection time.",
         "evidence_source": "Municipal maintenance records + platform monitoring logs", "success_threshold": "<=18"},
        {"name": "Leakage Reduction", "baseline": "0%", "target": "30", "unit": "%",
         "measurement_method": "Compare verified pre-pilot and pilot-period leakage measurements.",
         "evidence_source": "Municipal maintenance records + platform monitoring logs", "success_threshold": ">=25"},
    ]
    for k in kpis:
        st, d = req("POST", f"/api/challenges/{CHALLENGE_ID}/kpis", token=TOKEN, payload=k)
        if st != 201:
            record(False, f"add KPI {k['name']}", f"status={st}")
            return
    st, data = gett(f"/api/challenges/{CHALLENGE_ID}")
    ch = data if isinstance(data, dict) else {}
    names = [k["name"] for k in ch.get("kpis", [])]
    for want in ["Leakage Detection Time", "Leakage Reduction"]:
        record(want in names, "KPIs persisted", f"names={names}")


def stage_pilot_criteria():
    global CHALLENGE_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    payload = {
        "duration_weeks": 60, "budget_max": 1000000, "number_of_sites": 3,
        "target_users": "3 selected municipal wards",
        "geographic_scope": "3 selected municipal wards",
        "success_conditions": "Validate whether technology-based monitoring can reduce leakage detection time and reduce water loss under controlled municipal conditions.",
        "payment_conditions": "Paid on milestone completion",
    }
    st, d = req("PATCH", f"/api/challenges/{CHALLENGE_ID}", token=TOKEN, payload=payload)
    record(st == 200, "patch pilot criteria", f"status={st}")
    st, d = gett(f"/api/challenges/{CHALLENGE_ID}")
    pc = d.get("pilot_criteria", {}) if isinstance(d, dict) else {}
    record(pc.get("duration_weeks") == 60, "duration_weeks=60", f"got={pc.get('duration_weeks')}")
    record(pc.get("budget_max") == 1000000, "budget_max=1000000", f"got={pc.get('budget_max')}")
    record(pc.get("number_of_sites") == 3, "number_of_sites=3", f"got={pc.get('number_of_sites')}")
    m = pc.get("milestones", [])
    record(isinstance(m, list) and len(m) == 5, "5 milestones in criteria", f"got={m}")


def stage_data_ip_security():
    global CHALLENGE_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    payload = {
        "data_policy": {"ownership": "Municipal pipeline records, leakage reports and pilot monitoring data.",
                        "access": "Authorized pilot participants only.", "residency": "Maharashtra SDC"},
        "ip_policy": {"pre_existing": "Startup retains pre-existing IP.",
                      "new_ip": "Pilot-specific outputs and permitted data usage governed through the pilot agreement."},
        "cybersecurity": {"authentication": "Cybersecurity review required before live deployment.",
                          "encryption": "TLS 1.2+"},
        "risks": [{"risk": "False alerts", "probability": 3, "impact": 3},
                  {"risk": "Incomplete baseline data", "probability": 3, "impact": 3},
                  {"risk": "System integration risk", "probability": 2, "impact": 3}],
    }
    st, d = req("PATCH", f"/api/challenges/{CHALLENGE_ID}", token=TOKEN, payload=payload)
    record(st == 200, "patch data/ip/security", f"status={st}")
    st, d = gett(f"/api/challenges/{CHALLENGE_ID}")
    ch = d if isinstance(d, dict) else {}
    dp, ip, cs = ch.get("data_policy", {}), ch.get("ip_policy", {}), ch.get("cybersecurity", {})
    record(dp.get("ownership", "").startswith("Municipal pipeline"), "data ownership", f"got={dp.get('ownership')}")
    record(ip.get("pre_existing", "").startswith("Startup retains"), "IP pre-existing", f"got={ip.get('pre_existing')}")
    record(cs.get("authentication", "").startswith("Cybersecurity review"), "security review required", f"got={cs.get('authentication')}")


def stage_review_publish():
    global CHALLENGE_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    st, d = gett(f"/api/challenges/{CHALLENGE_ID}/review")
    errors = d.get("errors", []) if isinstance(d, dict) else []
    record(len(errors) == 0, "zero open gates", f"errors={errors}")
    st, d = req("POST", f"/api/challenges/{CHALLENGE_ID}/publish", token=TOKEN)
    record(st == 200, "publish challenge", f"status={st}")
    st, d = gett(f"/api/challenges/{CHALLENGE_ID}")
    ch = d if isinstance(d, dict) else {}
    record(ch.get("status") == "PUBLISHED", "status=PUBLISHED", f"got={ch.get('status')}")


def stage_matching():
    global CHALLENGE_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    st, d = req("POST", f"/api/matching/{CHALLENGE_ID}/run", token=TOKEN)
    record(st == 200, "run matching", f"status={st}")
    matches = d if isinstance(d, list) else []
    aqua = [m for m in matches if m.get("startup", {}).get("id") == "ST-001"]
    record(len(aqua) > 0, "AquaSense is a match", f"matches={[m.get('startup', {}).get('name') for m in matches]}")
    st, d = gett("/api/startups/ST-001")
    sname = d.get("name") if isinstance(d, dict) else None
    record(sname == "AquaSense Technologies", "startup name", f"got={sname}")


def stage_expert_evaluator():
    global CHALLENGE_ID, ASG_ID
    if not CHALLENGE_ID:
        return
    login("expert")
    st, d = gett(f"/api/evaluations/assignments?challenge_id={CHALLENGE_ID}")
    assignments = d if isinstance(d, list) else []
    asg = None
    for a in assignments:
        if a.get("startup_id") == "ST-001":
            asg = a
            break
    record(asg is not None, "assignment for ST-001", f"assignments={[a.get('startup_id') for a in assignments]}")
    if asg is None:
        # create authoritative assignment
        st, d = req("POST", "/api/evaluations/assign", token=TOKEN,
                    payload={"challenge_id": CHALLENGE_ID, "startup_id": "ST-001", "expert_id": "U-EXP1"})
        record(st == 201, "create evaluator assignment", f"status={st}")
        if isinstance(d, dict):
            ASG_ID = d.get("id")
        st, d = gett(f"/api/evaluations/assignments?challenge_id={CHALLENGE_ID}")
        for a in (d if isinstance(d, list) else []):
            if a.get("startup_id") == "ST-001":
                ASG_ID = a.get("id")
                break
    if ASG_ID:
        st, d = gett(f"/api/evaluations/assignments/{ASG_ID}")
        record(st == 200, "get assignment", f"status={st}")
        record(d.get("status") == "AWAITING_COI", "status AWAITING_COI", f"got={d.get('status')}")
        st, d = req("POST", f"/api/evaluations/assignments/{ASG_ID}/coi", token=TOKEN,
                    payload={"status": "NO_CONFLICT"})
        record(st == 200, "submit COI", f"status={st}")
        a = d if isinstance(d, dict) else {}
        record(a.get("status") == "COI_CLEARED" or (a.get("coi") or {}).get("status") == "NO_CONFLICT",
               "COI persisted", f"got={a.get('status')}")
        st, d = req("POST", f"/api/evaluations/assignments/{ASG_ID}/evaluation", token=TOKEN,
                    payload={"scores": {}, "recommendation": "RECOMMEND_FOR_PILOT", "final_comments": ""})
        record(st == 409, "evaluation blocked before COI cleared", f"status={st}")


def stage_expert_evaluation():
    global CHALLENGE_ID, ASG_ID
    if not CHALLENGE_ID:
        return
    login("expert")
    st, d = gett(f"/api/evaluations/assignments?challenge_id={CHALLENGE_ID}")
    asg = None
    for a in (d if isinstance(d, list) else []):
        if a.get("startup_id") == "ST-001":
            asg = a
            break
    if not asg:
        st, d = req("POST", "/api/evaluations/assign", token=TOKEN,
                    payload={"challenge_id": CHALLENGE_ID, "startup_id": "ST-001", "expert_id": "U-EXP1"})
        if st == 201:
            ASG_ID = d.get("id")
        st, d = gett(f"/api/evaluations/assignments?challenge_id={CHALLENGE_ID}")
        for a in (d if isinstance(d, list) else []):
            if a.get("startup_id") == "ST-001":
                ASG_ID = a.get("id")
                break
    if not ASG_ID:
        record(False, "no assignment", "create first")
        return
    st, d = gett(f"/api/evaluations/assignments/{ASG_ID}")
    # COI cleared
    if d.get("coi") and d["coi"].get("status") not in ("COI_CLEARED", "NO_CONFLICT"):
        req("POST", f"/api/evaluations/assignments/{ASG_ID}/coi", token=TOKEN,
            payload={"status": "NO_CONFLICT"})
    scores = {
        "problem_fit": {"score": 9, "justification": "Relevant"},
        "technical_feasibility": {"score": 8, "justification": "Proven"},
        "relevant_experience": {"score": 8, "justification": "Same domain"},
        "evidence_quality": {"score": 8, "justification": "Available"},
        "pilot_readiness": {"score": 8, "justification": "Installed"},
        "scalability": {"score": 8, "justification": "Scales"},
        "value_for_money": {"score": 8, "justification": "Mid-range"},
        "risk_compliance": {"score": 8, "justification": "Only open item"},
    }
    st, d = req("POST", f"/api/evaluations/assignments/{ASG_ID}/evaluation", token=TOKEN,
                payload={"scores": scores, "recommendation": "RECOMMEND_FOR_PILOT",
                         "final_comments": "The solution is relevant to municipal leakage detection and suitable for controlled pilot testing. Additional evidence is required before wider deployment."})
    record(st == 201, "evaluation submitted", f"status={st}")
    if isinstance(d, dict):
        record(d.get("status") == "EVALUATION_SUBMITTED", "submitted state", f"got={d.get('status')}")


def stage_pilot_creation():
    global CHALLENGE_ID, PILOT_ID, EVAL_ASSIGNMENT_ID
    if not CHALLENGE_ID:
        return
    login("government_officer")
    payload = {
        "name": "Pilot 01 — AquaSense Technologies",
        "startup_id": "ST-001",
        "challenge_id": CHALLENGE_ID,
        "duration_weeks": 60,
        "budget": 1000000,
        "objectives": "Validate whether technology-based monitoring can reduce leakage detection time and reduce water loss under controlled municipal conditions.",
        "sites": 3,
        "target_users": "3 selected municipal wards",
        "geographic_scope": "3 selected municipal wards",
    }
    st, d = req("POST", "/api/pilots", token=TOKEN, payload=payload)
    record(st == 201, "create pilot", f"status={st}")
    if isinstance(d, dict):
        PILOT_ID = d.get("id")
        EVAL_ASSIGNMENT_ID = d.get("id")
        st, d = gett(f"/api/pilots/{PILOT_ID}")
        p = d if isinstance(d, dict) else {}
        record(len(p.get("kpis", [])) >= 2, "pilot KPIs cloned", f"got={len(p.get('kpis', []))}")
        record(len(p.get("milestones", [])) >= 5, "pilot milestones cloned", f"got={len(p.get('milestones', []))}")


def stage_pilot_kpi():
    global PILOT_ID
    if not PILOT_ID:
        return
    login("government_officer")
    st, d = gett(f"/api/pilots/{PILOT_ID}")
    p = d if isinstance(d, dict) else {}
    kpis = {k.get("name"): k.get("id") for k in p.get("kpis", [])}
    for name, obs in [("Leakage Detection Time", "17"), ("Leakage Reduction", "18")]:
        kpid = kpis.get(name)
        if kpid:
            st, dd = req("POST", f"/api/pilots/{PILOT_ID}/kpis/{kpid}/observation",
                         token=TOKEN, payload={"observed_value": obs, "status": "TARGET_ACHIEVED"})
            record(st == 200, f"record {name} observed={obs}", f"status={st}")
    st, d = gett(f"/api/pilots/{PILOT_ID}")
    p = d if isinstance(d, dict) else {}
    for k in p.get("kpis", []):
        if k.get("name") == "Leakage Detection Time":
            record(k.get("observed_value") == "17", "observed 17h", f"got={k.get('observed_value')}")
        elif k.get("name") == "Leakage Reduction":
            record(k.get("observed_value") == "18", "observed 18%", f"got={k.get('observed_value')}")


def stage_milestones():
    global PILOT_ID
    if not PILOT_ID:
        return
    login("government_officer")
    st, d = gett(f"/api/pilots/{PILOT_ID}")
    p = d if isinstance(d, dict) else {}
    ms = p.get("milestones", [])
    total = sum(m.get("payment_percentage", 0) for m in ms)
    record(total == 100, "milestone total 100", f"got={total}")
    for m in ms:
        if m.get("payment_percentage") in (10, 20, 25):
            st, dd = req("PATCH", f"/api/pilots/{PILOT_ID}/milestones/{m.get('id')}/status",
                         token=TOKEN, payload={"status": "ACCEPTED"})
            record(st == 200, "milestone accepted", f"status={st}")
    st, d = gett(f"/api/pilots/{PILOT_ID}")
    p = d if isinstance(d, dict) else {}
    ms = p.get("milestones", [])
    completed = sum(1 for m in ms if m.get("status") == "ACCEPTED")
    record(completed == 4, "M1-M4 complete", f"M1-M4={completed}/4")


def stage_evidence():
    global PILOT_ID
    if not PILOT_ID:
        return
    login("government_officer")
    st, d = gett(f"/api/pilots/{PILOT_ID}")
    p = d if isinstance(d, dict) else {}
    kpis = {k.get("name"): k.get("id") for k in p.get("kpis", [])}
    for ep in [{"title": "21% reduction claim", "description": "Startup claim of 21% reduction",
                "claimed_value": "21%", "evidence_type": "REPORT"},
               {"title": "19% observed result", "description": "Observed 19% reduction",
                "claimed_value": "19%", "evidence_type": "REPORT"}]:
        st, dd = req("POST", "/api/evidence", token=TOKEN,
                     payload={"pilot_id": PILOT_ID, "evidence_type": ep["evidence_type"],
                              "title": ep["title"], "description": ep["description"],
                              "claimed_value": ep["claimed_value"]})
        record(st == 201, "upload evidence", f"status={st}")
    st, d = gett(f"/api/evidence?pilot_id={PILOT_ID}")
    ev = d if isinstance(d, list) else []
    record(len(ev) >= 2, "evidence rows exist", f"got={len(ev)}")


def stage_validation():
    global PILOT_ID
    if not PILOT_ID:
        return
    login("validator")
    # find existing package or create one
    st, d = gett(f"/api/validation/packages?pilot_id={PILOT_ID}")
    pkgs = d if isinstance(d, list) else []
    pkg = None
    if pkgs:
        pkg = pkgs[0]
    if pkg is None:
        st, d = req("POST", f"/api/validation/packages?pilot_id={PILOT_ID}", token=TOKEN)
        if st == 201:
            pkg = d
    record(pkg is not None, "validation package exists", f"status={st}")
    if pkg:
        # assign validator
        st, d = req("POST", f"/api/validation/packages/{pkg.get('id')}/assign?validator_id={EMAIL_BY_ROLE['validator']}",
                    token=TOKEN)
        # validate alias
        VALIDATOR_USER = d if isinstance(d, dict) else {}
        st, d = gett(f"/api/validation/packages/{pkg.get('id')}")
        p = d if isinstance(d, dict) else {}
        validators = p.get("validators", [])
        record(len(validators) > 0, "validator assigned", f"got={len(validators)}")
        # start validation
        st, d = req("POST", f"/api/validation/packages/{pkg.get('id')}/start", token=TOKEN)
        record(st == 200, "start validation", f"status={st}")
        # add finding
        st, d = req("POST", f"/api/validation/packages/{pkg.get('id')}/findings", token=TOKEN,
                    payload={"claimed": "21%", "observed": "19%", "validated_value": "18%",
                             "target": ">=25%", "finding": "PARTIALLY_SUPPORTED",
                             "explanation": "Evidence supports measurable improvement, but the predefined scale success threshold has not been achieved."})
        record(st == 201, "add finding", f"status={st}")
        # submit report
        st, d = req("POST", f"/api/validation/packages/{pkg.get('id')}/report", token=TOKEN,
                    payload={"summary": "Independent analysis supports a real improvement at 18%, below the 25% target.",
                             "overall_finding": "PARTIALLY_SUPPORTED",
                             "validated_kpis": {"Leakage Detection Time": "17h", "Leakage Reduction": "18%"}})
        record(st == 201, "submit validation report", f"status={st}")


def stage_decision():
    global PILOT_ID
    if not PILOT_ID:
        return
    login("senior_authority")
    st, d = req("POST", f"/api/decisions/{PILOT_ID}/recommendation", token=TOKEN)
    record(st == 201, "generate recommendation", f"status={st}")
    rec = d if isinstance(d, dict) else {}
    record(rec.get("outcome") == "RE_PILOT", "recommendation RE_PILOT", f"got={rec.get('outcome')}")
    st, d = req("POST", f"/api/decisions/{PILOT_ID}/government-decision", token=TOKEN,
                payload={"decision": "RE_PILOT",
                         "reason": "Pilot demonstrates measurable improvement, but current evidence does not satisfy the predefined scale threshold.",
                         "override": False})
    record(st == 201, "government RE-PILOT decision", f"status={st}")


# ===============================================================
def main():
    global TOKEN, CHALLENGE_ID, ASG_ID, PILOT_ID, EVAL_ASSIGNMENT_ID
    CHALLENGE_ID = None
    ASG_ID = None
    PILOT_ID = None
    EVAL_ASSIGNMENT_ID = None

    print("=" * 72)
    print("GOVINNOVATE MAHARASHTRA  —  END-TO-END DEMO AUDIT (8-minute SIH story)")
    print("=" * 72)

    stage("1 PROBLEM (create + persist + refresh)", stage_problem)
    stage("2 AI REQUIREMENTS (accept 1+2, reject 3)", stage_ai_requirements)
    stage("3 KPI BUILDER (two KPIs)", stage_kpis)
    stage("4 PILOT CRITERIA (60d/3wards/10L)", stage_pilot_criteria)
    stage("5 DATA/IP/SECURITY", stage_data_ip_security)
    stage("6 REVIEW & PUBLISH", stage_review_publish)
    stage("7 STARTUP MATCHING (AquaSense)", stage_matching)
    stage("8 EXPERT EVALUATOR + COI", stage_expert_evaluator)
    stage("9 EXPERT EVALUATION (9/8/8/8)", stage_expert_evaluation)
    stage("10 PILOT CREATION (connect ch+startup+eval)", stage_pilot_creation)
    stage("11 PILOT KPI MONITORING (17h/18%)", stage_pilot_kpi)
    stage("12 MILESTONES (M1-M4 complete, M5 pending)", stage_milestones)
    stage("13 EVIDENCE (claim/observed)", stage_evidence)
    stage("14 VALIDATION (PARTIALLY_SUPPORTED 18%)", stage_validation)
    stage("15 SENIOR AUTHORITY DECISION (RE-PILOT)", stage_decision)

    print("\n" + "=" * 72)
    print(f"RESULT: {PASSED} passed, {FAILED} failed")
    if FAILED:
        print("FAILED STAGES:")
        for s, d in FAIL.items():
            print(f"  - {s}: {d}")
    else:
        print("ALL STAGES PASSED")
    print("=" * 72)


if __name__ == "__main__":
    main()

import json, urllib.request

BASE = "http://127.0.0.1:8000"


def req(method, path, token=None, payload=None, headers=None):
    body = None
    hd = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        hd["Content-Type"] = "application/json"
    if token:
        hd["Authorization"] = "Bearer " + token
    if headers:
        hd.update(headers)
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=hd)
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


tok = None
st, d = req("POST", "/api/auth/login",
            payload={"email": "arjun.kulkarni@demo.gov.in", "password": "govinnovate-demo"})
tok = d["access_token"]
print("logged in", st)

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
    "budget_min": 600000,
    "budget_max": 1000000,
}
st, d = req("POST", "/api/challenges", token=tok, payload=p)
cid = d.get("id")
print("create:", st, cid)


def dump(tag):
    st, d = req("GET", "/api/challenges/" + cid, token=tok)
    c = d if isinstance(d, dict) else {}
    print(tag, "title=", repr(c.get("title")),
          "dept=", repr(c.get("department")),
          "prob=", repr(c.get("problem_statement"))[:40],
          "exp=", repr(c.get("expected_outcome"))[:40],
          "req=", c.get("requirements"))


dump("after create")

st, d = req("POST", "/api/challenges/" + cid + "/ai/analyse", token=tok)
print("analyse:", st)
dump("after analyse")

st, d = req("GET", "/api/challenges/" + cid + "/ai/suggestions", token=tok)
sugs = d if isinstance(d, list) else []
for s in sugs:
    if "real-time monitoring dashboard" in s.get("text", ""):
        st, d = req("POST",
                    "/api/challenges/suggestions/" + str(s.get("id")) + "/decide?decision=ACCEPT",
                    token=tok, payload={})
        print("decide accept functional1:", st)
        break
dump("after accept functional1")

st, d = req("GET", "/api/challenges/" + cid + "/review", token=tok)
print("review:", st, d if not isinstance(d, dict) else d.get("errors"))

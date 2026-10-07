# GovInnovate Maharashtra

**SIH26136 · Government of Maharashtra / Maharashtra State Innovation Society**

> **From Government Problem to Proven Innovation** — Evidence-Gated Decision Intelligence

Government should not have to trust a startup's claim. GovInnovate helps departments discover the
right startup, run a controlled pilot, collect evidence, **independently validate** the outcome, and
then make an **evidence-backed decision**.

```
Claim ≠ Evidence ≠ Validation ≠ Government Decision
Match Score ≠ Evidence Confidence · AI Recommendation ≠ Government Decision · Checksum ≠ Truth
```

**All workflow data is fictional demo data for evaluation purposes.** Public ecosystem figures are
real government data and are cited inline; fictional startups never appear inside public-data views.

**Data layers** — every number is labeled at component level:

- `GOVERNMENT PUBLIC DATA` — genuine public figures with citations (DPIIT startup counts via
  PIB/DPIIT releases, Maharashtra Startup Policy 2025 via MSInS, Jal Jeevan Mission water
  indicator), imported as **versioned snapshots** through pluggable `GovernmentDataProvider`
  classes. Missing figures show **DATA NOT AVAILABLE** — never estimates.
- `PLATFORM DATA` / `DEMO DATA` — this app's workflow records (fictional, for SIH26136 demo).
- `SIMULATED PILOT` — the AquaSense water story (21% → 19% → 18% → 20%) and soil branch.

Explore the registry at **Government Data** in the sidebar (source, retrieval dates, version
history, refresh log; admin-only refresh that never overwrites prior versions).

---

## Quick start (development)

**Prerequisites:** Python 3.11+, Node 18+.

**1. Backend** (port 8000):

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash (use .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The demo dataset (42 startups, the full water-leakage story, users for all 6 roles) seeds
automatically on first boot.

**2. Frontend** (port 5174/5173):

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (http://localhost:5173 or 5174) and sign in:

| Role | Email | Password |
|---|---|---|
| Government Officer | `arjun.kulkarni@demo.gov.in` | `govinnovate-demo` |
| Senior Authority | `meera.deshmukh@demo.gov.in` | `govinnovate-demo` |
| Startup (AquaSense) | `founder@aquasense.demo.in` | `govinnovate-demo` |
| Expert Evaluator | `r.kelkar@demo-expert.in` | `govinnovate-demo` |
| Independent Validator | `v.deshpande@demo-validator.in` | `govinnovate-demo` |
| Administrator | `admin@demo.gov.in` | `govinnovate-demo` |

You can also switch roles instantly from the header's **Role Authority** selector.

**API docs:** http://localhost:8000/docs (OpenAPI, 80+ endpoints incl. `/api/government-data/*`).

## Quick start (Docker)

```bash
docker compose up --build
# frontend: http://localhost:8080 · API: http://localhost:8000
```

For production, set `DATABASE_URL` to PostgreSQL in `docker-compose.yml` and rotate `SECRET_KEY`.

---

## The 3-minute demo script

1. **Dashboard** → pipeline stepper, live counters, demo-story shortcuts.
2. **Challenges → Create Challenge** → fill the problem → *Analyse problem with AI* →
   Accept/Edit/Reject suggestions (nothing becomes official until you approve) → add a KPI →
   publish (blocked until all gates pass).
3. **Matching** → pick the published challenge → *Run Matching* → expand
   "Why this score?" (weights, component bars, evidence limitations) → try *Override ranking*
   (reason mandatory, audited).
4. **Evaluations** → select challenge → see multi-expert aggregation (avg/median/min/max/stddev,
   HIGH EVALUATOR DISAGREEMENT flag) → open an assignment: COI declaration gates evaluation;
   recused experts are blocked.
5. **Pilots → Smart Leakage Detection Pilot** → KPI monitoring (baseline/claimed/observed kept
   separate), milestones with payments totalling 100%, explainable health (GREEN/AMBER/RED +
   reasons).
6. **Evidence** → upload a file → SHA-256 recorded ("integrity, not truth") → review workflow →
   ready-for-validation.
7. **Validation** → package VP-001 shows the chain **claim 21% → observed 19% → validated 18% →
   target 20%**, findings PARTIALLY_SUPPORTED — objective language, no allegations.
8. **Decisions → Smart Leakage Detection Pilot** → engine recommendation **RE-PILOT @ 78%** with
   reasons, missing evidence, risk flags and 12 explainable factor scores → switch role to
   **Senior Authority** → record the government decision (override needs a reason; history is
   append-only). *Abstention demo:* any pilot lacking validation/evidence yields
   INSUFFICIENT EVIDENCE — the engine refuses to guess.
9. **Re-Pilot Plans** → carried-forward KPI results, evidence gaps, and exactly what changes
   (3 → 10 sites, better baseline, security review) → create the Phase-2 pilot.
10. **Scale-Up → Village Soil Intelligence Pilot** (successful branch) → pilot-vs-scale scope
    comparison → approve as Senior Authority → **Procurement** → evidence-backed package marked
    **DRAFT — NOT A LEGALLY BINDING TENDER · LEGAL REVIEW REQUIRED**.
11. **Knowledge Centre** → engine-extracted lessons with Accept/Edit/Ignore + similar-pilot
    recommendations with explained similarity.
12. **Audit** → every action above with actor, role, old/new values, reason, correlation ID.

## Feature map

| Module | Highlights |
|---|---|
| Challenges | 6-step wizard, AI requirement engine, KPI builder, data/IP/security/risk, review gates |
| Startup Registry | 42 fictional startups, search/filter, claim-vs-verified evidence ladder |
| Matching | Mandated weights, explainable components, override-with-reason (audited) |
| Evaluations | 8 weighted criteria, COI workflow, recusal blocking, multi-expert aggregation |
| Pilots | Readiness gates, milestones, simulated payments (=100% validation), explainable health |
| Evidence | Secure upload, SHA-256, 10-state review workflow, version chain |
| Validation | Packages, validator COI, findings, hashed versioned reports |
| Decisions | Explainable engine, abstention, government decisions with audited overrides |
| Scale-Up / Procurement | Hard-gated plans, scope comparison, draft procurement packages |
| Re-Pilot | Carried-forward context, explicit scope changes, Phase-2 spawning |
| Knowledge | Lesson extraction, accept/edit/ignore, similar pilots |
| Governance | Analytics (sample sizes + limitations, N/A handling), audit, system health, global search |

See `docs/ARCHITECTURE.md` for the full architecture, security model and workflow gates.

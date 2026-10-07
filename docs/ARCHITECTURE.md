# GovInnovate Maharashtra — Architecture

**SIH26136 · Government of Maharashtra / Maharashtra State Innovation Society**
*From Government Problem to Proven Innovation — Evidence-Gated Decision Intelligence*

## 1. Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind CSS + Recharts | Stitch design tokens (Secretariat Navy / Ashoka Gold / Evidence Emerald) |
| Backend | FastAPI + Pydantic v2 | OpenAPI docs at `/docs` |
| ORM | SQLAlchemy 2.0 | Normalized models, JSON columns where appropriate |
| Database | SQLite (demo) / PostgreSQL (production) | `DATABASE_URL` env switch |
| Auth | JWT (python-jose) + bcrypt | Demo role switcher issues real tokens |
| AI | Rule-based engines | Deterministic, explainable, versioned, replaceable |

## 2. Layout

```
govinnovate/
├── backend/
│   ├── app/
│   │   ├── core/        config, database, security (JWT+RBAC), deps (authZ)
│   │   ├── models/      users, challenges, startups, evaluations, pilots,
│   │   │                evidence, decisions (all normalized)
│   │   ├── engines/     AIRequirementEngine, MatchingEngine, DecisionEngine,
│   │   │                KnowledgeEngine (+ evaluation stats)
│   │   ├── routers/     auth, challenges, startups, matching, evaluations,
│   │   │                pilots, evidence, validation, decisions, scaleup,
│   │   │                procurement, repilots, knowledge, analytics, audit,
│   │   │                system, search, demo
│   │   ├── schemas/     Pydantic request/response models
│   │   └── services/    audit, seed (demo data), demo shortcuts, bootstrap
│   ├── uploads/         evidence storage (SHA-256 names)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/  Shell (top strip + header + sidebar), ui kit
│       ├── pages/       24 route pages across the full workflow
│       ├── services/    api.js (typed fetch layer, auth handling)
│       └── lib/         status→badge tone map, formatters
├── docker-compose.yml
└── docs/ARCHITECTURE.md
```

## 3. Core workflow (all server-enforced)

```
Challenge → AI Requirements (accept/edit/reject) → KPIs → Publish (gates)
  → Matching (explainable, override w/ reason) → Expert Evaluation (COI-gated,
  versioned, disagreement surfaced) → Pilot (readiness gates, milestones,
  payments = 100%) → Evidence (SHA-256, review workflow, versions)
  → Validation (package → validator + COI → findings → report)
  → Decision Intelligence (abstains if evidence insufficient)
  → Government Decision (override requires reason; append-only history)
  → SCALE → Scale-Up plan → Approval → Procurement package (DRAFT, legal review)
  → RE-PILOT → Re-pilot plan → Phase-2 pilot
  → Knowledge extraction (accept/edit/ignore lessons)
```

## 4. Product rules enforced in code

| Rule | Where |
|---|---|
| Claim ≠ Evidence | `pilot_kpis.claimed_value` vs `observed_value` stored separately; startups may only write claims |
| Evidence ≠ Validation | Evidence review (`EVIDENCE_REVIEW`) and validation (`VALIDATION_SUBMIT`) are separate permissions |
| Validation ≠ Government Decision | `GovernmentDecision` table separate from `ValidationReport`; different role permissions |
| Match Score ≠ Evidence Confidence | Separate columns on `startup_matches` |
| AI Recommendation ≠ Government Decision | `DecisionRecommendation` never mutates `GovernmentDecision`; decisions recorded only by senior authority |
| Checksum ≠ Truth | SHA-256 stored with explicit integrity-not-truth notices in API payloads and UI |
| Insufficient Evidence is valid | `decision_engine.evaluate` returns abstention instead of guessing |

## 5. Workflow gates (server-side)

- Publish: title/department/problem/outcome + ≥1 accepted functional requirement + ≥1 KPI + pilot duration/budget + data ownership + security auth requirement.
- Pilot start: milestone payment percentages must total exactly 100%.
- Milestone payments: only after ACCEPTED status; transitions validated per state machine.
- Evaluation: only after COI cleared; recused experts blocked (403); low scores need justification.
- Validation: package must contain reviewed evidence; validator must be assigned with cleared COI; report needs ≥1 finding.
- Decision: engine abstains without measurable KPIs + completed validation + validated baseline + adequate evidence coverage.
- Scale-up: only after government SCALE decision (409 otherwise).
- Procurement: only after APPROVED scale-up plan.
- Re-pilot plan: only after government RE_PILOT decision.

## 6. Security

- JWT bearer auth; every router (except health/login/roles/openapi) requires `get_current_user`.
- RBAC matrix in `core/security.py` (30 permission codes across 6 roles); enforced via `Depends(require(...))`.
- Object-level checks: startups access only their own pilots/evidence; experts only their own assignments; validators only their packages.
- Status-transition state machines on pilot, milestone, payment, and evidence statuses.
- Upload validation: extension whitelist, 10MB cap, MIME recorded, SHA-256 checksum, sanitized storage name.
- Append-only audit log with actor, role, action, entity, old/new values, reason, correlation ID.

## 7. AI engines (replaceable)

Each engine is a small class with a stable interface and a version string stamped into every output:

- `AIRequirementEngine.generate(problem) → {category, suggestions[]}` — keyword-rules + templates.
- `MatchingEngine.score_startup(startup, challenge) → {match_score, components, explanations, evidence_confidence}` — mandated weights 25/20/15/15/10/10/5.
- `evaluate(pilot, kpis, validation, milestones, evidence) → {outcome, confidence, reasons, factors}` — hard abstention gates.
- `KnowledgeEngine.extract_lessons(...) / similar_pilots(...)` — rule-based, PENDING until officer decision.

Swapping in an LLM service means implementing the same interface; no router changes required.

## 8. Demo data

`app/services/seed.py` seeds on first boot (idempotent): 9 users across all roles, 5 departments,
42 fictional startups (marked DEMO), the full water-leakage story (challenge CH-WTR-001 → pilot
P-WTR-001 with claim 21% / observed 19% / validated 18% → RE-PILOT decision + plan), and the
successful branch (soil pilot P-AGR-001 → SCALE → approved plan → procurement package). All demo
passwords: `govinnovate-demo`.

## 9. Running

Development: see README.md. Docker: `docker compose up --build` (frontend on :8080, API on :8000).

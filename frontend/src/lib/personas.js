/**
 * Central persona configuration — ONE platform, five role-based views.
 *
 * The backend (app/core/security.py PERMISSIONS matrix) remains the single
 * source of truth for authorization: every API re-checks server-side. This
 * module MIRRORS that matrix so the UI can hide forbidden actions, filter the
 * sidebar and guard routes — it never grants anything the backend denies.
 *
 * All personas read from the same backend records; nothing here duplicates data.
 */

// --- Permission matrix (mirror of backend app/core/security.py) -------------
export const PERMS = {
  CHALLENGE_CREATE: ['government_officer', 'administrator'],
  CHALLENGE_EDIT: ['government_officer', 'administrator'],
  CHALLENGE_PUBLISH: ['government_officer', 'administrator'],
  AI_ANALYSE: ['government_officer', 'administrator'],
  AI_SUGGESTION_DECIDE: ['government_officer', 'administrator'],
  MATCH_RUN: ['government_officer', 'administrator'],
  MATCH_OVERRIDE: ['government_officer', 'administrator'],
  EVALUATION_SUBMIT: ['expert'],
  COI_DECLARE: ['expert', 'validator'],
  EVALUATION_ASSIGN: ['government_officer', 'administrator'],
  SHORTLIST_DECISION: ['government_officer', 'administrator'],
  PILOT_CREATE: ['government_officer', 'administrator'],
  PILOT_APPROVE: ['government_officer', 'administrator'],
  PILOT_TRANSITION: ['government_officer', 'administrator', 'startup'],
  MILESTONE_UPDATE: ['government_officer', 'administrator', 'startup'],
  EVIDENCE_SUBMIT: ['startup', 'government_officer', 'administrator'],
  EVIDENCE_REVIEW: ['government_officer', 'administrator'],
  EVIDENCE_OBSERVE: ['government_officer', 'administrator', 'validator'],
  VALIDATION_ASSIGN: ['government_officer', 'administrator'],
  VALIDATION_SUBMIT: ['validator'],
  DECISION_REQUEST: ['government_officer', 'administrator'],
  GOVERNMENT_DECISION: ['senior_authority', 'administrator'],
  SCALE_PLAN: ['government_officer', 'administrator'],
  SCALE_APPROVE: ['senior_authority', 'administrator'],
  PROCUREMENT_GENERATE: ['government_officer', 'administrator'],
  REPILOT_PLAN: ['government_officer', 'administrator'],
  KNOWLEDGE_DECIDE: ['government_officer', 'administrator'],
  USER_MANAGE: ['administrator'],
  DEMO_SEED: ['administrator', 'government_officer'],
  AUDIT_VIEW: ['government_officer', 'senior_authority', 'administrator'],
  SYSTEM_HEALTH: ['administrator', 'government_officer'],
};

/** Frontend mirror of backend `can()` — UI convenience only. */
export function can(role, permission) {
  return (PERMS[permission] || []).includes(role);
}

/** Conditional action renderer: hides controls the persona may not use. */
export function Can({ role, perm, anyOf, children }) {
  const ok = anyOf ? anyOf.some((p) => can(role, p)) : can(role, perm);
  return ok ? children : null;
}

// --- Role-scoped navigation (reuses existing routes, icons and labels) ------
const ALL = ['government_officer', 'senior_authority', 'startup', 'expert', 'validator', 'administrator'];

const NAV_GROUPS = [
  { group: 'Overview', roles: ALL, items: [['/dashboard', 'Dashboard', '▦']] },
  {
    group: 'Challenge & Discovery', roles: ALL,
    items: [
      ['/challenges', 'Challenges', '⚐'],
      ['/startups', 'Startups', '◎', null, ['government_officer', 'senior_authority', 'expert', 'administrator']],
      ['/matching', 'Matching', '⇄', null, ['government_officer', 'administrator']],
    ],
  },
  {
    group: 'Evaluation', roles: ['government_officer', 'expert', 'administrator'],
    items: [
      ['/evaluations', 'Assigned Evaluations', '✔', 'Your expert review queue · evaluations', ['expert']],
      ['/evaluations', 'Evaluations', '✔', 'Expert assignments & aggregates · evaluations', ['government_officer', 'administrator']],
      ['/evaluations', 'Conflict of Interest', '§', 'COI workflow · inside Evaluations', ['expert', 'validator', 'government_officer', 'administrator']],
    ],
  },
  {
    group: 'My Pilots', roles: ['startup'],
    items: [
      ['/pilots', 'My Pilots', '◈', 'Pilots for your startup (records only you can access)'],
      ['/pilots/:id/milestones', 'Milestones', '◫', 'Milestones & payments · inside Pilot Records'],
      ['/evidence', 'Evidence Submission', '▤', 'Submit evidence against your pilot KPIs'],
    ],
  },
  {
    group: 'Pilot Management', roles: ['government_officer', 'senior_authority', 'administrator'],
    items: [
      ['/pilots', 'Pilots', '◈'],
      ['/pilots/:id/kpis', 'KPIs', '≔', 'Pilot KPIs · inside Pilot Records'],
      ['/pilots/:id/milestones', 'Milestones', '◫', 'Milestones & payments · inside Pilot Records'],
    ],
  },
  {
    group: 'Evidence & Validation', roles: ['government_officer', 'senior_authority', 'validator', 'administrator'],
    items: [
      ['/evidence', 'Evidence', '▤', null, ['government_officer', 'senior_authority', 'administrator']],
      ['/evidence', 'Evidence Review', '▤', 'Read-only evidence for validation context', ['validator']],
      ['/validation', 'Validation Assignments', '✓', 'Your assigned validation packages', ['validator']],
      ['/validation', 'Validation', '✓', null, ['government_officer', 'senior_authority', 'administrator']],
    ],
  },
  {
    group: 'Decision', roles: ['government_officer', 'senior_authority', 'administrator'],
    items: [
      ['/decisions', 'Decisions', '⚖'],
      ['/scaleup', 'Scale-Up', '↥'],
      ['/repilots', 'Re-Pilot', '↻'],
    ],
  },
  {
    group: 'Procurement', roles: ['government_officer', 'administrator'],
    items: [['/procurement', 'Procurement Preparation', '❑']],
  },
  { group: 'Knowledge', roles: ALL, items: [['/knowledge', 'Knowledge Centre', '✦']] },
  {
    group: 'Government Intelligence', roles: ['government_officer', 'senior_authority', 'administrator'],
    items: [
      ['/analytics', 'Analytics', '▥'],
      ['/govdata', 'Government Data', '⛁'],
      ['/audit', 'Audit', '≡', null, ['government_officer', 'senior_authority', 'administrator']],
      ['/system', 'System Health', '⚙', null, ['administrator', 'government_officer']],
    ],
  },
];

/** Sidebar groups/items for a role. Existing Shell styling is unchanged. */
export function navFor(role) {
  return NAV_GROUPS
    .filter((g) => g.roles.includes(role))
    .map((g) => ({
      group: g.group,
      items: g.items.filter((it) => !it[4] || it[4].includes(role))
        .map(([to, text, icon, title]) => ({ to, text, icon, title })),
    }))
    .filter((g) => g.items.length > 0);
}

// --- Route guards ------------------------------------------------------------
// First matching prefix wins. 'startup' pilots/evidence are additionally
// object-scoped by the backend (own records only).
const ROUTE_RULES = [
  ['/challenges/new', ['government_officer', 'administrator']],
  ['/matching', ['government_officer', 'administrator']],
  ['/startups', ['government_officer', 'senior_authority', 'expert', 'administrator']],
  ['/evaluations', ['government_officer', 'expert', 'administrator']],
  ['/validation', ['government_officer', 'validator', 'administrator']],
  ['/decisions', ['government_officer', 'senior_authority', 'administrator']],
  ['/scaleup', ['government_officer', 'senior_authority', 'administrator']],
  ['/repilots', ['government_officer', 'senior_authority', 'administrator']],
  ['/procurement', ['government_officer', 'administrator']],
  ['/analytics', ['government_officer', 'senior_authority', 'administrator']],
  ['/audit', ['government_officer', 'senior_authority', 'administrator']],
  ['/system', ['administrator', 'government_officer']],
  // Open to all personas (backend scopes startup rows to their own records):
  ['/challenges', ALL],
  ['/pilots', ALL],
  ['/evidence', ALL],
  ['/knowledge', ALL],
  ['/govdata', ALL],
];

/** Roles allowed on a path, or null when the path is unguarded. */
export function rolesForPath(path) {
  const rule = ROUTE_RULES.find(([prefix]) => path === prefix || path.startsWith(prefix + '/'));
  return rule ? rule[1] : null;
}

// --- Persona metadata (labels mirror backend ROLE_LABELS) --------------------
export const PERSONA_META = {
  government_officer: { label: 'Government Officer', tagline: 'Department decision-maker' },
  senior_authority: { label: 'Senior Government Authority', tagline: 'Final approval authority' },
  startup: { label: 'Startup', tagline: 'Solution provider · pilot participant' },
  expert: { label: 'Expert Evaluator', tagline: 'Independent technical reviewer' },
  validator: { label: 'Independent Validator', tagline: 'Independent evidence reviewer' },
  administrator: { label: 'Administrator', tagline: 'Platform administration' },
};

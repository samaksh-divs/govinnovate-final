export const inr = (n) =>
  n === null || n === undefined || n === '' ? '—'
    : '₹' + Number(n).toLocaleString('en-IN');

export const dt = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? String(iso) : d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
};

export const d = (iso) => {
  if (!iso) return '—';
  const x = new Date(iso);
  return isNaN(x) ? String(iso) : x.toLocaleDateString('en-IN', { dateStyle: 'medium' });
};

/** Single source of truth for status → badge tone. */
export const TONES = {
  // generic workflow
  DRAFT: 'gray', PUBLISHED: 'green', CLOSED: 'gray', ARCHIVED: 'gray', IN_REVIEW: 'amber',
  APPROVED: 'green', REJECTED: 'red', PENDING: 'amber', ACCEPTED: 'green', EDITED: 'blue',
  IGNORED: 'gray',
  // eligibility
  ELIGIBLE: 'green', PARTIALLY_ELIGIBLE: 'amber', INCOMPLETE: 'red', NOT_ELIGIBLE: 'red',
  // pilot / health
  GREEN: 'green', AMBER: 'amber', RED: 'red', 'N/A': 'gray',
  NOT_STARTED: 'gray', BASELINE_PENDING: 'amber', BASELINE_VALIDATED: 'blue', IN_PROGRESS: 'blue',
  TARGET_ON_TRACK: 'green', AT_RISK: 'amber', TARGET_ACHIEVED: 'green', TARGET_NOT_ACHIEVED: 'red',
  INSUFFICIENT_DATA: 'gray',
  // pilot lifecycle
  PENDING_APPROVAL: 'amber', READY_TO_START: 'blue', ACTIVE: 'blue', CONCLUDED: 'gray',
  DECIDED: 'navy', SCALED: 'green', RE_PILOT: 'amber',
  // evidence
  UPLOADED: 'gray', UNDER_REVIEW: 'amber', ACCEPTED_FOR_MONITORING: 'blue',
  READY_FOR_VALIDATION: 'blue', VALIDATED: 'green', NEEDS_CLARIFICATION: 'amber',
  PARTIALLY_VALIDATED: 'amber', NOT_VALIDATED: 'red', INSUFFICIENT_EVIDENCE: 'gray',
  // validation / findings
  SUPPORTED: 'green', PARTIALLY_SUPPORTED: 'amber', NOT_SUPPORTED: 'red',
  CONTRADICTORY_EVIDENCE: 'red', UNVERIFIABLE: 'gray', UNKNOWN: 'gray',
  // decisions
  SCALE: 'green', RE_PILOT_: 'amber', REJECT: 'red',
  // evaluation
  AWAITING_COI: 'amber', COI_CLEARED: 'blue', EVALUATION_SUBMITTED: 'green', RECUSED: 'red',
  NO_CONFLICT: 'green', POTENTIAL_CONFLICT: 'amber', CONFIRMED_CONFLICT: 'red',
  // milestones & payments
  SUBMITTED: 'blue', BLOCKED: 'red', NOT_ELIGIBLE: 'gray', PENDING_APPROVAL_: 'amber',
  RELEASED: 'green',
  // matching
  HIGH: 'green', MEDIUM: 'amber', LOW: 'red',
  // validators
  ASSIGNED: 'blue', VALIDATOR_ASSIGNED: 'blue', IN_VALIDATION: 'amber', REPORT_SUBMITTED: 'green',
  PREPARED: 'gray', PLANNED: 'amber', PILOT_CREATED: 'green',
  // scale
  DRAFT_NOT_LEGALLY_BINDING: 'amber',
};

export const toneFor = (status) => TONES[String(status || '')] || 'gray';

export const label = (s) =>
  String(s || '—').replaceAll('_', ' ').replace(/_/g, ' ');

export const pct = (v) => (v === null || v === undefined || v === '' ? 'N/A' : `${v}%`);

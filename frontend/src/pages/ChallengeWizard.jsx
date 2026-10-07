import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../services/api';
import { Badge, Card, ErrorState, Field, Loading } from '../components/ui';
import { label } from '../lib/format';

const STEPS = ['Problem', 'AI Requirements', 'KPI Builder', 'Pilot Criteria', 'Data · IP · Security', 'Review & Publish'];
const EMPTY = {
  title: '', department: '', problem_category: '', problem_statement: '', current_situation: '', affected_population: '', existing_process: '', current_limitations: '', expected_outcome: '', geographic_scope: '', constraints: '', priority: 'HIGH', budget_min: 0, budget_max: 0,
  requirements: {}, pilot_criteria: {}, data_policy: {}, ip_policy: {}, cybersecurity: {}, risks: [],
};
const REQ_BUCKETS = ['functional', 'technical', 'security', 'data'];
const DEPARTMENTS = ['Municipal Water Department', 'Urban Development Department', 'Agriculture Department', 'Public Health Department', 'Transport Department'];

function ensureBucket(map, bucket) {
  if (!map[bucket]) map[bucket] = [];
}

function addOfficialRequirement(map, bucket, text) {
  ensureBucket(map, bucket);
  const trimmed = (text || '').trim();
  if (!trimmed) return;
  if (!map[bucket].some((r) => String(r).trim() === trimmed)) map[bucket].push(trimmed);
}

export default function ChallengeWizard({ notify }) {
  const [step, setStep] = useState(1);
  const [c, setC] = useState(EMPTY);
  const [id, setId] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [aiMeta, setAiMeta] = useState(null);
  const [review, setReview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  const patch = (p) => setC((x) => ({ ...x, ...p }));

  async function save(silent = false) {
    if (!id) {
      const created = await api.post('/api/challenges', c);
      setId(created.id);
      if (!silent) notify('Challenge draft created');
      return created.id;
    }
    await api.patch(`/api/challenges/${id}`, c);
    if (!silent) notify('Draft saved');
    return id;
  }

  async function runAI() {
    setBusy(true);
    try {
      const cid = await save(true);
      const res = await api.post(`/api/challenges/${cid}/ai/analyse`);
      setSuggestions(res.suggestions);
      setAiMeta(res);
      notify(`${res.suggestions.length} suggestions generated — nothing is official until you approve`);
      setStep(2);
    } catch (e) { notify(e.message); } finally { setBusy(false); }
  }

  async function decide(s, decision) {
    try {
      const body = decision === 'EDIT'
        ? { edited_text: (prompt('Edit suggestion text', s.edited_text || s.text) || '').trim() }
        : {};
      await api.postJson(`/api/challenges/suggestions/${s.id}/decide?decision=${decision}`, body);
      setSuggestions((list) => list.map((x) => x.id === s.id
        ? { ...x, status: decision === 'ACCEPT' ? 'ACCEPTED' : decision === 'EDIT' ? 'EDITED' : 'REJECTED' } : x));
      if (decision === 'ACCEPT' || decision === 'EDIT') {
        const cat = s.category || 'functional';
        const text = s.edited_text || s.text;
        setC((x) => {
          const next = { ...x };
          ensureBucket(next.requirements, cat);
          addOfficialRequirement(next.requirements, cat, text);
          return next;
        });
        notify(`Suggestion accepted — now an official requirement${decision === 'EDIT' ? ' with your edit' : ''}`);
      } else {
        notify(`Suggestion rejected — not an official requirement`);
      }
    } catch (e) { notify(e.message); }
  }

  async function publish() {
    setBusy(true);
    try {
      await save(true);
      const res = await api.get(`/api/challenges/${id}/review`);
      setReview(res);
      if (res.errors.length) { notify(`Publish blocked by ${res.errors.length} workflow gates`); return; }
      await api.post(`/api/challenges/${id}/publish`);
      notify('Challenge published — now visible for startup matching');
      nav(`/matching/${id}`);
    } catch (e) {
      if (e instanceof ApiError && e.errors.length) { setReview({ errors: e.errors }); notify('Publish blocked by workflow gates'); }
      else notify(e.message);
    } finally { setBusy(false); }
  }

  if (error) return <ErrorState error={error} />;

  return (
    <div className="mx-auto max-w-[1200px] space-y-5">
      <header>
        <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/challenges')}>← Back to challenges</button>
        <div className="eyebrow">Government Challenge Workflow · Stage 1</div>
        <h1 className="text-primary text-headline-lg font-bold">Create Government Challenge</h1>
        <p className="mt-1 text-[14px] text-ink-2">
          Define an operational problem and establish measurable outcomes. AI assists; you approve.
        </p>
      </header>

      <div className="flex flex-wrap gap-1.5">
        {STEPS.map((s, i) => (
          <button key={s} onClick={() => setStep(i + 1)}
            className={`rounded border px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide ${ step === i + 1 ? 'border-primary bg-primary text-white' : step > i + 1 ? 'border-[#A3D9B1] bg-emerald-soft text-emerald' : 'border-line bg-white text-ink-2'}`}>
            {step > i + 1 ? '✓ ' : ''}{i + 1}. {s}
          </button>
        ))}
      </div>

      {step === 1 && (
        <Card title="1 · Define the problem" eyebrow="Officer input">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Challenge title" required><input value={c.title} onChange={(e) => patch({ title: e.target.value })} placeholder="e.g. AI-Based Municipal Water Leakage Detection" /></Field>
            <Field label="Department" required>
              <select value={c.department} onChange={(e) => patch({ department: e.target.value })}>
                <option value="">Select department</option>
                {DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}
              </select>
            </Field>
            <Field label="Problem category"><input value={c.problem_category} onChange={(e) => patch({ problem_category: e.target.value })} placeholder="Water Management, Energy…" /></Field>
            <Field label="Priority">
              <select value={c.priority} onChange={(e) => patch({ priority: e.target.value })}>
                {['HIGH', 'MEDIUM', 'LOW'].map((x) => <option key={x}>{x}</option>)}
              </select>
            </Field>
          </div>
          <div className="mt-4 grid gap-4">
            <Field label="Problem statement" required hint="What is not working today? Be specific and operational.">
              <textarea value={c.problem_statement} onChange={(e) => patch({ problem_statement: e.target.value })} />
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Current situation"><textarea value={c.current_situation} onChange={(e) => patch({ current_situation: e.target.value })} /></Field>
              <Field label="Existing process"><textarea value={c.existing_process} onChange={(e) => patch({ existing_process: e.target.value })} /></Field>
              <Field label="Current limitations"><textarea value={c.current_limitations} onChange={(e) => patch({ current_limitations: e.target.value })} /></Field>
              <Field label="Expected outcome" required><textarea value={c.expected_outcome} onChange={(e) => patch({ expected_outcome: e.target.value })} /></Field>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Affected population"><input value={c.affected_population} onChange={(e) => patch({ affected_population: e.target.value })} /></Field>
              <Field label="Geographic scope"><input value={c.geographic_scope} onChange={(e) => patch({ geographic_scope: e.target.value })} /></Field>
            </div>
          </div>
          <div className="notice mt-4 flex items-center justify-between gap-3">
            <div>
              <strong>AI Requirement Assistant</strong>
              <div className="text-[12px]">Rule-based analysis generates requirement & KPI suggestions. Each needs your explicit Accept / Edit / Reject.</div>
            </div>
            <button className="btn-primary" onClick={runAI} disabled={busy}>✦ Analyse problem</button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card title="2 · AI Requirement Assistant" eyebrow="Human-in-the-loop"
          right={aiMeta && <Badge value="PENDING">Category: {aiMeta.category} · {Math.round(aiMeta.category_confidence * 100)}%</Badge>}>
          {suggestions.length === 0 ? (
            <div className="notice">No suggestions yet. Go back and run “Analyse problem”. AI suggestions never become official requirements automatically.</div>
          ) : (
            <>
              <div className="warnbox mb-4">
                <strong>Nothing below is official yet.</strong> Accept, edit, or reject each suggestion.
                Every decision is recorded in the audit trail with your name and timestamp.
              </div>
              <div className="space-y-2">
                {suggestions.map((s) => (
                  <div key={s.id} className="rounded border border-hairline p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge value={s.status === 'PENDING' ? 'UNDER_REVIEW' : s.status}>{s.status === 'PENDING' ? 'Awaiting officer review' : s.status}</Badge>
                          <span className="badge-gray">{s.category}</span>
                          <span className="mono text-ink-2">confidence {Math.round(s.confidence * 100)}%</span>
                        </div>
                        <p className="mt-1.5 text-[13px] text-ink">{s.edited_text || s.text}</p>
                        <p className="mt-0.5 text-[12px] text-ink-2">Rationale: {s.rationale}</p>
                      </div>
                      <div className="flex shrink-0 gap-1.5">
                        <button className="btn-secondary btn-sm" onClick={() => decide(s, 'ACCEPT')} disabled={s.status !== 'PENDING'}>Accept</button>
                        <button className="btn-secondary btn-sm" onClick={() => decide(s, 'EDIT')} disabled={s.status !== 'PENDING'}>Edit</button>
                        <button className="btn-danger btn-sm" onClick={() => decide(s, 'REJECT')} disabled={s.status !== 'PENDING'}>Reject</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      )}

      {step === 3 && <KpiBuilder c={c} patch={patch} id={id} notify={notify} save={save} />}

      {step === 4 && (
        <Card title="4 · Pilot criteria" eyebrow="Scope the controlled test">
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Pilot duration (weeks)" required>
              <input type="number" value={c.pilot_criteria.duration_weeks || ''} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, duration_weeks: Number(e.target.value) } })} />
            </Field>
            <Field label="Pilot budget max (₹)" required>
              <input type="number" value={c.pilot_criteria.budget_max || ''} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, budget_max: Number(e.target.value), budget_min: c.pilot_criteria.budget_min || 0 } })} />
            </Field>
            <Field label="Number of sites"><input type="number" value={c.pilot_criteria.number_of_sites || ''} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, number_of_sites: Number(e.target.value) } })} /></Field>
            <Field label="Target users"><input value={c.pilot_criteria.target_users || ''} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, target_users: e.target.value } })} /></Field>
            <Field label="Geographic scope"><input value={c.geographic_scope} onChange={(e) => patch({ geographic_scope: e.target.value })} /></Field>
            <Field label="Budget min (₹)"><input type="number" value={c.budget_min || ''} onChange={(e) => patch({ budget_min: Number(e.target.value) })} /></Field>
          </div>
          <div className="mt-4 grid gap-4">
            <Field label="Milestones (one per line)" hint="Each milestone gets deliverable + payment % in the pilot wizard.">
              <textarea value={(c.pilot_criteria.milestones || []).join('\n')} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, milestones: e.target.value.split('\n').filter(Boolean) } })} />
            </Field>
            <Field label="Payment conditions"><input value={c.pilot_criteria.payment_conditions || ''} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, payment_conditions: e.target.value } })} /></Field>
            <Field label="Success criteria" required><textarea value={c.pilot_criteria.success_conditions || ''} onChange={(e) => patch({ pilot_criteria: { ...c.pilot_criteria, success_conditions: e.target.value } })} /></Field>
          </div>
        </Card>
      )}

      {step === 5 && (
        <Card title="5 · Data · IP · Cybersecurity · Risk" eyebrow="Dedicated policy configuration">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Data ownership" required>
              <select value={c.data_policy.ownership || ''} onChange={(e) => patch({ data_policy: { ...c.data_policy, ownership: e.target.value } })}>
                <option value="">Select…</option>
                <option>Government of Maharashtra owns all pilot data</option>
                <option>Joint ownership (negotiated)</option>
                <option>Startup owns with government perpetual licence</option>
              </select>
            </Field>
            <Field label="Data residency"><input value={c.data_policy.residency || ''} onChange={(e) => patch({ data_policy: { ...c.data_policy, residency: e.target.value } })} placeholder="e.g. Maharashtra SDC (Pune)" /></Field>
            <Field label="Data retention"><input value={c.data_policy.retention || ''} onChange={(e) => patch({ data_policy: { ...c.data_policy, retention: e.target.value } })} placeholder="e.g. 7 years" /></Field>
            <Field label="Privacy requirements"><input value={c.data_policy.privacy || ''} onChange={(e) => patch({ data_policy: { ...c.data_policy, privacy: e.target.value } })} placeholder="DPDP Act 2023 compliance" /></Field>
            <Field label="Pre-existing IP"><input value={c.ip_policy.pre_existing || ''} onChange={(e) => patch({ ip_policy: { ...c.ip_policy, pre_existing: e.target.value } })} /></Field>
            <Field label="Government usage rights"><input value={c.ip_policy.new_ip || ''} onChange={(e) => patch({ ip_policy: { ...c.ip_policy, new_ip: e.target.value } })} /></Field>
            <Field label="Authentication requirement" required>
              <input value={c.cybersecurity.authentication || ''} onChange={(e) => patch({ cybersecurity: { ...c.cybersecurity, authentication: e.target.value } })} placeholder="SSO + RBAC" />
            </Field>
            <Field label="Encryption"><input value={c.cybersecurity.encryption || ''} onChange={(e) => patch({ cybersecurity: { ...c.cybersecurity, encryption: e.target.value } })} placeholder="TLS 1.2+ / AES-256" /></Field>
            <Field label="Security testing"><input value={c.cybersecurity.testing || ''} onChange={(e) => patch({ cybersecurity: { ...c.cybersecurity, testing: e.target.value } })} placeholder="VAPT before scale" /></Field>
            <Field label="Audit logging"><input value={c.cybersecurity.audit_logging || ''} onChange={(e) => patch({ cybersecurity: { ...c.cybersecurity, audit_logging: e.target.value } })} /></Field>
          </div>
          <div className="mt-4">
            <div className="eyebrow mb-2">Risks</div>
            <RiskEditor risks={c.risks} patch={patch} />
          </div>
        </Card>
      )}

      {step === 6 && (
        <Card title="6 · Review & publish" eyebrow="Final check"
          right={review?.errors?.length ? <Badge value="REJECTED">{review.errors.length} gates open</Badge> : undefined}>
          {review?.errors?.length ? (
            <div className="errorbox mb-4">
              <strong>Complete these before publishing:</strong>
              <ul className="mt-1 list-disc pl-4">{review.errors.map((e) => <li key={e}>{e}</li>)}</ul>
            </div>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <ReviewBlock title="Problem" onEdit={() => setStep(1)}>
              <p className="text-[13px] font-semibold text-ink">{c.title || 'Untitled'}</p>
              <p className="text-[12px] text-ink-2">{c.department} · {c.problem_category}</p>
              <p className="mt-1 text-[12px]">{c.problem_statement || 'No problem statement yet.'}</p>
            </ReviewBlock>
            <ReviewBlock title="Requirements (official)" onEdit={() => setStep(2)}>
              {Object.entries(c.requirements).length === 0 ? <p className="text-[12px] text-ink-2">None accepted yet.</p> :
                Object.entries(c.requirements).map(([k, list]) => (
                  <p key={k} className="text-[12px]"><span className="badge-gray mr-1">{k}</span>{list.length} accepted</p>
                ))}
            </ReviewBlock>
            <ReviewBlock title="KPIs" onEdit={() => setStep(3)}>
              <KpiReview c={c} id={id} />
            </ReviewBlock>
            <ReviewBlock title="Pilot · Data · Security" onEdit={() => setStep(4)}>
              <p className="text-[12px]">Duration: {c.pilot_criteria.duration_weeks || '—'} weeks · Budget: ₹{Number(c.pilot_criteria.budget_max || 0).toLocaleString('en-IN')}</p>
              <p className="text-[12px]">Data: {c.data_policy.ownership || '—'}</p>
              <p className="text-[12px]">Security: {c.cybersecurity.authentication || '—'}</p>
            </ReviewBlock>
          </div>
          <div className="notice mt-4">
            <strong>Responsible AI:</strong> AI provided suggestions only; the officer remains responsible
            for the final requirement set. Publishing makes this challenge visible to startup matching.
          </div>
        </Card>
      )}

      <div className="flex items-center justify-between gap-3 rounded-lg border border-hairline bg-white p-4 shadow-card">
        <button className="btn-quiet" onClick={() => save()} disabled={busy}>Save draft</button>
        <div className="flex gap-2">
          {step > 1 && <button className="btn-secondary" onClick={() => setStep(step - 1)}>← Back</button>}
          {step < 6
            ? <button className="btn-primary" onClick={() => { save(); setStep(step + 1); }} disabled={busy}>Continue →</button>
            : <button className="btn-primary" onClick={publish} disabled={busy}>Publish Challenge ↗</button>}
        </div>
      </div>
    </div>
  );
}

function ReviewBlock({ title, onEdit, children }) {
  return (
    <div className="rounded border border-hairline p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="eyebrow">{title}</span>
        <button className="link text-[12px]" onClick={onEdit}>Edit</button>
      </div>
      {children}
    </div>
  );
}

function RiskEditor({ risks, patch }) {
  const [draft, setDraft] = useState({ risk: '', probability: 2, impact: 3 });
  return (
    <div className="space-y-2">
      {risks.map((r, i) => (
        <div key={i} className="flex items-center justify-between rounded border border-hairline px-3 py-2 text-[13px]">
          <span>{r.risk} <span className="mono text-ink-2">P{r.probability}×I{r.impact}</span></span>
          <button className="btn-danger btn-sm" onClick={() => patch({ risks: risks.filter((_, j) => j !== i) })}>Remove</button>
        </div>
      ))}
      <div className="flex flex-wrap items-end gap-2 rounded border border-dashed border-line p-3">
        <Field label="Risk"><input value={draft.risk} onChange={(e) => setDraft({ ...draft, risk: e.target.value })} /></Field>
        <Field label="Probability (1-5)"><input type="number" min="1" max="5" value={draft.probability} onChange={(e) => setDraft({ ...draft, probability: Number(e.target.value) })} /></Field>
        <Field label="Impact (1-5)"><input type="number" min="1" max="5" value={draft.impact} onChange={(e) => setDraft({ ...draft, impact: Number(e.target.value) })} /></Field>
        <button className="btn-secondary" onClick={() => { if (draft.risk) { patch({ risks: [...risks, draft] }); setDraft({ risk: '', probability: 2, impact: 3 }); } }}>Add risk</button>
      </div>
    </div>
  );
}

function KpiBuilder({ c, patch, id, notify, save }) {
  const [kpis, setKpis] = useState([]);
  const [draft, setDraft] = useState({ name: '', baseline: '', target: '', unit: '%', measurement_method: '', evidence_source: '', success_threshold: '', direction: 'reduce', description: '' });
  useEffect(() => { if (id) api.get(`/api/challenges/${id}`).then((r) => setKpis(r.kpis)).catch(() => {}); }, [id]);

  async function add() {
    if (!draft.name) { notify('KPI name is required'); return; }
    try {
      const cid = id || (await save(true));
      const k = await api.post(`/api/challenges/${cid}/kpis`, draft);
      setKpis((x) => [...x, k]);
      setDraft({ name: '', baseline: '', target: '', unit: '%', measurement_method: '', evidence_source: '', success_threshold: '', direction: 'reduce', description: '' });
      notify('KPI added');
    } catch (e) { notify(e.message); }
  }
  async function remove(kpiId) {
    try { await api.del(`/api/challenges/${id}/kpis/${kpiId}`); setKpis((x) => x.filter((k) => k.id !== kpiId)); notify('KPI removed'); }
    catch (e) { notify(e.message); }
  }

  return (
    <div className="space-y-4">
      <div className="notice">
        A pilot is only useful when the <strong>baseline, target, measurement method and evidence source</strong> are explicit.
        Example: Leakage Reduction · baseline 12% · target 20% · smart meter comparison · municipal telemetry · threshold ≥ 18%.
      </div>
      {kpis.length > 0 && (
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>KPI</th><th>Baseline</th><th>Target</th><th>Threshold</th><th>Method</th><th>Evidence source</th><th></th></tr></thead>
            <tbody>
              {kpis.map((k) => (
                <tr key={k.id}>
                  <td className="font-semibold">{k.name}<div className="subtle">{label(k.direction)} · {k.unit}</div></td>
                  <td>{k.baseline || '—'}</td><td>{k.target || '—'}</td><td>{k.success_threshold || '—'}</td>
                  <td className="text-[12px]">{k.measurement_method || '—'}</td>
                  <td className="text-[12px]">{k.evidence_source || '—'}</td>
                  <td className="text-right"><button className="btn-danger btn-sm" onClick={() => remove(k.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="rounded-lg border border-dashed border-line p-4">
        <div className="eyebrow mb-3">Add KPI</div>
        <div className="grid gap-3 md:grid-cols-4">
          <Field label="KPI name" required><input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></Field>
          <Field label="Baseline"><input value={draft.baseline} onChange={(e) => setDraft({ ...draft, baseline: e.target.value })} placeholder="12%" /></Field>
          <Field label="Target"><input value={draft.target} onChange={(e) => setDraft({ ...draft, target: e.target.value })} placeholder="20%" /></Field>
          <Field label="Unit"><input value={draft.unit} onChange={(e) => setDraft({ ...draft, unit: e.target.value })} /></Field>
          <Field label="Measurement method"><input value={draft.measurement_method} onChange={(e) => setDraft({ ...draft, measurement_method: e.target.value })} /></Field>
          <Field label="Evidence source"><input value={draft.evidence_source} onChange={(e) => setDraft({ ...draft, evidence_source: e.target.value })} /></Field>
          <Field label="Success threshold"><input value={draft.success_threshold} onChange={(e) => setDraft({ ...draft, success_threshold: e.target.value })} placeholder="≥ 18%" /></Field>
          <Field label="Direction">
            <select value={draft.direction} onChange={(e) => setDraft({ ...draft, direction: e.target.value })}>
              <option value="reduce">reduce</option><option value="increase">increase</option>
            </select>
          </Field>
        </div>
        <button className="btn-primary mt-3" onClick={add}>＋ Add KPI</button>
      </div>
    </div>
  );
}

function KpiReview({ c, id }) {
  const [kpis, setKpis] = useState(c.kpis || []);
  useEffect(() => { if (id) api.get(`/api/challenges/${id}`).then((r) => setKpis(r.kpis || [])).catch(() => {}); }, [id]);
  if (!kpis.length) return <p className="text-[12px] text-ink-2">No KPIs yet.</p>;
  return <ul className="text-[12px]">{kpis.map((k) => <li key={k.id}>{k.name} · target {k.target}{k.unit} · threshold {k.success_threshold}</li>)}</ul>;
}

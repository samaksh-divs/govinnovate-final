import { useCallback, useEffect, useState } from 'react';
import { api, getUser } from '../services/api';
import { can } from '../lib/personas';
import { Badge, Card, EmptyState, ErrorState, Loading, MetricCard, Modal } from '../components/ui';
import { label } from '../lib/format';

export default function Evaluations({ notify }) {
  const [criteria, setCriteria] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [assignmentCoiCache, setAssignmentCoiCache] = useState({});

  // Keep authoritative COI declarations synced from the API across navigation.
  useEffect(() => {
    const onCoiUpdated = (e) => {
      const { assignmentId, coi } = e.detail || {};
      if (!assignmentId || !coi) return;
      setAssignmentCoiCache((prev) => ({ ...prev, [assignmentId]: coi }));
    };
    window.addEventListener('gv-coi-updated', onCoiUpdated);
    return () => window.removeEventListener('gv-coi-updated', onCoiUpdated);
  }, []);
  const [challengeId, setChallengeId] = useState('');
  const [assignments, setAssignments] = useState([]);
  const [aggregates, setAggregates] = useState([]);
  const [evaluating, setEvaluating] = useState(null); // assignment
  const canEvaluate = can(getUser()?.role, 'EVALUATION_SUBMIT');
  const canDecide = can(getUser()?.role, 'SHORTLIST_DECISION');
  const [busy, setBusy] = useState(null);

  async function decide(startupId, decision, reason) {
    setBusy(startupId);
    try {
      await api.post(`/api/evaluations/decisions?challenge_id=${challengeId}&startup_id=${startupId}&decision=${decision}&reason=${encodeURIComponent(reason)}`);
      notify(decision === 'SHORTLIST_FOR_PILOT' ? 'Application APPROVED — startup sees the updated status immediately' : 'Application rejected — startup sees the updated status immediately');
    } catch (e) { notify(`Decision failed: ${e.message}`); }
    finally { setBusy(null); }
  }
  const [coiWatching, setCoiWatching] = useState(null); // { assignment, status } when declaring COI
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/api/evaluations/criteria').then(setCriteria).catch(setError);
    api.get('/api/challenges').then(setChallenges).catch(() => {});
  }, []);

  const load = useCallback(() => {
    if (!challengeId) return;
    api.get(`/api/evaluations/assignments?challenge_id=${challengeId}`).then(setAssignments).catch(() => {});
    api.get(`/api/evaluations/aggregates/${challengeId}`).then(setAggregates).catch(() => {});
  }, [challengeId]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (!criteria) return <Loading />;

  const stats = {
    startups: aggregates.length,
    submitted: assignments.filter((a) => a.status === 'EVALUATION_SUBMITTED').length,
    coiOpen: assignments.filter((a) => a.status === 'AWAITING_COI').length,
    recused: assignments.filter((a) => a.status === 'RECUSED').length,
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Human Review Layer</div>
          <h1 className="text-primary text-headline-lg font-bold">Expert Evaluation</h1>
          <p className="mt-1 text-[14px] text-ink-2">Independent expert judgement with mandatory COI declarations, versioned submissions and visible disagreement.</p>
        </div>
        <span className="badge-blue">AI MATCH ≠ EXPERT EVALUATION</span>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <select value={challengeId} onChange={(e) => setChallengeId(e.target.value)}
          className="rounded border border-line bg-white px-3 py-2 text-[13px]">
          <option value="">Select a published challenge…</option>
          {challenges.filter((c) => c.status === 'PUBLISHED').map((c) => (
            <option key={c.id} value={c.id}>{c.title}</option>))}
        </select>
      </div>

      {!challengeId ? (
        <EmptyState icon="✔" title="Select a challenge">Expert assignments are created per published challenge and startup.</EmptyState>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="Startups under review" value={stats.startups} tone="blue" />
            <MetricCard label="Evaluations submitted" value={stats.submitted} tone="green" />
            <MetricCard label="COI pending" value={stats.coiOpen} tone="orange" attention={stats.coiOpen > 0} />
            <MetricCard label="Recused experts" value={stats.recused} tone="red" attention={stats.recused > 0} />
          </div>

          <Card eyebrow="Multi-expert aggregation" title="Aggregated scores — disagreement is never hidden">
            {aggregates.length === 0 ? <p className="subtle">No evaluations yet for this challenge.</p> : (
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead><tr><th>Startup</th><th>N</th><th>Avg</th><th>Median</th><th>Min</th><th>Max</th><th>Std dev</th><th>Consensus</th><th>Recommendation</th>{canDecide && <th>Decision</th>}</tr></thead>
                  <tbody>
                    {aggregates.map((a) => (
                      <tr key={a.startup_id}>
                        <td className="font-semibold">{a.startup?.name}</td>
                        <td>{a.evaluation_count}</td>
                        <td className="font-bold text-primary">{a.average ?? '—'}</td>
                        <td>{a.median ?? '—'}</td>
                        <td>{a.minimum ?? '—'}</td>
                        <td>{a.maximum ?? '—'}</td>
                        <td className={a.disagreement_flag ? 'font-bold text-crimson' : ''}>{a.stddev ?? '—'}</td>
                        <td>{a.disagreement_flag ? <span className="badge-red">⚠ HIGH EVALUATOR DISAGREEMENT</span> : <span className="badge-gray">{a.consensus}</span>}</td>
                        <td><span className="badge-blue">{label(a.recommendation)}</span></td>
                        {canDecide && (
                          <td className="text-right">
                            <div className="flex justify-end gap-1">
                              <button className="btn-primary btn-sm" disabled={busy === a.startup_id}
                                onClick={() => decide(a.startup_id, 'SHORTLIST_FOR_PILOT', 'Shortlisted for pilot based on aggregated expert evaluation')}>Approve</button>
                              <button className="btn-secondary btn-sm" disabled={busy === a.startup_id}
                                onClick={() => decide(a.startup_id, 'DO_NOT_SHORTLIST', 'Not shortlisted after expert evaluation review')}>Reject</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {aggregates.some((a) => Object.keys(a.criterion_disagreement).length > 0) && (
              <div className="warnbox mt-3">
                <strong>Criterion-level disagreement:</strong>{' '}
                {aggregates.flatMap((a) => Object.entries(a.criterion_disagreement)).map(([k, v]) => `${k} (${v} pts)`).join(' · ')}
              </div>
            )}
          </Card>

          <Card eyebrow="Assignments" title="Independent review status">
            {assignments.length === 0 ? (
              <div className="notice">No expert assignments yet. Officers assign experts from a startup's evaluation panel; each expert must declare COI first.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead><tr><th>Startup</th><th>Expert</th><th>Status</th><th>COI</th><th>Latest score</th><th></th></tr></thead>
                  <tbody>
                    {assignments.map((a) => (
                      <tr key={a.id}>
                        <td className="font-semibold">{a.startup_id}</td>
                        <td>{a.expert?.name}<div className="subtle">{a.expert?.organization}</div></td>
                        <td><Badge value={a.status} /></td>
                        <td>{a.coi ? <Badge value={a.coi.status} /> : <span className="badge-gray">Pending</span>}</td>
                        <td>{a.latest_evaluation ? `${a.latest_evaluation.weighted_total} (v${a.latest_evaluation.version})` : '—'}</td>
                        <td className="text-right">
                          {a.status !== 'RECUSED' && canEvaluate && (
                            <button className="btn-secondary btn-sm"
                              onClick={() => a.status === 'COI_CLEARED' ? setEvaluating(a) : notify('COI declaration required first')}>
                              {a.latest_evaluation ? 'View / Re-evaluate' : a.status === 'COI_CLEARED' ? 'Evaluate' : 'Declare COI'}
                            </button>
                          )}
                          {a.status === 'RECUSED' && <span className="badge-red">Blocked</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}

      {evaluating && coiWatching ? (
        <EvaluationModal assignment={evaluating} criteria={criteria.criteria} coiCategories={criteria.coi_categories}
          coiStatus={coiWatching.status}
          onClose={() => { setEvaluating(null); setCoiWatching(null); load(); }} notify={notify} />
      ) : evaluating && (
        <EvaluationModal assignment={evaluating} criteria={criteria.criteria} coiCategories={criteria.coi_categories}
          onClose={() => { setEvaluating(null); load(); }} notify={notify} />
      )}
    </div>
  );
}

function assessCoi(assignment, coiStatus) {
  // coiStatus: 'declaring' | 'declared' | null
  // The declaration is mandatory when the assignment has no COI, or when the user
  // is in the midst of declaring it but has not submitted yet.
  return !assignment.coi || coiStatus === 'declaring';
}

function EvaluationModal({ assignment, criteria, coiCategories, coiStatus, onClose, notify }) {
  const needsCoi = !assessCoi(assignment, coiStatus);
  const [scores, setScores] = useState(Object.fromEntries(criteria.map((c) => [c.key, { score: 60, justification: '' }])));
  const [recommendation, setRecommendation] = useState('RECOMMEND_FOR_PILOT');
  const [finalComments, setFinalComments] = useState('');
  const [coi, setCoi] = useState({ status: assignment.coi?.status || 'NO_CONFLICT', conflict_type: assignment.coi?.conflict_type || '', description: assignment.coi?.description || '' });
  const [error, setError] = useState('');

  async function submitCoi() {
    try {
      const res = await api.post(`/api/evaluations/assignments/${assignment.id}/coi`, coi);
      notify('COI declared');
      // Persist the declaration: authoritative state is in the backend; sync the
      // local assignments array so the change survives navigation/refreshes and
      // other components (metrics, table) see it.
      if (res && res.coi) {
        assignment.coi = res.coi;
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('gv-coi-updated', { detail: { assignmentId: assignment.id, coi: res.coi } }));
        }
        if (coi.status === 'CONFIRMED_CONFLICT') { onClose(); }
      }
    } catch (e) { setError(e.message); }
  }

  async function submit() {
    try {
      await api.post(`/api/evaluations/assignments/${assignment.id}/evaluation`, { scores, recommendation, final_comments: finalComments });
      notify('Evaluation submitted — versioned, prior scores preserved');
      onClose();
    } catch (e) { setError(e.message); }
  }

  return (
    <Modal wide eyebrow="Mandatory controls" title={assignment.expert?.name || 'Evaluation'} onClose={onClose}>
      {error && <div className="errorbox mb-3">{error}</div>}
      {needsCoi ? (
        <div className="space-y-3">
          <div className="warnbox">
            <strong>Conflict of Interest declaration is required before evaluation.</strong>
            <p className="mt-1 text-[12px]">A confirmed conflict permanently recuses the expert; a recused expert cannot evaluate that startup or pilot.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="field"><span>Declaration status<span className="req">*</span></span>
              <select value={coi.status} onChange={(e) => setCoi({ ...coi, status: e.target.value })}>
                {['NO_CONFLICT', 'POTENTIAL_CONFLICT', 'CONFIRMED_CONFLICT'].map((s) => <option key={s} value={s}>{label(s)}</option>)}
              </select></label>
            <label className="field"><span>Conflict type (if any)</span>
              <select value={coi.conflict_type} onChange={(e) => setCoi({ ...coi, conflict_type: e.target.value })}>
                <option value="">Select if applicable</option>
                {coiCategories.map((c) => <option key={c}>{c}</option>)}
              </select></label>
          </div>
          <label className="field"><span>Description</span>
            <textarea value={coi.description} onChange={(e) => setCoi({ ...coi, description: e.target.value })} /></label>
          <div className="flex justify-end"><button className="btn-primary" onClick={submitCoi}>Submit declaration ↗</button></div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <span className="badge-gray">Weighted criteria: 100%</span>
            <span className="badge-gray">Scores &lt; 40 require justification</span>
            <span className="badge-gray">Submissions are versioned</span>
          </div>
          {criteria.map((c) => (
            <div key={c.key} className="rounded border border-hairline p-3">
              <div className="flex items-center justify-between">
                <div><strong className="text-[13px]">{c.label}</strong> <span className="subtle">{c.weight}% weight</span></div>
                <span className="mono font-bold text-primary">{scores[c.key].score}</span>
              </div>
              <input type="range" min="0" max="100" value={scores[c.key].score} className="mt-2 w-full accent-[#0F2942]"
                onChange={(e) => setScores({ ...scores, [c.key]: { ...scores[c.key], score: Number(e.target.value) } })} />
              <input className="mt-1 w-full rounded border border-line px-2 py-1 text-[12px]" placeholder={scores[c.key].score < 40 ? 'Justification REQUIRED for low score' : 'Justification / concern (optional)'}
                value={scores[c.key].justification}
                onChange={(e) => setScores({ ...scores, [c.key]: { ...scores[c.key], justification: e.target.value } })} />
            </div>
          ))}
          <div className="grid gap-3 md:grid-cols-2">
            <label className="field"><span>Recommendation</span>
              <select value={recommendation} onChange={(e) => setRecommendation(e.target.value)}>
                {['RECOMMEND_FOR_PILOT', 'RECOMMEND_WITH_CONDITIONS', 'NEED_MORE_EVIDENCE', 'DO_NOT_RECOMMEND'].map((r) => <option key={r} value={r}>{label(r)}</option>)}
              </select></label>
            <label className="field"><span>Final comments</span>
              <textarea value={finalComments} onChange={(e) => setFinalComments(e.target.value)} placeholder="Summarise the evidence and judgement." /></label>
          </div>
          <div className="flex justify-end"><button className="btn-primary" onClick={submit}>Submit evaluation ↗</button></div>
        </div>
      )}
    </Modal>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { inr } from '../lib/format';

export default function Repilots({ notify }) {
  const [plans, setPlans] = useState([]);
  const [pilots, setPilots] = useState([]);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  const load = useCallback(() => {
    api.get('/api/pilots').then((ps) => {
      setPilots(ps);
      Promise.all(ps.map((p) =>
        api.get(`/api/repilots/${p.id}/plan`).then((r) => ({ ...r, pilot: p })).catch(() => null)))
        .then((rs) => setPlans(rs.filter(Boolean)));
    }).catch(setError);
  }, []);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;

  async function createPlan(pilotId) {
    try { await api.post(`/api/repilots/${pilotId}/plan`); notify('Re-pilot plan created from the RE_PILOT decision'); load(); }
    catch (e) { notify(e.message); }
  }
  async function spawn(planId) {
    try {
      const r = await api.post(`/api/repilots/plans/${planId}/create-pilot`);
      notify(`Follow-on pilot created: ${r.new_pilot_id}`); load();
    } catch (e) { notify(e.message); }
  }

  return (
    <div className="mx-auto max-w-[1300px] space-y-5">
      <header>
        <div className="eyebrow">Re-Pilot · Controlled Continuation</div>
        <h1 className="text-primary text-headline-lg font-bold">Re-Pilot Plans</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          A re-pilot carries forward KPI results, lessons, evidence gaps and risks — and shows exactly
          what is changing between pilots. Available only after a government RE-PILOT decision.
        </p>
      </header>

      {plans.length === 0 ? (
        <>
          <EmptyState icon="↻" title="No re-pilot plans yet">
            Record a RE-PILOT government decision in the decision workspace, then create the plan here.
          </EmptyState>
          <Card title="Pilots with recorded decisions">
            <ul className="space-y-2">
              {pilots.filter((p) => p.status === 'DECIDED' || p.status === 'RE_PILOT').map((p) => (
                <li key={p.id} className="flex items-center justify-between rounded border border-hairline px-3 py-2">
                  <span className="text-[13px] font-semibold">{p.name} <span className="badge-amber ml-1">{p.status}</span></span>
                  <button className="btn-secondary btn-sm" onClick={() => createPlan(p.id)}>Create re-pilot plan</button>
                </li>
              ))}
              {pilots.filter((p) => p.status === 'DECIDED' || p.status === 'RE_PILOT').length === 0 &&
                <li className="subtle">No eligible pilots (status DECIDED / RE_PILOT).</li>}
            </ul>
          </Card>
        </>
      ) : (
        <div className="space-y-4">
          {plans.map((plan) => (
            <Card key={plan.id}
              eyebrow={`Plan ${plan.id} · pilot ${plan.pilot_id}`}
              title={<div className="flex items-center gap-2"><Badge value={plan.status} />{plan.pilot?.name}</div>}
              right={
                <div className="flex gap-2">
                  {plan.status === 'PLANNED' && (
                    <button className="btn-primary btn-sm" onClick={() => spawn(plan.id)}>Create Phase-2 pilot ↗</button>
                  )}
                  {plan.new_pilot_id && (
                    <button className="btn-secondary btn-sm" onClick={() => nav(`/pilots/${plan.new_pilot_id}`)}>
                      Open {plan.new_pilot_id} ↗
                    </button>
                  )}
                </div>
              }>
              <div className="grid gap-4 xl:grid-cols-3">
                <div>
                  <div className="eyebrow mb-1">Carried forward</div>
                  <div className="rounded border border-hairline p-3">
                    <div className="eyebrow text-ink-2">Previous KPI results</div>
                    <table className="tbl mt-1">
                      <thead><tr><th>KPI</th><th>Claimed</th><th>Observed</th><th>Status</th></tr></thead>
                      <tbody>
                        {(plan.carried_forward.previous_kpi_results || []).map((k) => (
                          <tr key={k.name}><td className="text-[12px] font-semibold">{k.name}</td>
                            <td className="mono text-[12px]">{k.claimed || '—'}</td>
                            <td className="mono text-[12px]">{k.observed || '—'}</td><td className="text-[12px]">{k.status}</td></tr>
                        ))}
                      </tbody>
                    </table>
                    {(plan.carried_forward.evidence_gaps || []).length > 0 && (
                      <div className="mt-2">
                        <div className="eyebrow text-crimson">Evidence gaps to close</div>
                        <ul className="list-disc pl-4 text-[12px]">{plan.carried_forward.evidence_gaps.map((g) => <li key={g}>{g}</li>)}</ul>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <div className="eyebrow mb-1">What is changing</div>
                  <div className="rounded border border-hairline p-3">
                    {Object.entries(plan.scope_changes).map(([k, ch]) => (
                      <div key={k} className="border-b border-hairline py-1.5 text-[13px] last:border-0">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold capitalize">{k.replace('_', ' ')}</span>
                          <span className="mono">{String(ch.from)} → <b className="text-primary">{String(ch.to)}</b></span>
                        </div>
                        <div className="text-[11px] text-ink-2">{ch.reason}</div>
                      </div>
                    ))}
                    {plan.scope_changes.budget && (
                      <p className="mt-1 text-[12px] text-ink-2">Phase-2 budget: {inr(plan.scope_changes.budget.to)}</p>
                    )}
                  </div>
                </div>

                <div>
                  <div className="eyebrow mb-1">Required changes (conditions)</div>
                  <ul className="space-y-1">
                    {plan.required_changes.map((r) => (
                      <li key={r} className="flex gap-2 rounded border border-[#F6E05E] bg-gold-soft px-3 py-2 text-[13px]">⚠ {r}</li>
                    ))}
                  </ul>
                  {(plan.carried_forward.lessons || []).length > 0 && (
                    <div className="mt-2">
                      <div className="eyebrow">Lessons carried forward</div>
                      <ul className="list-disc pl-4 text-[12px]">{plan.carried_forward.lessons.map((l) => <li key={l.title}>{l.title}</li>)}</ul>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

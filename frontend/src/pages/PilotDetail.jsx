import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, ErrorState, Loading, MetricCard, PipelineStepper } from '../components/ui';
import { DataTag } from '../components/provenance';
import { inr, label } from '../lib/format';

export default function PilotDetail({ notify }) {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  const load = useCallback(() => {
    api.get(`/api/pilots/${id}`).then(setP).catch(setError);
    api.get(`/api/pilots/${id}/readiness`).then(setReadiness).catch(() => {});
  }, [id]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (!p) return <Loading />;

  const stageMap = { DRAFT: 1, PENDING_APPROVAL: 2, READY_TO_START: 3, ACTIVE: 5, CONCLUDED: 6, DECIDED: 7, SCALED: 8, RE_PILOT: 7 };

  async function action(fn, message) {
    try { await fn(); load(); notify(message); }
    catch (e) { notify(e.message); }
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/pilots')}>← All pilots</button>
          <div className="eyebrow">Pilot Record · Formal government project file</div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="mono text-ink-2">{p.id}</span>
            <DataTag kind="pilot">SIMULATED PILOT</DataTag>
          </div>
          <h1 className="mt-1 text-primary text-headline-lg font-bold">{p.name}</h1>
          <p className="mt-1 text-[13px] text-ink-2">{p.startup_name} · {p.department} · {p.duration_weeks} weeks · {p.sites} sites</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge value={p.status} />
          <div className="flex gap-2">
            {p.status === 'DRAFT' && (
              <button className="btn-primary" onClick={() => action(() => api.post(`/api/pilots/${id}/approve`), 'Pilot sent for startup acceptance')}>
                Submit for approval
              </button>
            )}
            {p.status === 'PENDING_APPROVAL' && (
              <button className="btn-primary" onClick={() => action(() => api.post(`/api/pilots/${id}/transition?to_status=READY_TO_START`), 'Agreement accepted — pilot ready to start')}>
                Accept (startup)
              </button>
            )}
            {p.status === 'READY_TO_START' && (
              <button className="btn-primary" onClick={() => action(() => api.post(`/api/pilots/${id}/transition?to_status=ACTIVE`), 'Pilot started')}>
                Start pilot
              </button>
            )}
            {p.status === 'ACTIVE' && (
              <button className="btn-secondary" onClick={() => action(() => api.post(`/api/pilots/${id}/transition?to_status=CONCLUDED`), 'Pilot concluded')}>
                Conclude pilot
              </button>
            )}
            <button className="btn-secondary" onClick={() => nav(`/decisions/${p.id}`)}>Decision intelligence ↗</button>
          </div>
        </div>
      </header>

      <div className="card card-pad">
        <PipelineStepper current={stageMap[p.status] || 1} />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Budget" value={inr(p.budget)} tone="blue" />
        <MetricCard label="Milestones accepted" value={`${p.milestones.filter((m) => m.status === 'ACCEPTED').length}/${p.milestones.length}`} tone="teal" />
        <MetricCard label="Evidence items" value={p.evidence_count} tone="navy" />
        <MetricCard label="KPIs" value={p.kpis.length} tone="orange" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" eyebrow="KPI monitoring" title="Baseline → Claim → Observed (kept separate)">
          <div className="flex justify-between items-center mt-2">
            <span className="text-[12px] text-ink-2">Open the separate KPI workspace →</span>
            <button className="btn-secondary btn-sm" onClick={() => nav(`/pilots/${id}/kpis`)}>KPI workspace ↗</button>
          </div>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>KPI</th><th>Baseline</th><th>Target</th><th>Threshold</th><th>Claimed</th><th>Observed</th><th>Status</th></tr></thead>
              <tbody>
                {p.kpis.map((k) => (
                  <tr key={k.id}>
                    <td className="font-semibold">{k.name}<div className="subtle">{k.evidence_source}</div></td>
                    <td>{k.baseline || '—'}</td>
                    <td>{k.target}{k.unit}</td>
                    <td>{k.success_threshold}</td>
                    <td className="text-ink-2">{k.claimed_value || '—'}</td>
                    <td className="font-bold text-primary">{k.observed_value || '—'}</td>
                    <td><Badge value={k.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="subtle mt-2">Startup claims and instrumented observations are recorded separately. Independent validation compares both.</p>
        </Card>

        <Card eyebrow="Pilot health" title={<span className={`badge-${p.health === 'GREEN' ? 'green' : p.health === 'RED' ? 'red' : 'amber'}`}>{p.health}</span>}>
          <ul className="space-y-2">
            {p.health_explanation.map((r, i) => (
              <li key={i} className="flex gap-2 rounded border border-hairline px-3 py-2 text-[13px]">
                <span>{p.health === 'GREEN' ? '✓' : '!'}</span>{r}
              </li>
            ))}
          </ul>
          <p className="subtle mt-3">Health is explainable — never a black-box score. Reasons are recomputed from KPI status, evidence states and the security checklist.</p>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Milestones & payments" title={`Payment allocation ${p.payment_total === 100 ? '✓ totals 100%' : `⚠ totals ${p.payment_total}%`}`}>
          <div className="flex justify-between items-center mt-2">
            <span className="text-[12px] text-ink-2">Open the separate Milestone workspace →</span>
            <button className="btn-secondary btn-sm" onClick={() => nav(`/pilots/${id}/milestones`)}>Milestone workspace ↗</button>
          </div>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Milestone</th><th>Deliverable</th><th>Payment</th><th>Status</th><th>Payment status</th><th></th></tr></thead>
              <tbody>
                {p.milestones.map((m) => (
                  <tr key={m.id}>
                    <td className="font-semibold">{m.name}</td>
                    <td className="text-[12px]">{m.deliverable}</td>
                    <td className="mono">{m.payment_percentage}% · {inr(Math.round(p.budget * m.payment_percentage / 100))}</td>
                    <td><Badge value={m.status} /></td>
                    <td><Badge value={m.payment_status} /></td>
                    <td className="text-right space-x-1">
                      {m.status === 'IN_PROGRESS' && (
                        <button className="btn-secondary btn-sm" onClick={() => action(() => api.patch(`/api/pilots/${id}/milestones/${m.id}/status?status=SUBMITTED`), 'Milestone submitted')}>Submit</button>
                      )}
                      {m.status === 'SUBMITTED' && (
                        <button className="btn-secondary btn-sm" onClick={() => action(() => api.patch(`/api/pilots/${id}/milestones/${m.id}/status?status=ACCEPTED`), 'Milestone accepted with evidence')}>Accept</button>
                      )}
                      {m.status === 'ACCEPTED' && m.payment_status === 'NOT_ELIGIBLE' && (
                        <button className="btn-secondary btn-sm" onClick={() => action(() => api.patch(`/api/pilots/${id}/milestones/${m.id}/status?payment_status=PENDING_APPROVAL`), 'Payment eligibility requested')}>Request payment</button>
                      )}
                      {m.payment_status === 'PENDING_APPROVAL' && (
                        <button className="btn-secondary btn-sm" onClick={() => action(() => api.patch(`/api/pilots/${id}/milestones/${m.id}/status?payment_status=APPROVED`), 'Payment approved (simulated)')}>Approve</button>
                      )}
                      {m.payment_status === 'APPROVED' && (
                        <button className="btn-secondary btn-sm" onClick={() => action(() => api.patch(`/api/pilots/${id}/milestones/${m.id}/status?payment_status=RELEASED`), 'Payment released (simulated ledger)')}>Release</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="subtle mt-2">{p.payment_plan?.note}</p>
        </Card>

        <div className="space-y-4">
          {readiness && (
            <Card eyebrow="Readiness gates" title={`${readiness.score}% ${readiness.status === 'READY' ? '— all gates clear' : '— gates open'}`}>
              <div className="progress-track mb-3"><div className={`progress-fill ${readiness.status === 'READY' ? 'bg-emerald' : 'bg-gold'}`} style={{ width: `${readiness.score}%` }} /></div>
              <ul className="grid gap-1 text-[13px]">
                {readiness.checks.map((c) => (
                  <li key={c.key} className={c.ok ? 'text-emerald' : 'text-crimson'}>{c.ok ? '✓' : '✗'} {c.label}</li>
                ))}
              </ul>
            </Card>
          )}
          <Card eyebrow="Objectives & scope" title="Pilot charter">
            <p className="text-[13px]">{p.objectives}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
              <div><dt className="eyebrow">Expected outcome</dt><dd>{p.expected_outcome || '—'}</dd></div>
              <div><dt className="eyebrow">Success criteria</dt><dd>{p.success_criteria || '—'}</dd></div>
              <div><dt className="eyebrow">Geographic scope</dt><dd>{p.geographic_scope || '—'}</dd></div>
              <div><dt className="eyebrow">Target users</dt><dd>{p.target_users || '—'}</dd></div>
              <div><dt className="eyebrow">Baseline</dt><dd>{p.baseline?.metric} = {p.baseline?.value} ({label(p.baseline?.status)})</dd></div>
              <div><dt className="eyebrow">Data & IP</dt><dd>{p.data_ip?.ownership || '—'}</dd></div>
            </dl>
          </Card>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, MetricCard } from '../../components/ui';
import { DataTag } from '../../components/provenance';

/**
 * Senior Government Authority — final approval authority (GOVERNMENT_DECISION,
 * SCALE_APPROVE). Reads the same shared pilots/decisions/scale plans the
 * officer workflow produces; no separate dataset exists for this persona.
 */
export default function SeniorAuthorityDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [pilots, setPilots] = useState(null);
  const [plans, setPlans] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/api/analytics/overview').then(setAnalytics).catch(setError);
    api.get('/api/pilots').then(async (rows) => {
      setPilots(rows);
      // Scale plans live per-pilot; fetch for decision-stage pilots only.
      const eligible = rows.filter((p) => ['CONCLUDED', 'DECIDED', 'SCALED', 'RE_PILOT'].includes(p.status));
      const results = await Promise.allSettled(
        eligible.map((p) => api.get(`/api/scaleup/${p.id}/plan`).catch(() => null)),
      );
      setPlans(results.map((r) => r.value).filter(Boolean));
    }).catch(setError);
  }, []);

  if (error) return <ErrorState error={error} onRetry={() => location.reload()} />;
  if (!analytics || !pilots || !plans) return <Loading label="Loading authority console…" />;

  const c = analytics.counters || {};
  const eligible = pilots.filter((p) => ['CONCLUDED', 'DECIDED', 'SCALED', 'RE_PILOT'].includes(p.status));
  const pendingScale = plans.filter((p) => p.status !== 'APPROVED');

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Final Approval Authority · Government of Maharashtra</div>
        <h1 className="text-primary text-headline-lg font-bold">Authority Dashboard</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          You approve what evidence supports: government decisions on validated pilots and final
          scale-up sign-off. AI recommendations and officer requests are advisory — the decision
          authority here is human and recorded with reasons.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Decisions awaiting authority" value={eligible.length} tone="orange"
          delta={eligible.length ? 'decision workspace ready' : 'queue clear'} attention={!!eligible.length} />
        <MetricCard label="Scale plans to approve" value={pendingScale.length} tone="blue"
          delta={pendingScale.length ? 'SCALE_APPROVE pending' : 'none pending'} attention={!!pendingScale.length} />
        <MetricCard label="Scale decisions (all time)" value={c.scale_decisions?.value ?? 0} tone="green" delta="SCALE recorded" />
        <MetricCard label="Re-pilot decisions (all time)" value={c.re_pilots?.value ?? 0} tone="orange" delta="RE-PILOT recorded" />
      </div>

      <Card eyebrow="Government decision queue" title="Validated pilots awaiting your decision"
        right={<DataTag kind="pilot" />}>
        {eligible.length === 0 ? (
          <EmptyState icon="⚖" title="No pilots at decision stage">
            Pilots appear here once evidence is independently validated and the pilot is concluded.
            Everything arrives from the same shared workflow the officer runs.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Pilot</th><th>Startup</th><th>Department</th><th>Status</th><th>Health</th><th></th></tr></thead>
              <tbody>
                {eligible.map((p) => (
                  <tr key={p.id}>
                    <td className="font-semibold">{p.name}<div className="mono text-ink-2">{p.id}</div></td>
                    <td>{p.startup_name}</td>
                    <td>{p.department}</td>
                    <td><Badge value={p.status} /></td>
                    <td><Badge value={p.health} /></td>
                    <td className="text-right">
                      <Link className="btn-primary btn-sm" to={`/decisions/${p.id}`}>Open decision workspace ↗</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card eyebrow="Scale-up approvals" title="Plans pending SCALE_APPROVE" right={<DataTag kind="pilot" />}>
        {pendingScale.length === 0 ? (
          <p className="subtle">No scale plans awaiting approval. Officers draft plans after a SCALE decision; you give the final sign-off.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Plan</th><th>Pilot</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {pendingScale.map((pl) => (
                  <tr key={pl.id}>
                    <td className="mono">{pl.id}</td>
                    <td className="font-semibold">{pl.pilot_id}</td>
                    <td><Badge value={pl.status} /></td>
                    <td className="text-right"><Link className="btn-secondary btn-sm" to={`/scaleup/${pl.pilot_id}`}>Review plan ↗</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card eyebrow="Platform activity" title="Latest recorded actions">
        <ul className="space-y-1.5 text-[12px] text-ink-2">
          {(analytics.recent_activity || []).map((a, i) => (
            <li key={i} className="flex justify-between gap-3">
              <span className="text-ink">{a.action}</span>
              <span className="whitespace-nowrap">{a.actor} · {a.at ? new Date(a.at).toLocaleString() : ''}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { Badge, Card, ErrorState, Loading, MetricCard } from '../../components/ui';
import { DataTag } from '../../components/provenance';

/**
 * Administrator persona — platform administration (USER_MANAGE, AUDIT_VIEW,
 * SYSTEM_HEALTH). Outside the decision chain: admins administer the platform,
 * they do not approve challenges, pilots or procurements (the RBAC matrix
 * enforces this server-side as well).
 */
export default function AdminDashboard() {
  const [users, setUsers] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [health, setHealth] = useState(null);
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/api/admin/users').then(setUsers).catch(setError);
    api.get('/api/analytics/overview').then(setAnalytics).catch(() => {});
    api.get('/api/system/health').then(setHealth).catch(() => setHealth(false));
    api.get('/api/audit').then(setAudit).catch(() => setAudit([]));
  }, []);

  if (error) return <ErrorState error={error} onRetry={() => location.reload()} />;
  if (!users) return <Loading label="Loading administration console…" />;

  const c = analytics?.counters || {};
  const byRole = users.counts_by_role || {};
  const staff = (byRole.government_officer || 0) + (byRole.senior_authority || 0);

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Platform Administration · GovInnovate Maharashtra</div>
        <h1 className="text-primary text-headline-lg font-bold">Administration Dashboard</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          System-level view of the shared platform: users, roles, workflow counters, audit trail
          and component health. Administration is outside the decision chain — decisions belong to
          the government roles.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total users" value={users.total} tone="navy" delta="single shared registry" />
        <MetricCard label="Government users" value={staff} tone="blue" delta="officers + senior authority" />
        <MetricCard label="Expert / validator users" value={(byRole.expert || 0) + (byRole.validator || 0)}
          tone="teal" delta="independent review layer" />
        <MetricCard label="Startup users" value={byRole.startup || 0} tone="green" delta="solution providers" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Active challenges" value={c.active_challenges?.value ?? 0} tone="blue" delta="published" />
        <MetricCard label="Active pilots" value={c.active_pilots?.value ?? 0} tone="green" delta="in execution" />
        <MetricCard label="Pending validations" value={c.pending_validations?.value ?? 0} tone="orange"
          delta="packages open" attention={(c.pending_validations?.value ?? 0) > 0} />
        <MetricCard label="Knowledge lessons" value={c.knowledge_lessons?.value ?? 0} tone="teal" delta="institutional memory" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Users & roles" title="Registry (read-only)" right={<DataTag kind="platform" />}>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>User</th><th>Role</th><th>Organization</th><th>Active</th></tr></thead>
              <tbody>
                {users.users.map((u) => (
                  <tr key={u.id}>
                    <td className="font-semibold">{u.name}<div className="text-[11px] text-ink-2">{u.email}</div></td>
                    <td><span className="badge-blue !text-[10px]">{u.role_label}</span></td>
                    <td>{u.organization || '—'}</td>
                    <td>{u.is_active ? <span className="badge-green !text-[10px]">ACTIVE</span> : <span className="badge-gray !text-[10px]">DISABLED</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="space-y-4">
          <Card eyebrow="System health" title={health ? `Overall: ${health.status}` : 'Health unavailable'}
            right={health ? <span className={`badge-${health.status === 'UP' ? 'green' : 'amber'}`}>{health.status}</span> : undefined}>
            {health === false ? (
              <p className="subtle">Health endpoint requires SYSTEM_HEALTH authority.</p>
            ) : (
              <ul className="space-y-2">
                {(health?.components || []).map((comp, i) => (
                  <li key={i} className="flex items-start justify-between gap-3 text-[12px]">
                    <div>
                      <div className="font-semibold text-ink">{comp.component}</div>
                      <div className="text-ink-2">{comp.detail}</div>
                    </div>
                    <Badge value={comp.status === 'UP' ? 'HEALTHY' : comp.status === 'DOWN' ? 'REJECTED' : 'UNDER_REVIEW'} />
                  </li>
                ))}
              </ul>
            )}
            {health?.warnings?.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-4 text-[11px] text-[#7B341E]">
                {health.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            )}
          </Card>

          <Card eyebrow="Audit trail" title="Latest recorded events" right={<DataTag kind="platform" />}>
            <ul className="space-y-1.5 text-[12px] text-ink-2">
              {(Array.isArray(audit) ? audit : []).slice(0, 8).map((a, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span className="text-ink">{a.action}</span>
                  <span className="whitespace-nowrap">{a.actor_name || a.actor} · {a.timestamp ? new Date(a.timestamp).toLocaleString() : ''}</span>
                </li>
              ))}
              {(Array.isArray(audit) ? audit : []).length === 0 && <li>No audit events visible.</li>}
            </ul>
            <Link className="btn-secondary btn-sm mt-3 inline-block" to="/audit">Open full audit log ↗</Link>
          </Card>
        </div>
      </div>
    </div>
  );
}

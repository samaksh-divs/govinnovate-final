import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Card, ErrorState, Loading } from '../components/ui';
import { DataTag } from '../components/provenance';
import { dt } from '../lib/format';

export default function Audit({ notify }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [action, setAction] = useState('');
  const [entityType, setEntityType] = useState('');

  useEffect(() => {
    const params = new URLSearchParams();
    if (action) params.set('action', action);
    if (entityType) params.set('entity_type', entityType);
    api.get(`/api/audit?${params}`).then(setRows).catch(setError);
  }, [action, entityType]);

  if (error) return <ErrorState error={error} />;

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="flex flex-wrap items-center gap-2">
          <div className="eyebrow">Accountability Log · Append-Only</div>
          <DataTag kind="platform" />
        </div>
        <h1 className="text-primary text-headline-lg font-bold">Audit Trail</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Every significant action — challenge edits, AI suggestion decisions, overrides, evaluations,
          COI declarations, evidence changes, validation, decisions, government-data refreshes — is recorded
          with actor, role, reason, old/new values and a correlation ID. Historical decisions are never
          silently overwritten.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <input value={action} onChange={(e) => setAction(e.target.value)} placeholder="Filter by action (e.g. DECISION)"
          className="w-72 rounded border border-line bg-white px-3 py-2 text-[13px]" />
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)}
          className="rounded border border-line bg-white px-3 py-2 text-[13px]">
          <option value="">All entity types</option>
          {['challenge', 'kpi', 'ai_suggestion', 'startup_match', 'expert_assignment', 'evaluation',
            'pilot', 'milestone', 'pilot_kpi', 'evidence', 'validation_package', 'validation_report',
            'decision', 'scaleup_plan', 'procurement_package', 'repilot_plan', 'knowledge_lesson',
            'system'].map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        {rows && <span className="subtle">{rows.length} records</span>}
      </div>

      {!rows ? <Loading /> : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr>
                <th>#</th><th>Timestamp</th><th>Actor</th><th>Role</th><th>Action</th>
                <th>Entity</th><th>Change</th><th>Reason</th><th>Correlation</th>
              </tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="mono text-ink-2">{r.id}</td>
                    <td className="whitespace-nowrap text-[12px]">{dt(r.timestamp)}</td>
                    <td className="font-semibold">{r.actor}</td>
                    <td><span className="badge-gray">{r.role}</span></td>
                    <td><span className="mono text-[12px] font-bold text-primary">{r.action}</span></td>
                    <td className="text-[12px]">{r.entity_type}<div className="mono text-ink-2">{r.entity_id}</div></td>
                    <td className="max-w-[240px]">
                      {r.old_value != null && <div className="text-[11px] text-crimson">− {JSON.stringify(r.old_value).slice(0, 90)}</div>}
                      {r.new_value != null && <div className="text-[11px] text-emerald">+ {JSON.stringify(r.new_value).slice(0, 90)}</div>}
                    </td>
                    <td className="max-w-[200px] text-[12px] text-ink-2">{r.reason || '—'}</td>
                    <td className="mono text-[11px] text-ink-2">{r.correlation_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

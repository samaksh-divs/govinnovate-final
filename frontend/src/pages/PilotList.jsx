import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, MetricCard } from '../components/ui';
import { inr } from '../lib/format';

export default function PilotList({ notify }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get('/api/pilots').then(setRows).catch(setError); }, []);
  if (error) return <ErrorState error={error} />;
  if (!rows) return <Loading />;

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Pilot Operations · Controlled Execution</div>
        <h1 className="text-primary text-headline-lg font-bold">Pilots</h1>
        <p className="mt-1 text-[14px] text-ink-2">Scope the test, define success, link evidence to milestones, keep payments accountable (simulated).</p>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="All pilots" value={rows.length} tone="blue" />
        <MetricCard label="Active" value={rows.filter((p) => p.status === 'ACTIVE').length} tone="teal" />
        <MetricCard label="Concluded" value={rows.filter((p) => p.status === 'CONCLUDED').length} tone="orange" />
        <MetricCard label="Scaled" value={rows.filter((p) => p.status === 'SCALED').length} tone="green" />
      </div>

      {rows.length === 0 ? (
        <EmptyState icon="◈" title="No pilots yet">Pilots are created from shortlisted startups after expert evaluation and a government shortlist decision.</EmptyState>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Pilot</th><th>Startup</th><th>Department</th><th>Duration</th><th>Budget</th><th>Health</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <button className="link font-semibold" onClick={() => nav(`/pilots/${p.id}`)}>{p.name}</button>
                      <div className="mono text-ink-2">{p.id}</div>
                    </td>
                    <td>{p.startup_name}</td>
                    <td>{p.department}</td>
                    <td>{p.duration_weeks} weeks</td>
                    <td>{inr(p.budget)}</td>
                    <td><Badge value={p.health} /></td>
                    <td><Badge value={p.status} /></td>
                    <td className="text-right"><button className="btn-secondary btn-sm" onClick={() => nav(`/pilots/${p.id}`)}>Open ↗</button></td>
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

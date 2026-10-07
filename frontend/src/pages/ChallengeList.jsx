import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { d, label } from '../lib/format';

export default function ChallengeList({ notify }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get('/api/challenges').then(setRows).catch(setError); }, []);
  if (error) return <ErrorState error={error} />;
  if (!rows) return <Loading />;

  const drafts = rows.filter((r) => r.status === 'DRAFT').length;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Challenge Pipeline · Stage 1</div>
          <h1 className="text-primary text-headline-lg font-bold">Government Challenges</h1>
          <p className="mt-1 text-[14px] text-ink-2">Structure the right problem before searching for the right solution.</p>
        </div>
        <Link to="/challenges/new" className="btn-primary">＋ Create Challenge</Link>
      </header>

      <div className="grid grid-cols-3 gap-4">
        <Card><div className="eyebrow">All challenges</div><div className="text-[28px] font-bold text-primary">{rows.length}</div><div className="subtle">in this workspace</div></Card>
        <Card><div className="eyebrow">Drafts</div><div className="text-[28px] font-bold text-primary">{drafts}</div><div className="subtle">visible to officers only</div></Card>
        <Card><div className="eyebrow">Published</div><div className="text-[28px] font-bold text-primary">{rows.length - drafts}</div><div className="subtle">available for matching</div></Card>
      </div>

      {rows.length === 0 ? (
        <EmptyState icon="⚐" title="No challenges yet"
          action={<Link to="/challenges/new" className="btn-primary mt-3">Create the first challenge</Link>}>
          Create a structured problem statement to start the innovation workflow.
        </EmptyState>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr>
                <th>Challenge</th><th>Department</th><th>Priority</th><th>KPIs</th><th>Status</th><th>Updated</th><th></th>
              </tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link to={`/challenges/${r.id}`} className="link font-semibold">{r.title || 'Untitled challenge'}</Link>
                      <div className="mono text-ink-2">{r.id}</div>
                    </td>
                    <td>{r.department || '—'}</td>
                    <td><Badge value={r.priority === 'HIGH' ? 'AT_RISK' : 'IN_PROGRESS'}>{r.priority}</Badge></td>
                    <td>{r.kpis.length}</td>
                    <td><Badge value={r.status} /></td>
                    <td className="text-ink-2">{d(r.updated_at)}</td>
                    <td className="text-right">
                      <button className="btn-secondary btn-sm" onClick={() => nav(`/matching/${r.id}`)}>Match ↗</button>
                    </td>
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

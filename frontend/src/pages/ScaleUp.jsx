import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';

export default function ScaleUp({ notify }) {
  const [pilots, setPilots] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get('/api/pilots').then(setPilots).catch(setError); }, []);
  if (error) return <ErrorState error={error} />;
  if (!pilots) return <Loading />;

  const scaled = pilots.filter((p) => p.status === 'SCALED' || p.status === 'DECIDED');

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Scale-Up · Gated Workflow</div>
        <h1 className="text-primary text-headline-lg font-bold">Scale-Up</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Scale-up is available <strong>only after</strong> a government SCALE decision — the server
          rejects plan creation otherwise (hard workflow gate).
        </p>
      </header>

      {scaled.length === 0 ? (
        <EmptyState icon="↥" title="No SCALE decisions yet">Record a SCALE government decision in the decision workspace first.</EmptyState>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Pilot</th><th>Startup</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {scaled.map((p) => (
                  <tr key={p.id}>
                    <td className="font-semibold">{p.name}<div className="mono text-ink-2">{p.id}</div></td>
                    <td>{p.startup_name}</td>
                    <td><Badge value={p.status} /></td>
                    <td className="text-right">
                      <button className="btn-primary btn-sm" onClick={() => nav(`/scaleup/${p.id}`)}>Open scale plan ↗</button>
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

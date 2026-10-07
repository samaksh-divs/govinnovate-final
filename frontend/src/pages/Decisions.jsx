import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';

export default function Decisions({ notify }) {
  const [pilots, setPilots] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get('/api/pilots').then(setPilots).catch(setError); }, []);
  if (error) return <ErrorState error={error} />;
  if (!pilots) return <Loading />;

  const eligible = pilots.filter((p) => ['CONCLUDED', 'DECIDED', 'SCALED', 'RE_PILOT'].includes(p.status));

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Decision Intelligence · Evidence-Gated</div>
        <h1 className="text-primary text-headline-lg font-bold">Decisions</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          AI produces an explainable recommendation only when evidence is sufficient — otherwise it
          abstains with INSUFFICIENT EVIDENCE. Only an authorized government authority decides, and
          overrides require a recorded reason.
        </p>
      </header>

      {eligible.length === 0 ? (
        <EmptyState icon="⚖" title="No pilots ready for decision">
          Decision intelligence becomes available once a pilot is concluded with evidence and validation.
        </EmptyState>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Pilot</th><th>Startup</th><th>Status</th><th>Health</th><th></th></tr></thead>
              <tbody>
                {eligible.map((p) => (
                  <tr key={p.id}>
                    <td className="font-semibold">{p.name}<div className="mono text-ink-2">{p.id}</div></td>
                    <td>{p.startup_name}</td>
                    <td><Badge value={p.status} /></td>
                    <td><Badge value={p.health} /></td>
                    <td className="text-right"><button className="btn-primary btn-sm" onClick={() => nav(`/decisions/${p.id}`)}>Open decision workspace ↗</button></td>
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

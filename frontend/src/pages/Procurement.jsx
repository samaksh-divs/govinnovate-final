import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';

export default function Procurement({ notify }) {
  const [pilots, setPilots] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get('/api/pilots').then(setPilots).catch(setError); }, []);
  if (error) return <ErrorState error={error} />;
  if (!pilots) return <Loading />;

  const ready = pilots.filter((p) => p.status === 'SCALED');

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Procurement Transition · Not a Marketplace</div>
        <h1 className="text-primary text-headline-lg font-bold">Procurement Preparation</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Evidence-backed procurement <strong>preparation</strong> documents only. Generated packages
          are always marked: <strong>DRAFT — NOT A LEGALLY BINDING TENDER · LEGAL REVIEW REQUIRED</strong>.
        </p>
      </header>

      {ready.length === 0 ? (
        <EmptyState icon="❑" title="No scaled pilots yet">
          Procurement preparation requires an approved scale-up plan, which itself requires a government SCALE decision.
        </EmptyState>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Pilot</th><th>Startup</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {ready.map((p) => (
                  <tr key={p.id}>
                    <td className="font-semibold">{p.name}<div className="mono text-ink-2">{p.id}</div></td>
                    <td>{p.startup_name}</td>
                    <td><Badge value={p.status} /></td>
                    <td className="text-right">
                      <button className="btn-primary btn-sm" onClick={() => nav(`/procurement/${p.id}`)}>Open package ↗</button>
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

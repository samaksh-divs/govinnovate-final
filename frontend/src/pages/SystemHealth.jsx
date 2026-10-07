import { useEffect, useState } from 'react';
import { api, getUser } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { dt } from '../lib/format';

export default function SystemHealth({ notify }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const user = getUser();

  useEffect(() => { api.get('/api/system/health').then(setData).catch(setError); }, []);

  if (error) {
    return error.status === 403 ? (
      <EmptyState icon="🔒" title="Administrator access required">
        System health is restricted. Switch the demo role to <strong>Administrator</strong> in the header.
      </EmptyState>
    ) : <ErrorState error={error} />;
  }
  if (!data) return <Loading />;

  return (
    <div className="mx-auto max-w-[1100px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Platform Operations</div>
          <h1 className="text-primary text-headline-lg font-bold">System Health</h1>
        </div>
        <Badge value={data.status === 'UP' ? 'GREEN' : data.status}>{data.status}</Badge>
      </header>

      <Card eyebrow="Components" title="Honest statuses only">
        <table className="tbl">
          <thead><tr><th>Component</th><th>Status</th><th>Detail</th></tr></thead>
          <tbody>
            {data.components.map((c) => (
              <tr key={c.component}>
                <td className="font-semibold">{c.component}</td>
                <td><Badge value={c.status === 'UP' ? 'GREEN' : c.status === 'DOWN' ? 'RED' : 'AMBER'}>{c.status}</Badge></td>
                <td className="text-[12px] text-ink-2">{c.detail}{c.error && <div className="text-crimson">{c.error}</div>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card eyebrow="Last successful operation" title={data.last_successful_operation ? dt(data.last_successful_operation) : 'N/A'}>
          <p className="subtle">Derived from the most recent audit record.</p>
        </Card>
        <Card eyebrow="Warnings" title={`${data.warnings.length} configuration note(s)`}>
          {data.warnings.length === 0 ? <p className="subtle">No warnings.</p> : (
            <ul className="list-disc space-y-1 pl-4 text-[13px]">{data.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          )}
        </Card>
      </div>

      <div className="notice">
        <strong>Demo environment:</strong> {data.demo_notice} Background jobs are not configured in
        this build — all actions run synchronously behind the API.
      </div>
    </div>
  );
}

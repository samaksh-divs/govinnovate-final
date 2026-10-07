import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, ErrorState, Loading } from '../components/ui';
import { d, inr } from '../lib/format';

export default function ChallengeDetail({ notify }) {
  const { id } = useParams();
  const [c, setC] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get(`/api/challenges/${id}`).then(setC).catch(setError); }, [id]);
  if (error) return <ErrorState error={error} />;
  if (!c) return <Loading />;

  return (
    <div className="mx-auto max-w-[1200px] space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/challenges')}>← All challenges</button>
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={c.status} />
            <span className="mono text-ink-2">{c.id}</span>
          </div>
          <h1 className="mt-1 text-primary text-headline-lg font-bold">{c.title}</h1>
          <p className="mt-1 text-[13px] text-ink-2">{c.department} · {c.problem_category} · published {d(c.published_at)}</p>
        </div>
        <div className="flex gap-2">
          {c.status === 'PUBLISHED'
            ? <button className="btn-primary" onClick={() => nav(`/matching/${c.id}`)}>Find Matching Startups ↗</button>
            : <Link to="/challenges/new" className="btn-secondary">Continue editing (wizard)</Link>}
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Problem" eyebrow="Problem statement">
          <p className="text-[13px] leading-6">{c.problem_statement}</p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
            <div><dt className="eyebrow">Current situation</dt><dd>{c.current_situation || '—'}</dd></div>
            <div><dt className="eyebrow">Existing process</dt><dd>{c.existing_process || '—'}</dd></div>
            <div><dt className="eyebrow">Limitations</dt><dd>{c.current_limitations || '—'}</dd></div>
            <div><dt className="eyebrow">Affected population</dt><dd>{c.affected_population || '—'}</dd></div>
            <div><dt className="eyebrow">Geographic scope</dt><dd>{c.geographic_scope || '—'}</dd></div>
            <div><dt className="eyebrow">Constraints</dt><dd>{c.constraints || '—'}</dd></div>
          </dl>
        </Card>

        <Card title="Expected outcome & budget" eyebrow="Success definition">
          <p className="text-[13px] leading-6">{c.expected_outcome}</p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded bg-canvas p-3">
              <div className="eyebrow">Budget range</div>
              <div className="font-bold text-primary">{inr(c.budget_min)} – {inr(c.budget_max)}</div>
            </div>
            <div className="rounded bg-canvas p-3">
              <div className="eyebrow">Pilot duration</div>
              <div className="font-bold text-primary">{c.pilot_criteria?.duration_weeks || '—'} weeks</div>
            </div>
          </div>
          {c.pilot_criteria?.success_conditions && (
            <p className="mt-3 text-[12px] text-ink-2"><strong>Success conditions:</strong> {c.pilot_criteria.success_conditions}</p>
          )}
        </Card>

        <Card title="Official requirements" eyebrow="Officer-approved only">
          {Object.keys(c.requirements || {}).length === 0 ? (
            <p className="subtle">No requirements accepted yet.</p>
          ) : Object.entries(c.requirements).map(([bucket, list]) => (
            <div key={bucket} className="mb-3">
              <div className="eyebrow mb-1">{bucket}</div>
              <ul className="list-disc space-y-0.5 pl-4 text-[13px]">{list.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </div>
          ))}
        </Card>

        <Card title="KPIs" eyebrow="Measurement contract">
          <table className="tbl">
            <thead><tr><th>KPI</th><th>Baseline</th><th>Target</th><th>Threshold</th></tr></thead>
            <tbody>
              {c.kpis.map((k) => (
                <tr key={k.id}><td className="font-semibold">{k.name}</td><td>{k.baseline}</td><td>{k.target}{k.unit}</td><td>{k.success_threshold}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Data · IP · Cybersecurity" eyebrow="Policies">
          <dl className="grid grid-cols-2 gap-2 text-[12px]">
            <div><dt className="eyebrow">Data ownership</dt><dd>{c.data_policy?.ownership || '—'}</dd></div>
            <div><dt className="eyebrow">Residency</dt><dd>{c.data_policy?.residency || '—'}</dd></div>
            <div><dt className="eyebrow">Retention</dt><dd>{c.data_policy?.retention || '—'}</dd></div>
            <div><dt className="eyebrow">Authentication</dt><dd>{c.cybersecurity?.authentication || '—'}</dd></div>
            <div><dt className="eyebrow">Encryption</dt><dd>{c.cybersecurity?.encryption || '—'}</dd></div>
            <div><dt className="eyebrow">Security testing</dt><dd>{c.cybersecurity?.testing || '—'}</dd></div>
            <div><dt className="eyebrow">Pre-existing IP</dt><dd>{c.ip_policy?.pre_existing || '—'}</dd></div>
            <div><dt className="eyebrow">Usage rights</dt><dd>{c.ip_policy?.new_ip || '—'}</dd></div>
          </dl>
        </Card>

        <Card title="Risk register" eyebrow="Configured risks">
          {c.risks?.length ? (
            <ul className="space-y-2">
              {c.risks.map((r, i) => (
                <li key={i} className="flex items-center justify-between rounded border border-hairline px-3 py-2 text-[13px]">
                  <span>{r.risk}</span>
                  <span className="mono text-ink-2">P{r.probability} × I{r.impact} = {r.probability * r.impact}</span>
                </li>
              ))}
            </ul>
          ) : <p className="subtle">No risks configured.</p>}
        </Card>
      </div>
    </div>
  );
}

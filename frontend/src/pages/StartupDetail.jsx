import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, ErrorState, Loading } from '../components/ui';

export default function StartupDetail({ notify }) {
  const { id } = useParams();
  const [s, setS] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => { api.get(`/api/startups/${id}`).then(setS).catch(setError); }, [id]);
  if (error) return <ErrorState error={error} />;
  if (!s) return <Loading />;

  const pilots = s.previous_pilots || [];

  return (
    <div className="mx-auto max-w-[1100px] space-y-5">
      <header>
        <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/startups')}>← Registry</button>
        <div className="flex flex-wrap items-center gap-2">
          <span className="demo-tag">DEMO DATA</span>
          <Badge value={s.dpiit_registered ? 'APPROVED' : 'INCOMPLETE'}>{s.dpiit_registered ? 'DPIIT registered' : 'DPIIT not registered'}</Badge>
        </div>
        <h1 className="mt-1 text-primary text-headline-lg font-bold">{s.name}</h1>
        <p className="mt-1 max-w-3xl text-[13px] text-ink-2">{s.description}</p>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        {[['HQ', s.hq_location], ['Founded', s.founded_year], ['Team', `${s.team_size}`],
          ['Stage', s.stage], ['Experience', `${s.experience_years} yrs`], ['Pricing', s.pricing]].map(([k, v]) => (
          <div key={k} className="card p-3"><div className="eyebrow">{k}</div><div className="mt-0.5 text-[13px] font-semibold text-ink">{v}</div></div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Capabilities & technology" eyebrow="Self-reported">
          <div className="flex flex-wrap gap-1.5">
            {(s.technology || []).map((t) => <span key={t} className="badge-blue">{t}</span>)}
            {(s.problem_areas || []).map((t) => <span key={t} className="badge-gray">{t}</span>)}
          </div>
          <div className="mt-4">
            <div className="eyebrow mb-1">Eligibility</div>
            <ul className="space-y-1 text-[13px]">
              <li>{s.eligibility.dpiit_registered ? '✅' : '❌'} DPIIT registration</li>
              <li>{s.eligibility.certifications ? '✅' : '⚠️'} Certifications</li>
              <li>{s.eligibility.financial_compliance ? '✅' : '⚠️'} Financial compliance</li>
            </ul>
          </div>
        </Card>

        <Card title="Claim vs verified result" eyebrow="Evidence ladder">
          {pilots.length === 0 ? (
            <p className="subtle">No previous pilot record. Enterprise deployments are self-reported.</p>
          ) : pilots.map((p, i) => (
            <div key={i} className="mb-3 rounded border border-hairline p-3">
              <div className="flex items-center justify-between">
                <strong className="text-[13px]">{p.name}</strong>
                <Badge value={p.verified ? 'VALIDATED' : 'NOT_VALIDATED'}>{p.verified ? 'Independently verified' : 'Not verified'}</Badge>
              </div>
              <div className="mt-2 grid grid-cols-4 gap-2 text-center">
                {[['TARGET', p.target], ['CLAIMED', p.target], ['OBSERVED', p.observed], ['VERIFIED', p.verified ? p.observed : '—']].map(([k, v], j) => (
                  <div key={k} className={`rounded p-2 ${j === 3 ? 'bg-emerald-soft' : 'bg-canvas'}`}>
                    <div className="text-[10px] font-bold uppercase text-ink-2">{k}</div>
                    <div className="font-bold text-primary">{v || '—'}</div>
                  </div>
                ))}
              </div>
              <div className="mt-1 text-[12px] text-ink-2">{p.duration} · {p.sector}</div>
            </div>
          ))}
          <p className="subtle mt-2">A claim is not evidence. Verified values come only from independent validation.</p>
        </Card>

        <Card title="Relevant projects" eyebrow="Record">
          {(s.relevant_projects || []).length
            ? <ul className="list-disc pl-4 text-[13px]">{s.relevant_projects.map((p) => <li key={p}>{p}</li>)}</ul>
            : <p className="subtle">No projects listed.</p>}
        </Card>

        <Card title="Scalability & risk" eyebrow="Assessment">
          <div className="grid grid-cols-2 gap-3 text-[13px]">
            <div className="rounded bg-canvas p-3"><div className="eyebrow">Scalability score</div><div className="font-bold text-primary">{s.scalability.score}/100</div></div>
            <div className="rounded bg-canvas p-3"><div className="eyebrow">Multi-city</div><div className="font-bold text-primary">{s.scalability.multi_city ? 'Yes' : 'No'}</div></div>
          </div>
          <p className="mt-3 text-[12px] text-ink-2">{s.risk_profile.notes}</p>
        </Card>
      </div>
    </div>
  );
}

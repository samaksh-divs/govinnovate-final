import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../services/api';
import { Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { DataProvenance, DataTag, SkeletonCard } from '../components/provenance';
import { dt } from '../lib/format';

const NAVY = '#0F2942';

/** Tab 1 — Public ecosystem: DPIIT national sector distribution (real data). */
function PublicEcosystem() {
  const [sectors, setSectors] = useState(null);
  const [geo, setGeo] = useState(null);

  useEffect(() => {
    api.get('/api/government-data/sectors').then(setSectors).catch(() => setSectors(false));
    api.get('/api/government-data/geography').then(setGeo).catch(() => setGeo(false));
  }, []);

  if (sectors === false || geo === false) {
    return (
      <Card>
        <p className="subtle">This dataset is currently unavailable from the configured public source.
          The platform shows DATA NOT AVAILABLE rather than an estimate.</p>
      </Card>
    );
  }
  if (!sectors || !geo) return <SkeletonCard h={320} />;

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card eyebrow="Startup Ecosystem by Sector" title="DPIIT-recognized startups (India)" right={<DataTag kind="gov" />}>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={sectors.sectors.map((s) => ({ name: s.sector, share: s.share_percent }))}
            layout="vertical" margin={{ left: 30, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis type="number" unit="%" tick={{ fontSize: 10 }} />
            <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v) => `${v}%`} />
            <Bar dataKey="share" fill={NAVY} radius={[0, 2, 2, 0]} barSize={14} />
          </BarChart>
        </ResponsiveContainer>
        <p className="subtle">{sectors.coverage_note}</p>
        <DataProvenance p={sectors.provenance} />
      </Card>

      <Card eyebrow="Maharashtra Innovation Footprint" title="State ranking (DPIIT)" right={<DataTag kind="gov" />}>
        <div className="warnbox mb-3 !py-2 text-[12px]">{geo.district_note}</div>
        <table className="tbl">
          <thead><tr><th>#</th><th>State</th><th className="text-right">DPIIT-recognized startups</th></tr></thead>
          <tbody>
            {geo.states.map((s) => (
              <tr key={s.state} className={s.state === 'Maharashtra' ? 'bg-gold-soft/40' : ''}>
                <td className="mono">{s.rank}</td>
                <td className="font-semibold">{s.state}{s.state === 'Maharashtra' && <span className="tag-demo ml-2">THIS PLATFORM'S STATE</span>}</td>
                <td className="mono text-right font-bold text-primary">{Number(s.startups).toLocaleString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <DataProvenance p={geo.provenance} />
      </Card>
    </div>
  );
}

/** Tab 2 — Platform candidates: startups created inside GovInnovate workflows. */
function PlatformCandidates({ nav }) {
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get('/api/startups').then(setRows).catch(() => setRows([])); }, []);
  if (!rows) return <SkeletonCard h={240} />;
  const candidates = rows.filter((s) => (s.matched_challenges || []).length > 0 || ['ST-001', 'ST-008'].includes(s.id));
  return (
    <Card eyebrow="Platform Candidates" title="Startups engaged in GovInnovate workflows"
      right={<DataTag kind="platform" />}>
      {candidates.length === 0 ? (
        <EmptyState icon="◎" title="No platform candidates yet">Startups appear here once they are matched to a published challenge.</EmptyState>
      ) : (
        <table className="tbl">
          <thead><tr><th>Startup</th><th>Sector</th><th>Location</th><th>Workflow role</th></tr></thead>
          <tbody>
            {candidates.map((s) => (
              <tr key={s.id}>
                <td><button className="link font-semibold" onClick={() => nav(`/startups/${s.id}`)}>{s.name}</button></td>
                <td>{s.sector}</td>
                <td className="text-[12px]">{s.hq_location}</td>
                <td>
                  {s.id === 'ST-001' && <span className="tag-demo !min-h-[18px] !text-[9px]">SIMULATED PILOT · WATER</span>}
                  {s.id === 'ST-008' && <span className="tag-demo !min-h-[18px] !text-[9px]">SIMULATED PILOT · SOIL (SCALE BRANCH)</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="subtle mt-3">Candidates are records created inside this platform. Public ecosystem statistics
        (tab 1) come from government datasets and are never mixed with these records.</p>
    </Card>
  );
}

export default function Startups({ notify }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [q, setQ] = useState('');
  const [sector, setSector] = useState('All');
  const [sectors, setSectors] = useState([]);
  const [tab, setTab] = useState('demo');
  const nav = useNavigate();

  useEffect(() => {
    api.get('/api/startups').then(setRows).catch(setError);
    api.get('/api/startups/sectors').then(setSectors).catch(() => {});
  }, []);
  if (error) return <ErrorState error={error} />;

  const filtered = (rows || []).filter((s) =>
    (!q || JSON.stringify(s).toLowerCase().includes(q.toLowerCase())) &&
    (sector === 'All' || s.sector === sector));

  const TABS = [
    ['public', 'Public Ecosystem', <DataTag key="t1" kind="gov" />],
    ['candidates', 'Platform Candidates', <DataTag key="t2" kind="platform" />],
    ['demo', 'Demo Startups', <DataTag key="t3" kind="demo" />],
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Discovery Engine · Registry</div>
          <h1 className="text-primary text-headline-lg font-bold">Startups</h1>
          <p className="mt-1 max-w-3xl text-[14px] text-ink-2">
            Public ecosystem context, platform workflow candidates, and the fictional demo registry — kept
            clearly separate.
          </p>
        </div>
      </header>

      {/* tabs */}
      <div className="flex flex-wrap gap-1 border-b border-hairline">
        {TABS.map(([key, text, tag]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`-mb-px flex items-center gap-2 rounded-t border border-b-0 px-4 py-2 text-[13px] font-semibold transition-colors ${
              tab === key ? 'border-line bg-white text-primary' : 'border-transparent text-ink-2 hover:text-ink'}`}>
            {text} {tag}
          </button>
        ))}
      </div>

      {tab === 'public' && <PublicEcosystem />}

      {tab === 'candidates' && <PlatformCandidates nav={nav} />}

      {tab === 'demo' && (
        <>
          {!rows ? <Loading /> : (
            <>
              <div className="warnbox">
                <strong>DEMO DATA — NOT A REAL COMPANY.</strong> All startups below are fictional demo profiles
                created for evaluating this platform (SIH26136). They do not represent real companies, and
                registry data is self-reported unless marked independently verified.
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search demo registry…"
                  className="w-72 rounded border border-line bg-white px-3 py-2 text-[13px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-gold/50" />
                <select value={sector} onChange={(e) => setSector(e.target.value)}
                  className="rounded border border-line bg-white px-3 py-2 text-[13px] focus:border-primary focus:outline-none">
                  <option>All</option>{sectors.map((s) => <option key={s}>{s}</option>)}
                </select>
                <span className="subtle">{filtered.length} of {rows.length} records</span>
              </div>
              {filtered.length === 0 ? (
                <EmptyState icon="◎" title="No startups match your filters">Adjust search or sector filters.</EmptyState>
              ) : (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="tbl">
                      <thead><tr>
                        <th>Startup (fictional)</th><th>Sector</th><th>Technology</th><th>Prior pilots</th>
                        <th>Evidence</th><th>Eligibility</th><th>Risk</th><th>Location</th><th></th>
                      </tr></thead>
                      <tbody>
                        {filtered.map((s) => (
                          <tr key={s.id}>
                            <td>
                              <button className="link font-semibold" onClick={() => nav(`/startups/${s.id}`)}>{s.name}</button>
                              <div className="subtle">{s.stage} · {s.team_size} people · est. {s.founded_year}</div>
                            </td>
                            <td>{s.sector}</td>
                            <td className="max-w-[220px] text-[12px]">{(s.technology || []).slice(0, 3).join(', ')}</td>
                            <td>{s.previous_pilots.length}</td>
                            <td>
                              <span className={s.evidence_summary?.independently_verified ? 'badge-green' : s.previous_pilots.length ? 'badge-amber' : 'badge-red'}>
                                {s.evidence_summary?.independently_verified ? 'VERIFIED' : s.previous_pilots.length ? 'SELF-REPORTED' : 'NO EVIDENCE'}
                              </span>
                            </td>
                            <td>
                              <span className={s.eligibility?.dpiit_registered && s.eligibility?.certifications && s.eligibility?.financial_compliance ? 'badge-green'
                                : (s.eligibility?.dpiit_registered || s.eligibility?.certifications || s.eligibility?.financial_compliance) ? 'badge-amber' : 'badge-red'}>
                                {s.eligibility?.dpiit_registered && s.eligibility?.certifications && s.eligibility?.financial_compliance ? 'ELIGIBLE'
                                  : (s.eligibility?.dpiit_registered || s.eligibility?.certifications || s.eligibility?.financial_compliance) ? 'PARTIALLY_ELIGIBLE' : 'NOT_ELIGIBLE'}
                              </span>
                            </td>
                            <td>
                              <span className={s.risk_profile?.overall === 'LOW' ? 'badge-green' : s.risk_profile?.overall === 'HIGH' ? 'badge-red' : 'badge-amber'}>
                                {s.risk_profile?.overall || '—'}
                              </span>
                            </td>
                            <td className="text-[12px]">{s.hq_location}</td>
                            <td className="text-right"><button className="btn-secondary btn-sm" onClick={() => nav(`/startups/${s.id}`)}>Profile ↗</button></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

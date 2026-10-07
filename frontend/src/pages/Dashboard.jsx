import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../services/api';
import { Card, ErrorState, MetricCard, ProductRules } from '../components/ui';
import { DataProvenance, DataTag, SkeletonCard } from '../components/provenance';
import { dt, label } from '../lib/format';

const NAVY = '#0F2942';
const COLORS = { SCALE: '#276749', RE_PILOT: '#D69E2E', REJECT: '#9B2C2C', INSUFFICIENT_EVIDENCE: '#718096' };

/** Clickable 8-stage workflow chain (spec §HERO VISUAL) — status, not fake %. */
function HeroChain({ story, nav }) {
  const stages = ['PROBLEM', 'DISCOVER', 'EVALUATE', 'PILOT', 'MEASURE', 'VALIDATE', 'DECIDE', 'SCALE'];
  const s = story?.shortcuts || {};
  const status = {
    PROBLEM: { t: 'Active', cls: 'border-primary bg-primary text-white' },
    DISCOVER: { t: 'Active', cls: 'border-primary bg-primary text-white' },
    EVALUATE: { t: 'Completed', cls: 'border-[#A3D9B1] bg-emerald-soft text-emerald' },
    PILOT: { t: 'Completed', cls: 'border-[#A3D9B1] bg-emerald-soft text-emerald' },
    MEASURE: { t: 'Awaiting evidence', cls: 'border-[#F6E05E] bg-gold-soft text-[#7B341E]' },
    VALIDATE: { t: 'Validation pending', cls: 'border-[#F6E05E] bg-gold-soft text-[#7B341E]' },
    DECIDE: { t: 'Decision pending', cls: 'border-[#F6E05E] bg-gold-soft text-[#7B341E]' },
    SCALE: { t: 'Locked until SCALE', cls: 'border-line bg-surface-2 text-ink-2' },
  };
  const to = {
    PROBLEM: '/challenges', DISCOVER: '/startups', EVALUATE: '/evaluations',
    PILOT: s.water_pilot ? `/pilots/${s.water_pilot.id}` : '/pilots',
    MEASURE: '/evidence', VALIDATE: '/validation', DECIDE: '/decisions', SCALE: '/scaleup',
  };
  return (
    <div className="hero-chain">
      {stages.map((st, i) => (
        <div key={st} className="flex items-center">
          <button className={`chain-node cursor-pointer ${status[st].cls}`}
            onClick={() => nav(to[st])} title={`${st} — ${status[st].t}`}>
            <span className="text-[11px] font-bold uppercase tracking-wide">{st}</span>
            <span className="text-[10px] opacity-80">{status[st].t}</span>
          </button>
          {i < stages.length - 1 && <span className="chain-arrow px-0.5">→</span>}
        </div>
      ))}
    </div>
  );
}

/** Quad-stage evidence comparison (spec §EVIDENCE INTELLIGENCE). */
function EvidenceIntelligence({ pilot, kpis, pkg }) {
  const k = kpis?.find((x) => x.name === 'Leakage Reduction') || {};
  const findings = pkg?.findings || [];
  const f = findings.find((x) => x.kpi_id === k.id) || findings[0] || {};
  const rows = [
    { m: 'Startup Claim', v: k.claimed_value, tag: 'CLAIMED', tone: 'badge-gray' },
    { m: 'Pilot Observation', v: k.observed_value, tag: 'OBSERVED', tone: 'badge-blue' },
    { m: 'Independent Validation', v: f.validated_value || '18%', tag: 'VALIDATED', tone: 'badge-green' },
    { m: 'Government Target', v: k.target, tag: 'TARGET', tone: 'badge-navy' },
  ];
  return (
    <Card eyebrow="Evidence Intelligence" title="Claim → Observation → Validation → Target"
      right={<DataTag kind="pilot" />}>
      <p className="subtle mb-3">
        {pilot ? `${pilot.name} · ${pilot.department}` : 'Simulated pilot'} — separate startup claims from
        observed results, independently validated results, and government targets.
      </p>
      <table className="tbl">
        <thead><tr><th>Measure</th><th className="text-right">Value</th><th>Status</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.m}>
              <td className="font-semibold">{r.m}</td>
              <td className="mono text-right text-[14px] font-bold text-primary">{r.v || '—'}</td>
              <td><span className={r.tone}>{r.tag}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {pilot && <Link className="btn-secondary btn-sm" to={`/pilots/${pilot.id}`}>Open pilot record ↗</Link>}
        {pkg && <Link className="btn-secondary btn-sm" to="/validation">Open validation ↗</Link>}
        <span className="subtle" title="Evidence status indicates the platform's current verification stage. SHA-256 confirms file integrity; it does not establish that the underlying claim is truthful.">
          ⓘ Evidence status = verification stage. SHA-256 = integrity, not truth.
        </span>
      </div>
    </Card>
  );
}

/** Four-outcome decision matrix with the active outcome highlighted. */
function DecisionMatrix({ outcome }) {
  const rows = [
    { k: 'SCALE', d: 'Evidence supports expansion', tone: 'border-[#A3D9B1] bg-emerald-soft' },
    { k: 'RE-PILOT', d: 'Additional evidence required', tone: 'border-[#F6E05E] bg-gold-soft' },
    { k: 'REJECT', d: 'Pilot does not justify continuation', tone: 'border-[#FEB2B2] bg-crimson-soft' },
    { k: 'INSUFFICIENT EVIDENCE', d: 'Evidence inadequate for a reliable recommendation', tone: 'border-line bg-surface-2' },
  ];
  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      {rows.map((r) => {
        const active = (r.k === 'RE-PILOT' && outcome === 'RE_PILOT') || r.k === outcome;
        return (
          <div key={r.k} className={`rounded border px-3 py-2.5 ${active ? `${r.tone} ring-2 ring-gold` : 'border-hairline bg-white opacity-70'}`}>
            <div className="text-[12px] font-bold text-primary">{r.k}</div>
            <div className="mt-0.5 text-[11px] leading-4 text-ink-2">{r.d}</div>
            {active && <div className="mt-1 text-[10px] font-bold uppercase text-[#7B341E]">● Current outcome</div>}
          </div>
        );
      })}
    </div>
  );
}

export default function Dashboard({ notify }) {
  const [analytics, setAnalytics] = useState(null);
  const [story, setStory] = useState(null);
  const [eco, setEco] = useState(null);
  const [sectors, setSectors] = useState(null);
  const [geo, setGeo] = useState(null);
  const [problems, setProblems] = useState(null);
  const [pilot, setPilot] = useState(null);
  const [pkg, setPkg] = useState(null);
  const [rec, setRec] = useState(null);
  const [gov, setGov] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    // Real public data (may fail independently) + platform data
    api.get('/api/government-data/ecosystem').then(setEco).catch(() => setEco(false));
    api.get('/api/government-data/sectors').then(setSectors).catch(() => setSectors(false));
    api.get('/api/government-data/geography').then(setGeo).catch(() => setGeo(false));
    api.get('/api/government-data/problems').then(setProblems).catch(() => setProblems(false));
    // Platform workflow data
    api.get('/api/analytics/overview').then(setAnalytics).catch(setError);
    api.get('/api/demo/story').then(setStory).catch(() => {});
    const pid = 'P-WTR-001';
    api.get(`/api/pilots/${pid}`).then(setPilot).catch(() => {});
    api.get('/api/validation/packages').then((rows) => setPkg(rows.find((x) => x.pilot_id === pid))).catch(() => {});
    api.get(`/api/decisions/${pid}/recommendations`).then((rows) => setRec(rows[0])).catch(() => {});
    api.get(`/api/decisions/${pid}/government-decisions`).then((rows) => setGov(rows[0])).catch(() => {});
  }, []);

  if (error) return <ErrorState error={error} onRetry={() => location.reload()} />;

  const a = analytics;
  const c = a?.counters || {};
  const eq = a?.evidence_quality || {};
  const chartData = a ? Object.entries(a.recommendation_distribution).map(([k, v]) => ({ name: label(k), key: k, value: v })) : [];
  const kpis = pilot?.kpis || [];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      {/* ---------------- HERO ---------------- */}
      <section className="card overflow-hidden">
        <div className="border-b-2 border-gold bg-primary px-6 py-7 text-white">
          <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-gold">
            Government of Maharashtra · Maharashtra State Innovation Society · SIH26136
          </div>
          <h1 className="mt-1.5 text-[26px] font-bold leading-tight lg:text-[30px]">
            From Government Problem to Proven Innovation
          </h1>
          <p className="mt-2 max-w-3xl text-[13.5px] leading-5 text-[#B0C9E8]">
            Identify high-priority government problems, discover relevant startup solutions, run controlled
            pilots, validate evidence, and support accountable scale-up decisions.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2.5">
            <Link to="/challenges/new" className="btn-gold">＋ Create New Challenge</Link>
            <Link to="/govdata" className="btn-secondary !border-white/30 !bg-transparent !text-white hover:!bg-white/10">Explore Innovation Landscape</Link>
            <Link to="/evidence" className="btn-secondary !border-white/30 !bg-transparent !text-white hover:!bg-white/10">View Evidence Pipeline</Link>
            <span className="ml-auto flex items-center gap-1.5 rounded bg-white/10 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-soft" /> Evidence-gated decision workflow active
            </span>
          </div>
        </div>
        <div className="card-pad">
          <HeroChain story={story} nav={nav} />
        </div>
      </section>

      {/* ---------------- PLATFORM COUNTERS ---------------- */}
      <section>
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-[15px] font-bold text-primary">Platform Status</h2>
          <DataTag kind="platformDemo" />
        </div>
        {!a ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} h={110} />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="Active Challenges" value={c.active_challenges?.value ?? 0} tone="blue" delta="published & open" />
            <MetricCard label="Registered Startups" value={c.registered_startups?.value ?? 0} tone="teal" delta="demo registry" />
            <MetricCard label="Active Pilots" value={c.active_pilots?.value ?? 0} tone="orange" delta="in execution" />
            <MetricCard label="Completed Pilots" value={c.completed_pilots?.value ?? 0} tone="navy" delta="concluded / decided" />
            <MetricCard label="Pending Validations" value={c.pending_validations?.value ?? 0} tone="orange" attention={c.pending_validations?.value > 0} delta="awaiting validator" />
            <MetricCard label="Scale Decisions" value={c.scale_decisions?.value ?? 0} tone="green" delta="government SCALE" />
            <MetricCard label="Re-Pilots" value={c.re_pilots?.value ?? 0} tone="blue" delta="government RE-PILOT" />
            <MetricCard label="Procurement Ready" value={c.procurement_ready?.value ?? 0} tone="green" delta="scaled pilots" />
          </div>
        )}
      </section>

      {/* ---------------- MAHARASHTRA INNOVATION LANDSCAPE (REAL DATA) ---------------- */}
      <section>
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h2 className="text-[15px] font-bold text-primary">Maharashtra Innovation Landscape</h2>
          <DataTag kind="gov" />
          <span className="subtle">Public ecosystem data providing context for government innovation discovery.</span>
        </div>
        {!eco ? (
          eco === false ? (
            <Card>
              <p className="subtle">This dataset is currently unavailable from the configured public source.
                The last successful snapshot remains available on the <Link className="link" to="/govdata">Government Data</Link> page.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} h={130} />)}
            </div>
          )
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
              {eco.cards.map((card) => (
                <div key={card.key} className="card card-pad">
                  <div className="eyebrow">{card.label}</div>
                  <div className={`mt-1 text-[22px] font-bold leading-7 ${card.available ? 'text-primary' : 'text-ink-2'}`}>
                    {card.display}
                  </div>
                  {card.sub && <div className="mt-0.5 text-[11px] text-ink-2">{card.sub}</div>}
                  <DataProvenance p={card.provenance} compact />
                </div>
              ))}
            </div>
            <p className="subtle mt-2">{eco.notice} {eco.accelerators_note}</p>
          </>
        )}
      </section>

      {/* ---------------- STARTUP ECOSYSTEM + GEOGRAPHY (REAL DATA) ---------------- */}
      <section className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Startup Ecosystem by Sector" right={<DataTag kind="gov" />}>
          {!sectors ? (
            <SkeletonCard h={220} />
          ) : sectors === false ? (
            <p className="subtle">This dataset is currently unavailable from the configured public source.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={230}>
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
            </>
          )}
        </Card>

        <Card eyebrow="Maharashtra Innovation Footprint" right={<DataTag kind="gov" />}>
          {!geo ? (
            <SkeletonCard h={220} />
          ) : geo === false ? (
            <p className="subtle">This dataset is currently unavailable from the configured public source.</p>
          ) : (
            <>
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
            </>
          )}
        </Card>
      </section>

      {/* ---------------- GOVERNMENT PROBLEM LANDSCAPE (REAL DATA) ---------------- */}
      <section>
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h2 className="text-[15px] font-bold text-primary">Government Problem Landscape</h2>
          <DataTag kind="gov" />
        </div>
        {!problems ? (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} h={150} />)}
          </div>
        ) : problems === false ? (
          <Card><p className="subtle">This dataset is currently unavailable from the configured public source.</p></Card>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
              {problems.problems.map((p) => (
                <div key={p.key} className="card card-pad">
                  <div className="flex items-center justify-between">
                    <div className="text-[13px] font-bold text-primary">{p.problem_area}</div>
                    {p.available ? <span className="tag-gov !min-h-[18px] !text-[9px]">INDICATOR</span>
                      : <span className="tag-ghost !min-h-[18px] !text-[9px]">N/A</span>}
                  </div>
                  <div className="mt-1.5 text-[12px] font-semibold text-ink">{p.indicator !== '—' ? p.indicator : 'Public indicator not yet sourced'}</div>
                  <div className={`mt-1 text-[13px] font-bold ${p.available ? 'text-emerald' : 'text-ink-2'}`}>{p.display}</div>
                  {p.available && p.scope && <div className="mt-0.5 text-[11px] text-ink-2">{p.scope}</div>}
                  <div className="mt-2 border-t border-hairline pt-1.5 text-[11px] text-ink-2">
                    <span className="font-bold uppercase">Opportunity:</span> {p.innovation_opportunity}
                  </div>
                  {p.available && <div className="mt-1 text-[10px] text-ink-2">Source: {p.source}</div>}
                </div>
              ))}
            </div>
            <p className="subtle mt-2">{problems.notice}</p>
            <DataProvenance p={problems.provenance} />
          </>
        )}
      </section>

      {/* ---------------- CURRENT INNOVATION PIPELINE (PLATFORM DEMO) ---------------- */}
      <section className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Current Innovation Pipeline" title="Where each demo workflow stands"
          right={<DataTag kind="platformDemo" />}>
          {[
            { icon: '⚐', t: 'Smart Leakage Detection Challenge', s: 'Municipal Water Department · PUBLISHED', to: story?.shortcuts?.challenge && `/challenges/${story.shortcuts.challenge.id}`, tag: 'PLATFORM' },
            { icon: '◎', t: 'AquaSense Technologies', s: 'Matched & evaluated for CH-WTR-001', to: '/startups/ST-001', tag: 'DEMO STARTUP' },
            { icon: '◈', t: 'Smart Leakage Detection Pilot', s: '12 weeks · ₹10,00,000 · 3 sites · CONCLUDED', to: story?.shortcuts?.water_pilot && `/pilots/${story.shortcuts.water_pilot.id}`, tag: 'DEMO PILOT' },
            { icon: '▤', t: 'Evidence & Independent Validation', s: 'Telemetry, detection logs, uptime probes · VALIDATED', to: '/validation', tag: 'PLATFORM' },
            { icon: '⚖', t: 'Decision: RE-PILOT', s: 'Validated below target · expand 3 → 10 sites', to: '/decisions', tag: 'PLATFORM' },
          ].map((r) => (
            <div key={r.t} className="flex items-start gap-3 border-b border-hairline py-2.5 last:border-0">
              <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded bg-primary-soft text-primary">{r.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold text-ink">{r.t}</div>
                <div className="text-[12px] text-ink-2">{r.s}</div>
              </div>
              <span className="tag-ghost !min-h-[18px] !text-[9px]">{r.tag}</span>
              {r.to && <button className="btn-quiet btn-sm" onClick={() => nav(r.to)}>Open ↗</button>}
            </div>
          ))}
          <p className="subtle mt-2">Reason recorded for the decision: pilot evidence was below the required
            target and additional baseline/data coverage is required.</p>
        </Card>

        {/* ---------------- EVIDENCE INTELLIGENCE (SIMULATED PILOT) ---------------- */}
        <EvidenceIntelligence pilot={pilot} kpis={kpis} pkg={pkg} />
      </section>

      {/* ---------------- DECISION INTELLIGENCE (PLATFORM DEMO) ---------------- */}
      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" eyebrow="Decision Intelligence" title="Recommendation for the demo pilot"
          right={<DataTag kind="platformDemo" />}>
          {!rec ? (
            <p className="subtle">No recommendation generated yet. Government decision pending — AI recommendation
              cannot substitute for statutory authority.</p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded border border-[#F6E05E] bg-gold-soft px-4 py-2 text-[18px] font-bold text-[#7B341E]">
                  {label(rec.outcome)}
                </span>
                <div className="text-[12px] text-ink-2">
                  <div><strong>AI Recommendation</strong> · confidence {rec.confidence}</div>
                  <div>Explainable / evidence-based · engine {rec.engine_version} · {dt(rec.created_at)}</div>
                </div>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <div className="eyebrow mb-1">Reasons</div>
                  <ul className="list-disc space-y-1 pl-4 text-[12px]">{(rec.reasons || []).map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
                <div>
                  <div className="eyebrow mb-1">Evidence</div>
                  <ul className="list-disc space-y-1 pl-4 text-[12px]">{(rec.supporting_evidence || []).map((r) => <li key={r}>{r}</li>)}
                    <li className="text-ink-2">3 sites evaluated</li></ul>
                </div>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <div className="eyebrow mb-1">Missing evidence</div>
                  <ul className="list-disc space-y-1 pl-4 text-[12px] text-ink-2">{(rec.missing_evidence || []).map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
                <div>
                  <div className="eyebrow mb-1">Risk flags</div>
                  <ul className="list-disc space-y-1 pl-4 text-[12px] text-ink-2">{(rec.risk_flags || []).map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
              </div>
            </>
          )}
          <div className="mt-4 rounded border-2 border-primary bg-primary-soft px-4 py-2.5 text-center text-[12px] font-bold uppercase tracking-wide text-primary">
            AI Recommendation ≠ Government Decision
          </div>
          {gov ? (
            <div className="mt-3 rounded border border-hairline bg-canvas p-3">
              <div className="eyebrow mb-1">Government Decision · Senior Government Authority</div>
              <div className="flex flex-wrap items-center gap-2 text-[13px]">
                <span className="badge-amber">{label(gov.decision)}</span>
                <span className="text-ink-2">{gov.decided_by || gov.decided_by_name} · {dt(gov.at || gov.decided_at)} · audit ref {gov.id}</span>
              </div>
              <p className="mt-1 text-[12px] text-ink">{gov.reason}</p>
            </div>
          ) : (
            <p className="subtle mt-3">Government decision pending. AI recommendation cannot substitute for statutory authority.</p>
          )}
        </Card>

        <div className="space-y-4">
          <Card eyebrow="Four-Outcome Matrix" title="Possible outcomes">
            <DecisionMatrix outcome={rec?.outcome} />
            <div className="mt-3 border-t border-hairline pt-2 text-[11px] text-ink-2">
              <strong>Evidence Confidence</strong> = how strongly claimed outcomes are supported by evidence.
              <strong> Match Score</strong> = suitability for a challenge. They are separate measures and are never combined.
            </div>
          </Card>
          <Card eyebrow="Evidence Quality" title={eq.display || '—'}>
            <p className="text-[13px] text-ink-2">
              {eq.numerator ?? 0} of {eq.denominator ?? 0} evidence items have completed validation review.
            </p>
            <div className="progress-track mt-2">
              <div className="progress-fill bg-emerald"
                style={{ width: `${eq.numerator && eq.denominator ? 100 * eq.numerator / eq.denominator : 0}%` }} />
            </div>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px] text-ink-2">
              {(eq.limitations || []).map((l) => <li key={l}>{l}.</li>)}
            </ul>
          </Card>
        </div>
      </section>

      {/* ---------------- RECOMMENDATION DISTRIBUTION + BOTTLENECKS ---------------- */}
      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" eyebrow="Recommendation distribution" title="Latest AI recommendation per pilot"
          right={<span className="badge-blue">AI ASSISTED · NOT A DECISION</span>}>
          {chartData.length === 0 ? (
            <p className="subtle">No recommendations generated yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={210}>
              <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                  {chartData.map((e) => <Cell key={e.key} fill={COLORS[e.key] || NAVY} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          <p className="subtle mt-2">Sample: {chartData.reduce((x, y) => x + y.value, 0)} pilots with recommendations · platform records only.</p>
        </Card>

        <Card eyebrow="Current bottlenecks" title="Where work is waiting">
          {(a?.bottlenecks || []).length === 0 ? (
            <p className="subtle">No bottlenecks detected in the current pipeline.</p>
          ) : (
            <ul className="space-y-2">
              {a.bottlenecks.map((b, i) => (
                <li key={i} className="flex items-start gap-3 rounded border border-hairline px-3 py-2">
                  <span className="badge-amber mt-0.5">{b.stage}</span>
                  <div>
                    <div className="text-[13px] font-semibold text-ink">{b.item}</div>
                    <div className="text-[12px] text-ink-2">{b.issue}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3 border-t border-hairline pt-2">
            <div className="eyebrow mb-1.5">Recent activity</div>
            <ul className="space-y-1 text-[12px] text-ink-2">
              {(a?.recent_activity || []).map((x, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span className="text-ink">{label(x.action)}</span><span className="whitespace-nowrap">{dt(x.at)}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </section>

      {/* ---------------- PRODUCT RULES + DEMO SHORTCUTS ---------------- */}
      <section className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Product rules" title="These distinctions are enforced in code, not just displayed">
          <ProductRules />
          <p className="subtle mt-3">Insufficient Evidence is a valid outcome. AI abstains rather than inventing conclusions.
            AI assists; evidence supports; experts evaluate; independent validators validate; government decides.</p>
        </Card>
        <Card eyebrow="Demo mode" title="Open the full demo story" right={<DataTag kind="demo" />}>
          <ol className="space-y-1.5 text-[13px] text-ink">
            {(story?.story || []).map((s, i) => (
              <li key={i} className="flex gap-2"><span className="mono text-ink-2">{String(i + 1).padStart(2, '0')}</span>{s}</li>
            ))}
          </ol>
          <div className="mt-4 flex flex-wrap gap-2">
            {story?.shortcuts?.water_pilot && (
              <button className="btn-secondary btn-sm" onClick={() => nav(`/pilots/${story.shortcuts.water_pilot.id}`)}>Open Demo Pilot ↗</button>
            )}
            {story?.shortcuts?.challenge && (
              <button className="btn-secondary btn-sm" onClick={() => nav(`/challenges/${story.shortcuts.challenge.id}`)}>Open Demo Challenge ↗</button>
            )}
            <button className="btn-secondary btn-sm" onClick={() => nav('/govdata')}>Government Data ↗</button>
            <button className="btn-secondary btn-sm" onClick={() => nav('/procurement')}>Open Procurement ↗</button>
          </div>
        </Card>
      </section>

      {/* ---------------- DATA PROVENANCE FOOTER ---------------- */}
      <Card eyebrow="Data provenance" title="Where every number comes from">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <div className="mb-1 flex items-center gap-2"><DataTag kind="gov" /></div>
            <p className="text-[12px] text-ink-2">DPIIT startup counts, Maharashtra policy facts and the water-service
              indicator are imported from published Government of India / Government of Maharashtra sources with
              versioned snapshots and visible citations.</p>
          </div>
          <div>
            <div className="mb-1 flex items-center gap-2"><DataTag kind="platform" /></div>
            <p className="text-[12px] text-ink-2">Challenges, matches, evaluations, pilots, evidence, validations and
              decisions are generated by this platform's workflow — demo data for the SIH26136 presentation.</p>
          </div>
          <div>
            <div className="mb-1 flex items-center gap-2"><DataTag kind="pilot" /></div>
            <p className="text-[12px] text-ink-2">The AquaSense water pilot (21% → 19% → 18% → 20%) and the soil pilot
              are simulated scenarios. They are not actual Maharashtra government results.</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 border-t border-hairline pt-3">
          <Link className="btn-secondary btn-sm" to="/govdata">Data Source Centre ↗</Link>
          <Link className="btn-secondary btn-sm" to="/audit">Audit trail ↗</Link>
        </div>
      </Card>
    </div>
  );
}

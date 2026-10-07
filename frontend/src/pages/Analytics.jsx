import { useEffect, useState } from 'react';
import { BarChart, Bar, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../services/api';
import { Card, ErrorState, Loading, MetricCard } from '../components/ui';
import { DataTag, SkeletonCard } from '../components/provenance';
import { dt } from '../lib/format';

const COLORS = { SCALE: '#276749', RE_PILOT: '#D69E2E', REJECT: '#9B2C2C', INSUFFICIENT_EVIDENCE: '#718096' };

export default function Analytics({ notify }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { api.get('/api/analytics/overview').then(setData).catch(setError); }, []);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Loading />;

  const c = data.counters;
  const chart = Object.entries(data.recommendation_distribution).map(([k, v]) => ({ name: k, value: v }));

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="flex flex-wrap items-center gap-2">
          <div className="eyebrow">Government Intelligence</div>
          <DataTag kind="platform" />
        </div>
        <h1 className="text-primary text-headline-lg font-bold">Analytics &amp; Impact</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Every metric states its <strong>sample size, period and limitations</strong>. When a
          denominator is zero the value shows <strong>N/A</strong> — never a misleading 0%.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {!data ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} h={110} />) : (
          <>
            <MetricCard label="Active challenges" value={c.active_challenges.value} tone="blue" delta={c.active_challenges.period} />
            <MetricCard label="Registered startups" value={c.registered_startups.value} tone="teal" delta={c.registered_startups.period} />
            <MetricCard label="Active pilots" value={c.active_pilots.value} tone="orange" delta={c.active_pilots.period} />
            <MetricCard label="Completed pilots" value={c.completed_pilots.value} tone="navy" delta={c.completed_pilots.period} />
            <MetricCard label="Pending validations" value={c.pending_validations.value} tone="orange" delta={c.pending_validations.period} />
            <MetricCard label="Knowledge lessons" value={c.knowledge_lessons.value} tone="green" delta={c.knowledge_lessons.period} />
          </>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Decision outcomes" title="Latest AI recommendation per pilot">
          {chart.length === 0 ? <p className="subtle">No recommendations yet.</p> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chart} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                  {chart.map((e) => <Cell key={e.name} fill={COLORS[e.name] || '#0F2942'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          <p className="subtle mt-2">Sample: {chart.reduce((a, b) => a + b.value, 0)} pilots with a generated recommendation · period: all time · source: platform records only.</p>
        </Card>

        <Card eyebrow="Evidence quality" title={data.evidence_quality.display} right={<DataTag kind="platform" />}>
          <p className="text-[13px]">
            {data.evidence_quality.numerator} of {data.evidence_quality.denominator} evidence items have
            completed validation review ({data.evidence_quality.definition}).
          </p>
          <ul className="mt-3 list-disc space-y-1 pl-4 text-[12px] text-ink-2">
            {data.evidence_quality.limitations.map((l) => <li key={l}>{l}</li>)}
            <li>SHA-256 proves file integrity — not the truth of the underlying claim.</li>
          </ul>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Bottlenecks" title="Stages waiting on humans">
          {data.bottlenecks.length === 0 ? <p className="subtle">No bottlenecks detected.</p> : (
            <ul className="space-y-2">
              {data.bottlenecks.map((b, i) => (
                <li key={i} className="flex items-center justify-between rounded border border-hairline px-3 py-2 text-[13px]">
                  <span><span className="badge-amber mr-2">{b.stage}</span>{b.item}</span>
                  <span className="text-ink-2">{b.issue}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card eyebrow="Recent platform activity" title="From the audit trail">
          <ul className="space-y-1.5 text-[13px]">
            {data.recent_activity.map((a, i) => (
              <li key={i} className="flex justify-between border-b border-hairline pb-1.5 last:border-0">
                <span className="font-medium text-ink">{a.action}</span>
                <span className="text-ink-2">{a.actor} · {dt(a.at)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="notice">{data.disclaimer}</div>
    </div>
  );
}

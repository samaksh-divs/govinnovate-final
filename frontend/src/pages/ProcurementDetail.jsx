import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, getUser } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { d, inr, label } from '../lib/format';

export default function ProcurementDetail({ notify }) {
  const { pilotId } = useParams();
  const [pkg, setPkg] = useState(null);
  const [pilot, setPilot] = useState(null);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const nav = useNavigate();

  const load = useCallback(() => {
    api.get(`/api/pilots/${pilotId}`).then(setPilot).catch(setError);
    api.get(`/api/procurement/${pilotId}/package`).then(setPkg).catch(() => setNotFound(true));
  }, [pilotId]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (!pilot) return <Loading />;
  if (notFound) {
    return (
      <div className="mx-auto max-w-3xl space-y-5 pt-6">
        <button className="btn-quiet btn-sm" onClick={() => nav('/procurement')}>← Procurement</button>
        <EmptyState icon="🔒" title="No procurement package generated"
          action={<button className="btn-primary mt-3" onClick={() => nav(`/scaleup/${pilotId}`)}>Open scale-up plan</button>}>
          An approved scale-up plan is required before procurement preparation (hard workflow gate).
        </EmptyState>
      </div>
    );
  }
  if (!pkg) return <Loading />;

  async function generate() {
    try { setPkg(await api.post(`/api/procurement/${pilotId}/package`)); notify('Draft procurement package generated'); }
    catch (e) { notify(e.message); }
  }

  const c = pkg.content || {};

  return (
    <div className="mx-auto max-w-[1200px] space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/procurement')}>← Procurement</button>
          <div className="eyebrow">Procurement Package · {pkg.id} · generated {d(pkg.generated_at)}</div>
          <h1 className="text-primary text-headline-lg font-bold">{pilot.name} — Scale Procurement Prep</h1>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge value={pkg.status} />
          {['government_officer', 'administrator'].includes(getUser()?.role) && (
            <button className="btn-secondary btn-sm" onClick={generate}>↻ Regenerate package</button>
          )}
        </div>
      </header>

      <div className="border-2 border-dashed border-gold bg-gold-soft p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-[15px] font-bold text-[#7B341E]">⚠ DRAFT — NOT A LEGALLY BINDING TENDER</div>
          <div className="text-[13px] font-bold text-crimson">LEGAL REVIEW REQUIRED</div>
        </div>
        <p className="mt-1 text-[12px] text-[#7B341E]">
          This document is an evidence-backed <strong>preparation draft</strong> generated from pilot data.
          It does not constitute a tender, contract, or award. Formal procurement must follow the
          Maharashtra Public Procurement process with legal review.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Requirements summary" title="From the original challenge">
          {Object.keys(c.requirements_summary || {}).length === 0 ? <p className="subtle">Not linked to a challenge.</p> :
            Object.entries(c.requirements_summary).map(([bucket, list]) => (
              <div key={bucket} className="mb-2">
                <div className="eyebrow">{bucket}</div>
                <ul className="list-disc pl-4 text-[13px]">{(list || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
              </div>
            ))}
        </Card>

        <Card eyebrow="Validated KPIs" title="What was independently validated">
          <table className="tbl">
            <thead><tr><th>KPI</th><th>Target</th><th>Threshold</th><th>Validated</th></tr></thead>
            <tbody>
              {(c.validated_kpis || []).map((k) => (
                <tr key={k.name}><td className="font-semibold">{k.name}</td><td>{k.target}</td><td>{k.threshold}</td><td className="font-bold text-emerald">{k.validated}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card eyebrow="Pilot evidence summary" title="Context for evaluators">
          <dl className="grid grid-cols-2 gap-2 text-[13px]">
            <div><dt className="eyebrow">Pilot budget</dt><dd>{inr(c.pilot_evidence_summary?.budget)}</dd></div>
            <div><dt className="eyebrow">Duration</dt><dd>{c.pilot_evidence_summary?.duration_weeks} weeks</dd></div>
            <div><dt className="eyebrow">Sites</dt><dd>{c.pilot_evidence_summary?.sites}</dd></div>
            <div><dt className="eyebrow">Validation outcome</dt><dd><Badge value={c.pilot_evidence_summary?.validation} /></dd></div>
          </dl>
          {c.pilot_evidence_summary?.validation_report_sha256 && (
            <p className="mono mt-2 break-all text-[11px] text-ink-2">Report SHA-256: {c.pilot_evidence_summary.validation_report_sha256}</p>
          )}
        </Card>

        <Card eyebrow="Cybersecurity requirements" title="Carried into procurement">
          {Object.entries(c.cybersecurity_requirements || {}).map(([k, v]) => (
            <p key={k} className="border-b border-hairline py-1.5 text-[13px] last:border-0"><span className="eyebrow block">{label(k)}</span>{v}</p>
          ))}
        </Card>

        <Card eyebrow="Implementation scope" title="From the approved scale plan">
          {Object.entries(c.implementation_scope || {}).map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-hairline py-1.5 text-[13px] last:border-0">
              <span className="text-ink-2">{label(k)}</span><span className="font-semibold">{typeof v === 'number' && k.includes('budget') ? inr(v) : String(v)}</span>
            </div>
          ))}
        </Card>

        <Card eyebrow="Lessons learned" title="Accepted knowledge carried forward">
          {(c.lessons_learned || []).length === 0 ? <p className="subtle">No accepted lessons yet.</p> : (
            <ul className="space-y-2">
              {c.lessons_learned.map((l) => (
                <li key={l.title} className="rounded border border-hairline p-3 text-[13px]">
                  <strong>{l.title}</strong><p className="mt-0.5 text-ink-2">{l.lesson}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, getUser } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { inr, label } from '../lib/format';

export default function ScaleDetail({ notify }) {
  const { pilotId } = useParams();
  const [plan, setPlan] = useState(null);
  const [pilot, setPilot] = useState(null);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const nav = useNavigate();
  const user = getUser();

  const load = useCallback(() => {
    api.get(`/api/pilots/${pilotId}`).then(setPilot).catch(setError);
    api.get(`/api/scaleup/${pilotId}/plan`).then(setPlan).catch(() => setNotFound(true));
  }, [pilotId]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (!pilot) return <Loading />;
  if (notFound) {
    return (
      <div className="mx-auto max-w-3xl space-y-5 pt-6">
        <button className="btn-quiet btn-sm" onClick={() => nav('/scaleup')}>← Scale-up</button>
        <EmptyState icon="🔒" title="No scale-up plan exists"
          action={<button className="btn-primary mt-3" onClick={() => nav(`/decisions/${pilotId}`)}>Open decision workspace</button>}>
          {pilot.status === 'DECIDED'
            ? 'A government SCALE decision is required first — open the decision workspace and record SCALE.'
            : `Pilot status is ${label(pilot.status)}. Scale-up unlocks only after a government SCALE decision.`}
        </EmptyState>
      </div>
    );
  }
  if (!plan) return <Loading />;

  async function act(fn, message) {
    try { await fn(); load(); notify(message); } catch (e) { notify(e.message); }
  }

  const canApprove = ['senior_authority', 'administrator'].includes(user?.role);
  const scope = (obj) => Object.entries(obj).map(([k, v]) => (
    <div key={k} className="flex justify-between border-b border-hairline py-1.5 text-[13px] last:border-0">
      <span className="text-ink-2">{label(k)}</span>
      <span className="font-semibold text-ink">{typeof v === 'number' && k.includes('budget') ? inr(v) : String(v)}</span>
    </div>
  ));

  return (
    <div className="mx-auto max-w-[1200px] space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/scaleup')}>← Scale-up</button>
          <div className="eyebrow">Scale-Up Plan · {plan.id}</div>
          <h1 className="text-primary text-headline-lg font-bold">{pilot.name}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Badge value={plan.status} />
          {plan.status !== 'APPROVED' && canApprove && (
            <button className="btn-primary" onClick={() => act(() => api.post(`/api/scaleup/plans/${plan.id}/approve`), 'Scale plan approved — pilot marked SCALED')}>
              Approve scale-up
            </button>
          )}
          {plan.status === 'APPROVED' && (
            <button className="btn-gold" onClick={() => nav(`/procurement/${pilotId}`)}>Generate procurement package ↗</button>
          )}
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="Pilot scope (validated)" title="What was tested">
          {scope(plan.pilot_scope)}
        </Card>
        <Card eyebrow="Scale scope (proposed)" title="What scale means">
          {scope(plan.scale_scope)}
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card eyebrow="New KPIs for scale phase" title="Measurement continues">
          <ul className="list-disc space-y-1 pl-4 text-[13px]">{plan.new_kpis.map((k) => <li key={k}>{k}</li>)}</ul>
        </Card>
        <Card eyebrow="Operational risks" title="Reviewed before approval">
          <ul className="list-disc space-y-1 pl-4 text-[13px]">{plan.operational_risks.map((k) => <li key={k}>{k}</li>)}</ul>
        </Card>
        <Card eyebrow="Cybersecurity at scale" title="Re-assessment required">
          {Object.entries(plan.cybersecurity_plan).map(([k, v]) => (
            <p key={k} className="border-b border-hairline py-1.5 text-[13px] last:border-0">
              <span className="eyebrow block">{label(k)}</span>{v}
            </p>
          ))}
        </Card>
      </div>

      <Card eyebrow="Support requirements" title="Institutional capabilities needed">
        <div className="flex flex-wrap gap-2">{plan.support_requirements.map((s) => <span key={s} className="badge-blue">{s}</span>)}</div>
      </Card>

      <div className="notice">
        Approval is a <strong>senior-authority action</strong>. After approval, an evidence-backed
        procurement package can be prepared — clearly marked as a draft, not a legally binding tender.
      </div>
    </div>
  );
}

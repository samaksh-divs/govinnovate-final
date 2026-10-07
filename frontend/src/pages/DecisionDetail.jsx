import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, getUser } from '../services/api';
import { Badge, Card, ErrorState, Loading, ScoreBar } from '../components/ui';
import { dt, label } from '../lib/format';

const OUTCOMES = [
  { key: 'SCALE', icon: '↥', desc: 'Proceed to scale-up planning' },
  { key: 'RE_PILOT', icon: '↻', desc: 'Controlled re-pilot with corrected scope' },
  { key: 'INSUFFICIENT_EVIDENCE', icon: '?', desc: 'Abstain — evidence gap' },
  { key: 'REJECT', icon: '✕', desc: 'Close without scale' },
];

export default function DecisionDetail({ notify }) {
  const { pilotId } = useParams();
  const [pilot, setPilot] = useState(null);
  const [rec, setRec] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [decision, setDecision] = useState({ decision: '', reason: '', override: false });
  const nav = useNavigate();
  const user = getUser();

  const load = useCallback(() => {
    api.get(`/api/pilots/${pilotId}`).then(setPilot).catch(setError);
    api.get(`/api/decisions/${pilotId}/recommendations`).then((r) => setRec(r[0] || null)).catch(() => {});
    api.get(`/api/decisions/${pilotId}/government-decisions`).then(setHistory).catch(() => {});
  }, [pilotId]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (!pilot) return <Loading />;

  async function generate() {
    setBusy(true);
    try {
      const r = await api.post(`/api/decisions/${pilotId}/recommendation`);
      setRec(r);
      notify(r.outcome === 'INSUFFICIENT_EVIDENCE'
        ? 'Engine abstains: INSUFFICIENT EVIDENCE'
        : `Recommendation: ${label(r.outcome)} at ${Math.round(r.confidence * 100)}% confidence`);
    } catch (e) { notify(e.message); } finally { setBusy(false); }
  }

  async function record() {
    if (!decision.decision) { notify('Choose SCALE / RE-PILOT / REJECT / INSUFFICIENT EVIDENCE'); return; }
    try {
      await api.post(`/api/decisions/${pilotId}/government-decision`, decision);
      notify(`Government decision recorded: ${label(decision.decision)}`);
      setDecision({ decision: '', reason: '', override: false });
      load();
    } catch (e) { notify(e.message); }
  }

  const isAbstain = rec?.outcome === 'INSUFFICIENT_EVIDENCE';
  const canDecide = ['senior_authority', 'administrator'].includes(user?.role);

  return (
    <div className="mx-auto max-w-[1300px] space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button className="btn-quiet btn-sm mb-2" onClick={() => nav('/decisions')}>← All decisions</button>
          <div className="eyebrow">Decision Intelligence Workspace · {pilot.id}</div>
          <h1 className="text-primary text-headline-lg font-bold">{pilot.name}</h1>
          <p className="mt-1 text-[13px] text-ink-2">{pilot.startup_name} · {pilot.department} · status {label(pilot.status)}</p>
        </div>
        <button className="btn-primary" onClick={generate} disabled={busy}>{busy ? 'Evaluating…' : '✦ Generate / Refresh Recommendation'}</button>
      </header>

      {!rec ? (
        <Card><p className="subtle">No recommendation generated yet. Generate one to populate the workspace.</p></Card>
      ) : (
        <>
          {/* recommendation banner */}
          <div className={`rounded-lg border p-5 ${isAbstain ? 'border-[#F6E05E] bg-gold-soft' : rec.outcome === 'SCALE' ? 'border-[#A3D9B1] bg-emerald-soft' : rec.outcome === 'REJECT' ? 'border-[#FEB2B2] bg-crimson-soft' : 'border-[#BEE3F8] bg-azure-soft'}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-[20px] font-bold text-white">
                  {OUTCOMES.find((o) => o.key === rec.outcome)?.icon}
                </div>
                <div>
                  <div className="eyebrow">Engine recommendation · {rec.engine_version}</div>
                  <div className="text-[22px] font-bold text-primary">{label(rec.outcome)}</div>
                  <div className="text-[12px] text-ink-2">{rec.timestamp && dt(rec.timestamp)} · confidence {rec.outcome === 'INSUFFICIENT_EVIDENCE' ? '— (abstained)' : `${Math.round(rec.confidence * 100)}%`}</div>
                </div>
              </div>
              <span className="badge-navy">AI RECOMMENDATION ≠ GOVERNMENT DECISION</span>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <div className="eyebrow mb-1">Why (reasons)</div>
                <ul className="list-disc space-y-1 pl-4 text-[13px]">{rec.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              </div>
              {rec.supporting_evidence.length > 0 && (
                <div>
                  <div className="eyebrow mb-1 text-emerald">Supporting evidence</div>
                  <ul className="list-disc space-y-1 pl-4 text-[13px]">{rec.supporting_evidence.map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
              )}
              {rec.missing_evidence.length > 0 && (
                <div>
                  <div className="eyebrow mb-1 text-crimson">Missing evidence / gates</div>
                  <ul className="list-disc space-y-1 pl-4 text-[13px]">{rec.missing_evidence.map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
              )}
              {rec.risk_flags.length > 0 && (
                <div>
                  <div className="eyebrow mb-1 text-[#7B341E]">Risk flags (objective)</div>
                  <ul className="list-disc space-y-1 pl-4 text-[13px]">{rec.risk_flags.map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="xl:col-span-2" eyebrow="Explainable factors" title="Factor scores behind the recommendation">
              <div className="grid gap-3 md:grid-cols-3">
                {Object.entries(rec.factor_scores).map(([k, v]) => (
                  <ScoreBar key={k} label={label(k)} value={v} tone={v >= 70 ? 'bg-emerald' : v >= 45 ? 'bg-gold' : 'bg-crimson'} />
                ))}
              </div>
            </Card>

            <Card eyebrow="Outcome matrix" title="Legally defensible paths">
              <div className="grid grid-cols-2 gap-2">
                {OUTCOMES.map((o) => (
                  <div key={o.key} className={`rounded-lg border p-3 ${rec.outcome === o.key ? 'border-primary bg-primary-soft' : 'border-hairline bg-canvas'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-[16px]">{o.icon}</span>
                      {rec.outcome === o.key && <span className="badge-navy">ENGINE PICK</span>}
                    </div>
                    <div className="mt-1 text-[13px] font-bold text-primary">{label(o.key)}</div>
                    <div className="text-[11px] text-ink-2">{o.desc}</div>
                  </div>
                ))}
              </div>
              {rec.disclaimer && <p className="subtle mt-3">{rec.disclaimer}</p>}
            </Card>
          </div>
        </>
      )}

      {/* government decision */}
      <Card eyebrow="Final government action" title="Record the government decision"
        right={<span className="badge-blue">{canDecide ? 'Authorized authority signed in' : 'Requires Senior Authority role'}</span>}>
        {!canDecide ? (
          <div className="notice">Only a <strong>Senior Government Authority</strong> (or Administrator) may record the
            decision. Switch the demo role in the header to try this step — the server enforces it.</div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            <label className="field"><span>Decision<span className="req">*</span></span>
              <select value={decision.decision} onChange={(e) => setDecision({ ...decision, decision: e.target.value })}>
                <option value="">Select…</option>
                <option value="SCALE">SCALE</option>
                <option value="RE_PILOT">RE-PILOT</option>
                <option value="REJECT">REJECT</option>
                <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT EVIDENCE</option>
              </select></label>
            <label className="field">
              <span>Decision type</span>
              <label className="flex items-center gap-2 text-[13px]">
                <input type="checkbox" checked={decision.override} onChange={(e) => setDecision({ ...decision, override: e.target.checked })} />
                Override the AI recommendation (reason mandatory)
              </label>
            </label>
            <label className="field md:col-span-2"><span>Reason (permanent government record)<span className="req">*</span></span>
              <textarea value={decision.reason} onChange={(e) => setDecision({ ...decision, reason: e.target.value })}
                placeholder="Why this decision? Conditions? Evidence relied upon?" /></label>
            <div className="flex justify-end md:col-span-2">
              <button className="btn-primary" onClick={record} disabled={!decision.reason.trim()}>Record government decision ↗</button>
            </div>
          </div>
        )}
        {history.length > 0 && (
          <div className="mt-4 border-t border-hairline pt-3">
            <div className="eyebrow mb-2">Decision history (append-only, never overwritten)</div>
            <ul className="space-y-2">
              {history.map((h) => (
                <li key={h.id} className="rounded border border-hairline p-3 text-[13px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge value={h.decision === 'SCALE' ? 'SCALE' : h.decision === 'RE_PILOT' ? 'RE_PILOT' : h.decision === 'REJECT' ? 'REJECT' : 'INSUFFICIENT_EVIDENCE'} />
                    <span className="badge-gray">{h.decision_type}</span>
                    <span className="subtle">AI was: {label(h.ai_outcome) || '—'}</span>
                    <span className="ml-auto subtle">{h.decided_by} · {dt(h.at)}</span>
                  </div>
                  <p className="mt-1 text-ink-2">{h.reason}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </div>
  );
}

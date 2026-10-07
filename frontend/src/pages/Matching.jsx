import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, ScoreBar } from '../components/ui';
import { label } from '../lib/format';

const W = [['Problem fit', 'problemFit', 25], ['Technology fit', 'technologyFit', 20],
  ['Relevant experience', 'experience', 15], ['Verified pilot evidence', 'evidence', 15],
  ['Eligibility', 'eligibility', 10], ['Scalability', 'scalability', 10], ['Risk', 'risk', 5]];

export default function Matching({ notify }) {
  const { challengeId } = useParams();
  const [challenges, setChallenges] = useState([]);
  const [matches, setMatches] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [override, setOverride] = useState(null); // {match, rank, reason}
  const nav = useNavigate();

  useEffect(() => {
    api.get('/api/challenges').then(setChallenges).catch(() => {});
  }, []);
  useEffect(() => {
    if (!challengeId) return;
    api.get(`/api/matching/${challengeId}`).then(setMatches).catch(setError);
  }, [challengeId]);

  async function run() {
    setBusy(true); setError(null);
    try {
      setMatches(await api.post(`/api/matching/${challengeId}/run`));
      notify('Explainable matching complete — results audited');
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  async function submitOverride() {
    try {
      await api.post(`/api/matching/${challengeId}/override?match_id=${override.match.id}&new_rank=${override.rank}&reason=${encodeURIComponent(override.reason)}`);
      setMatches(await api.get(`/api/matching/${challengeId}`));
      setOverride(null);
      notify('Ranking overridden — reason recorded in audit trail');
    } catch (e) { notify(e.message); }
  }

  const active = challenges.find((x) => x.id === challengeId);

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Matching Engine · Explainable by design</div>
          <h1 className="text-primary text-headline-lg font-bold">Startup Matching</h1>
          <p className="mt-1 text-[14px] text-ink-2">Match Score measures suitability. Evidence Confidence separately measures how well claims were supported. They are never merged.</p>
        </div>
        {challengeId && <button className="btn-primary" onClick={run} disabled={busy}>{busy ? 'Running…' : '↻ Run / Refresh Matching'}</button>}
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <select value={challengeId || ''} onChange={(e) => nav(`/matching/${e.target.value}`)}
          className="rounded border border-line bg-white px-3 py-2 text-[13px] focus:border-primary focus:outline-none">
          <option value="">Select a published challenge…</option>
          {challenges.filter((c) => c.status === 'PUBLISHED').map((c) => (
            <option key={c.id} value={c.id}>{c.title}</option>
          ))}
        </select>
        {active && <Badge value="PUBLISHED">{active.department}</Badge>}
      </div>

      {!challengeId ? (
        <EmptyState icon="⇄" title="Select a challenge to match startups">
          The discovery engine uses approved challenge requirements and KPIs to calculate explainable, auditable matches.
        </EmptyState>
      ) : error ? <ErrorState error={error} onRetry={() => nav(0)} />
        : !matches ? <Loading label="Loading matches…" />
        : matches.length === 0 ? (
          <EmptyState icon="⇄" title="No matches yet" action={<button className="btn-primary mt-3" onClick={run}>Run matching</button>}>
            Run the matching engine to score the registry against this challenge.
          </EmptyState>
        ) : (
          <>
            <Card eyebrow="Mandated weights" title="How the Match Score is computed">
              <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-7">
                {W.map(([t, k, w]) => <ScoreBar key={k} label={t} value={w} tone="bg-azure" />)}
              </div>
              <p className="subtle mt-2">Weighted sum → 0-100 Match Score. Engine version is stamped on every run and stored with results.</p>
            </Card>

            <div className="space-y-3">
              {matches.map((m) => (
                <div key={m.id} className="card">
                  <div className="flex flex-wrap items-center gap-4 p-4">
                    <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-lg bg-primary-soft">
                      <span className="text-[18px] font-bold text-primary">{m.match_score}</span>
                      <span className="text-[9px] font-bold uppercase text-ink-2">match</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <button className="link text-[15px] font-bold" onClick={() => nav(`/startups/${m.startup.id}`)}>{m.startup.name}</button>
                        <Badge value={m.eligibility_status} />
                        <span className={`badge-${m.evidence_confidence === 'HIGH' ? 'green' : m.evidence_confidence === 'MEDIUM' ? 'amber' : 'red'}`}>
                          Evidence confidence: {m.evidence_confidence}
                        </span>
                        {m.overridden && <span className="badge-amber" title={m.override_reason}>OVERRIDDEN</span>}
                      </div>
                      <div className="subtle mt-0.5">{m.startup.sector} · {m.startup.hq_location} · {m.startup.stage}</div>
                      <div className="mt-2 grid gap-2 md:grid-cols-4 xl:grid-cols-7">
                        {W.map(([t, k]) => <ScoreBar key={k} label={t} value={m.component_scores[k]} tone="bg-primary" />)}
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1.5">
                      <span className="mono text-ink-2">rank #{m.rank}</span>
                      <button className="link text-[12px]" onClick={() => setExpanded(expanded === m.id ? null : m.id)}>
                        {expanded === m.id ? 'Hide explanation' : 'Why this score? ↗'}
                      </button>
                      <button className="btn-secondary btn-sm" onClick={() => setOverride({ match: m, rank: m.rank, reason: '' })}>
                        Override ranking
                      </button>
                    </div>
                  </div>
                  {expanded === m.id && (
                    <div className="border-t border-hairline bg-canvas p-4">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <div className="eyebrow mb-1 text-emerald">Why matched</div>
                          <ul className="list-disc space-y-1 pl-4 text-[13px]">
                            {m.explanations.why_matched.map((r) => <li key={r}>{r}</li>)}
                          </ul>
                        </div>
                        <div>
                          <div className="eyebrow mb-1 text-crimson">Evidence limitations</div>
                          <ul className="list-disc space-y-1 pl-4 text-[13px]">
                            {m.explanations.limitations.map((r) => <li key={r}>{r}</li>)}
                          </ul>
                        </div>
                      </div>
                      <p className="subtle mt-3">{m.explanations.note} · Engine: {m.run_version}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

      {override && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onMouseDown={(e) => e.target === e.currentTarget && setOverride(null)}>
          <div className="card w-full max-w-lg p-5 shadow-overlay">
            <h3 className="text-primary text-headline-sm font-bold">Override ranking — {override.match.startup.name}</h3>
            <p className="subtle mt-1">Government may override AI ranking. A reason is mandatory and an audit record is created.</p>
            <div className="mt-3 grid gap-3">
              <label className="field"><span>New rank (1-100)<span className="req">*</span></span>
                <input type="number" min="1" max="100" value={override.rank}
                  onChange={(e) => setOverride({ ...override, rank: Number(e.target.value) })} /></label>
              <label className="field"><span>Reason<span className="req">*</span></span>
                <textarea value={override.reason} onChange={(e) => setOverride({ ...override, reason: e.target.value })}
                  placeholder="e.g. Site visit confirmed stronger field capability than registry data reflects" /></label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button className="btn-quiet" onClick={() => setOverride(null)}>Cancel</button>
              <button className="btn-primary" onClick={submitOverride} disabled={!override.reason.trim()}>Record override</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

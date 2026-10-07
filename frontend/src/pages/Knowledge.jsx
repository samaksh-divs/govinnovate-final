import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { label } from '../lib/format';

export default function Knowledge({ notify }) {
  const [lessons, setLessons] = useState(null);
  const [similar, setSimilar] = useState(null);
  const [error, setError] = useState(null);
  const [extractBusy, setExtractBusy] = useState(false);

  const load = useCallback(() => {
    api.get('/api/knowledge/lessons').then(setLessons).catch(setError);
    api.get('/api/knowledge/similar?sector=Water%20Management&problem_type=leakage%20reduction&technology=Acoustic%20IoT')
      .then(setSimilar).catch(() => {});
  }, []);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (!lessons) return <Loading />;

  async function extract() {
    setExtractBusy(true);
    try {
      const r = await api.post('/api/knowledge/pilots/P-WTR-001/extract');
      notify(`${r.generated} candidate lessons generated — none applied automatically`);
      load();
    } catch (e) { notify(e.message); } finally { setExtractBusy(false); }
  }
  async function decide(lessonId, decision) {
    const edited = decision === 'EDIT' ? prompt('Edit the lesson text:') : null;
    if (decision === 'EDIT' && !edited) return;
    try {
      const q = `decision=${decision}${edited ? `&edited_lesson=${encodeURIComponent(edited)}` : ''}`;
      await api.post(`/api/knowledge/lessons/${lessonId}/decide?${q}`);
      notify(`Lesson ${decision.toLowerCase()}d — recorded with your name`);
      load();
    } catch (e) { notify(e.message); }
  }

  const pending = lessons.filter((l) => l.status === 'PENDING');

  return (
    <div className="mx-auto max-w-[1300px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Knowledge Engine · Institutional Learning</div>
          <h1 className="text-primary text-headline-lg font-bold">Knowledge Centre</h1>
          <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
            Evidence-backed lessons extracted from concluded pilots. Every recommendation requires
            explicit <strong>Accept / Edit / Ignore</strong> — nothing is applied automatically.
          </p>
        </div>
        <button className="btn-primary" onClick={extract} disabled={extractBusy}>
          {extractBusy ? 'Extracting…' : '✦ Extract lessons from demo pilot'}
        </button>
      </header>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2 space-y-3">
          {lessons.length === 0 ? (
            <EmptyState icon="✦" title="No lessons yet">Run the knowledge engine on a concluded pilot to extract candidates.</EmptyState>
          ) : (
            <>
              {pending.length > 0 && (
                <div className="warnbox">{pending.length} recommendation(s) awaiting an officer decision.</div>
              )}
              {lessons.map((l) => (
                <Card key={l.id}
                  eyebrow={<span className="flex items-center gap-2"><Badge value={l.status} />{l.source === 'KNOWLEDGE_ENGINE' ? 'Knowledge Engine' : 'Officer'} · {l.sector}</span>}
                  title={l.title}
                  right={
                    l.status === 'PENDING' ? (
                      <div className="flex gap-1.5">
                        <button className="btn-secondary btn-sm" onClick={() => decide(l.id, 'ACCEPT')}>Accept</button>
                        <button className="btn-secondary btn-sm" onClick={() => decide(l.id, 'EDIT')}>Edit</button>
                        <button className="btn-danger btn-sm" onClick={() => decide(l.id, 'IGNORE')}>Ignore</button>
                      </div>
                    ) : undefined
                  }>
                  <p className="text-[13px] leading-6">{l.edited_lesson || l.lesson}</p>
                  <dl className="mt-3 grid gap-2 text-[12px] md:grid-cols-2">
                    <div className="rounded bg-canvas p-2"><dt className="eyebrow">Evidence</dt><dd>{l.evidence}</dd></div>
                    <div className="rounded bg-canvas p-2"><dt className="eyebrow">Recommendation</dt><dd>{l.recommendation}</dd></div>
                  </dl>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(l.tags || []).map((t) => <span key={t} className="badge-gray">#{t}</span>)}
                  </div>
                </Card>
              ))}
            </>
          )}
        </div>

        <Card eyebrow="Similar pilot recommender" title="Why these are similar">
          {!similar ? <Loading /> : similar.results.length === 0 ? (
            <p className="subtle">No sufficiently similar historical pilots.</p>
          ) : (
            <div className="space-y-3">
              {similar.results.map((r) => (
                <div key={r.pilot.id} className="rounded border border-hairline p-3">
                  <div className="flex items-center justify-between">
                    <strong className="text-[13px]">{r.pilot.name}</strong>
                    <span className="mono text-[12px] font-bold text-primary">{r.similarity}%</span>
                  </div>
                  <div className="subtle mt-0.5">{r.pilot.department} · {r.pilot.year} · outcome {label(r.pilot.outcome)}</div>
                  <p className="mt-1 text-[12px] text-ink">{r.pilot.summary}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {r.why_similar.map((w) => <span key={w} className="badge-blue">{w}</span>)}
                  </div>
                </div>
              ))}
              <p className="subtle">{similar.note}</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

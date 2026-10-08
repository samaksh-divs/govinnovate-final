import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, MetricCard } from '../../components/ui';
import { DataTag } from '../../components/provenance';
import { label } from '../../lib/format';

/**
 * Startup persona — solution provider / pilot participant. All data comes from
 * GET /api/startups/me/overview, which assembles the SAME shared records the
 * officer/expert/validator personas operate on (matching = your application,
 * evaluation aggregate, your pilots, your evidence). Nothing is copied.
 */
export default function StartupDashboard({ notify }) {
  const [overview, setOverview] = useState(null);
  const [challenges, setChallenges] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/api/startups/me/overview').then(setOverview).catch(setError);
    api.get('/api/challenges').then(setChallenges).catch(() => {});
  }, []);

  if (error) return <ErrorState error={error} onRetry={() => location.reload()} />;
  if (!overview) return <Loading label="Loading your workspace…" />;

  const open = (challenges || []).filter((c) => c.status === 'PUBLISHED');
  const apps = overview.applications || [];
  const pilots = overview.pilots || [];
  const activePilots = pilots.filter((p) => ['READY_TO_START', 'ACTIVE'].includes(p.status));
  const ev = overview.evidence || {};

  const stageFor = (a) => {
    const stageLabels = {
      SUBMITTED: 'SUBMITTED — awaiting expert evaluation',
      UNDER_REVIEW: 'UNDER REVIEW — expert evaluation in progress',
      APPROVED: 'APPROVED — shortlisted for pilot by the department',
      REJECTED: 'REJECTED — not shortlisted',
      MORE_EVIDENCE_REQUESTED: 'MORE EVIDENCE REQUESTED by the department',
      RE_EVALUATION_REQUESTED: 'RE-EVALUATION REQUESTED by the department',
      PILOT_CREATED: 'PILOT CREATED — proceed to execution',
    };
    if (stageLabels[a.stage]) return stageLabels[a.stage];
    if (a.evaluation?.recommendation) return `Evaluation: ${label(a.evaluation.recommendation)}`;
    if (a.rank) return `Matched · rank #${a.rank}`;
    return 'Match pending';
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">{overview.startup?.name} · {overview.startup?.sector || 'Startup'}</div>
        <h1 className="text-primary text-headline-lg font-bold">Startup Dashboard</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Track your applications, pilots and evidence through the government workflow. You see
          only your own records — officers, experts and validators work the same records from
          their side.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Open challenges" value={open.length} tone="blue" delta="published & matching" />
        <MetricCard label="My applications" value={apps.length} tone="navy"
          delta={apps.length ? 'in evaluation pipeline' : 'none yet'} />
        <MetricCard label="Active pilots" value={activePilots.length} tone="green"
          delta={activePilots.length ? 'in execution' : 'none active'} />
        <MetricCard label="Evidence validated" value={`${ev.validated ?? 0}/${ev.total ?? 0}`} tone="teal"
          delta={ev.awaiting_review ? `${ev.awaiting_review} awaiting review` : 'review pipeline clear'}
          attention={!!ev.awaiting_review} />
      </div>

      <Card eyebrow="My applications" title="Where each application stands"
        right={<DataTag kind="challenge" />}>
        {apps.length === 0 ? (
          <EmptyState icon="⚐" title="No applications yet"
            action={open.length ? <Link className="btn-primary btn-sm" to="/challenges">Browse open challenges</Link> : undefined}>
            When the department runs matching on a published challenge, your startup's application
            status (match rank, expert evaluation, shortlist decision) appears here automatically.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">              <table className="tbl">
                <thead><tr><th>Challenge</th><th>Department</th><th>Rank</th><th>Match score</th><th>Current stage</th><th></th></tr></thead>
                <tbody>
                  {apps.map((a, i) => (
                    <tr key={i}>
                      <td className="font-semibold">
                        {a.challenge ? <Link className="link" to={`/challenges/${a.challenge.id}`}>{a.challenge.title}</Link> : '—'}
                      </td>
                      <td>{a.challenge?.department || '—'}</td>
                      <td className="mono">{a.rank ? `#${a.rank}` : '—'}</td>
                      <td className="mono">{a.match_score ?? '—'}</td>
                      <td>{stageFor(a)}</td>
                      <td className="text-right">
                        {a.stage === 'PILOT_CREATED' && a.pilot_id && (
                          <Link className="btn-primary btn-sm" to={`/pilots/${a.pilot_id}`}>View Pilot ↗</Link>
                        )}
                        {a.stage === 'APPROVED' && <span className="badge-green">NEXT STEP: PILOT</span>}
                        {a.stage === 'REJECTED' && <span className="badge-red">CLOSED</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
          </div>
        )}
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card eyebrow="My pilots" title="Pilot execution status" right={<DataTag kind="pilot" />}>
          {pilots.length === 0 ? (
            <EmptyState icon="◈" title="No pilots yet">
              A pilot is created for your startup after officers shortlist it following expert
              evaluation. You'll accept it here, then submit evidence against its KPIs.
            </EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead><tr><th>Pilot</th><th>Department</th><th>Status</th><th>Health</th><th></th></tr></thead>
                <tbody>
                  {pilots.map((p) => (
                    <tr key={p.id}>
                      <td className="font-semibold">{p.name}</td>
                      <td>{p.department}</td>
                      <td><Badge value={p.status} /></td>
                      <td><Badge value={p.health} /></td>
                      <td className="text-right"><Link className="btn-secondary btn-sm" to={`/pilots/${p.id}`}>Open ↗</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card eyebrow="Open challenges" title="Published by departments" right={<DataTag kind="challenge" />}>
          {open.length === 0 ? (
            <p className="subtle">No published challenges right now. Check back — publishing is officer-controlled.</p>
          ) : (
            <ul className="space-y-2">
              {open.slice(0, 6).map((c) => (
                <li key={c.id} className="rounded border border-hairline bg-canvas p-3">
                  <div className="flex items-center justify-between gap-2">
                    <Link className="link text-[13px] font-semibold" to={`/challenges/${c.id}`}>{c.title}</Link>
                    <span className="mono text-[11px] text-ink-2">{c.department}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[12px] text-ink-2">{c.problem_statement}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card eyebrow="Next actions" title="Your part of the workflow">
        <ol className="list-decimal space-y-1 pl-5 text-[13px] text-ink-2">
          <li>Track application stages above — expert evaluation and shortlist decisions appear automatically.</li>
          <li>When a pilot is created for you, <Link className="link" to="/pilots">accept it in My Pilots</Link> to move it to READY_TO_START.</li>
          <li>Submit measurement evidence against pilot KPIs from <Link className="link" to="/evidence">Evidence Submission</Link>.</li>
          <li>Final decisions (SCALE / RE-PILOT / REJECT) are made by government authorities — you see the outcome here and on the pilot.</li>
        </ol>
      </Card>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, MetricCard } from '../../components/ui';
import { DataTag } from '../../components/provenance';
import { label } from '../../lib/format';

/**
 * Expert Evaluator persona — technical review layer (EVALUATION_SUBMIT, COI_DECLARE).
 * The backend already scopes GET /api/evaluations/assignments to the signed-in
 * expert; this view never receives officer decision controls.
 */
export default function ExpertDashboard() {
  const [assignments, setAssignments] = useState(null);
  const [startups, setStartups] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/api/evaluations/assignments').then(setAssignments).catch(setError);
    api.get('/api/startups').then(setStartups).catch(() => {});
  }, []);

  if (error) return <ErrorState error={error} onRetry={() => location.reload()} />;
  if (!assignments) return <Loading label="Loading your review queue…" />;

  const nameOf = (id) => startups.find((s) => s.id === id)?.name || id;
  const stats = {
    assigned: assignments.length,
    coiOpen: assignments.filter((a) => a.status === 'AWAITING_COI').length,
    pendingScore: assignments.filter((a) => a.status !== 'AWAITING_COI' && a.status !== 'RECUSED'
      && !a.latest_evaluation).length,
    submitted: assignments.filter((a) => a.latest_evaluation).length,
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Human Review Layer · Expert Evaluation</div>
        <h1 className="text-primary text-headline-lg font-bold">Evaluator Dashboard</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Your assigned evaluations only. Score the published criteria, declare conflicts of
          interest first, and justify scores below 40. Evaluation informs decisions — it never
          makes them.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Assigned evaluations" value={stats.assigned} tone="blue" delta="from challenge officers" />
        <MetricCard label="Awaiting my score" value={stats.pendingScore} tone="orange"
          delta={stats.pendingScore ? 'criteria scoring open' : 'queue clear'} attention={!!stats.pendingScore} />
        <MetricCard label="COI declaration open" value={stats.coiOpen} tone="red"
          delta={stats.coiOpen ? 'declare before scoring' : 'all declared'} attention={!!stats.coiOpen} />
        <MetricCard label="Submitted evaluations" value={stats.submitted} tone="green" delta="versioned, auditable" />
      </div>

      <Card eyebrow="My assignments" title="Independent review queue" right={<DataTag kind="challenge" />}>
        {assignments.length === 0 ? (
          <EmptyState icon="✔" title="No evaluations assigned yet">
            When a challenge officer assigns you a startup for expert review, it appears here with
            its evidence and scoring criteria.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Challenge</th><th>Startup</th><th>Status</th><th>Latest score</th><th>Recommendation</th><th></th></tr></thead>
              <tbody>
                {assignments.map((a) => (
                  <tr key={a.id}>
                    <td className="mono">{a.challenge_id}</td>
                    <td className="font-semibold">{nameOf(a.startup_id)}</td>
                    <td><Badge value={a.status} /></td>
                    <td className="mono">{a.latest_evaluation ? a.latest_evaluation.weighted_total : '—'}</td>
                    <td>{a.latest_evaluation ? label(a.latest_evaluation.recommendation) : '—'}</td>
                    <td className="text-right"><Link className="btn-primary btn-sm" to="/evaluations">Open evaluation ↗</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card eyebrow="Review context" title="Where evaluation sits in the workflow">
        <p className="text-[13px] leading-6 text-ink-2">
          Startup applies → <strong className="text-ink">you evaluate against published criteria</strong> →
          officer takes the shortlist decision → pilot runs → validator validates → government decides.
          Your scores are aggregated with other experts; disagreement is flagged, never hidden.
        </p>
      </Card>
    </div>
  );
}

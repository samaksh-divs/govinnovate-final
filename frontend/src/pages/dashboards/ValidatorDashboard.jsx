import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, MetricCard } from '../../components/ui';
import { DataTag } from '../../components/provenance';

/**
 * Independent Validator persona — evidence reviewer (VALIDATION_SUBMIT, COI_DECLARE).
 * GET /api/validation/assignments is scoped server-side to the signed-in
 * validator, so this queue can only ever show this validator's own work.
 * Final procurement authority deliberately does NOT exist for this role.
 */
export default function ValidatorDashboard() {
  const [assignments, setAssignments] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/api/validation/assignments').then(setAssignments).catch(setError);
  }, []);

  if (error) return <ErrorState error={error} onRetry={() => location.reload()} />;
  if (!assignments) return <Loading label="Loading your validation queue…" />;

  const stats = {
    assigned: assignments.length,
    coiOpen: assignments.filter((a) => a.coi_status === 'AWAITING_COI').length,
    inProgress: assignments.filter((a) => a.status === 'IN_PROGRESS'
      || (a.package?.status === 'IN_VALIDATION' && a.status !== 'SUBMITTED')).length,
    submitted: assignments.filter((a) => a.status === 'SUBMITTED').length,
  };

  const nextAction = (a) => {
    if (a.coi_status === 'AWAITING_COI') return 'Declare COI first';
    if (a.status === 'SUBMITTED') return 'Report submitted';
    if (a.package?.status === 'IN_VALIDATION') return 'Add findings / report';
    if (a.package?.status === 'VALIDATOR_ASSIGNED') return 'Start validation';
    return 'Awaiting package state';
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <div className="eyebrow">Independent Validation · Claim → Observed → Validated</div>
        <h1 className="text-primary text-headline-lg font-bold">Validator Dashboard</h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Your assigned validation packages only. Compare claimed vs observed values, record
          objective findings — including honest <em>INSUFFICIENT EVIDENCE</em> and{' '}
          <em>UNKNOWN</em> states — and submit the validation report. You never hold final
          government or procurement authority.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Assigned packages" value={stats.assigned} tone="blue" delta="from challenge officers" />
        <MetricCard label="COI declaration open" value={stats.coiOpen} tone="red"
          delta={stats.coiOpen ? 'required before starting' : 'all declared'} attention={!!stats.coiOpen} />
        <MetricCard label="Validation in progress" value={stats.inProgress} tone="orange"
          delta={stats.inProgress ? 'findings open' : 'none running'} attention={!!stats.inProgress} />
        <MetricCard label="Reports submitted" value={stats.submitted} tone="green" delta="versioned, auditable" />
      </div>

      <Card eyebrow="My assignments" title="Validation queue" right={<DataTag kind="pilot" />}>
        {assignments.length === 0 ? (
          <EmptyState icon="✓" title="No validation packages assigned yet">
            Officers prepare validation packages from reviewed evidence and assign them to you.
            Your queue fills from the same shared evidence the startup submits and the officer
            reviews.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Pilot</th><th>Startup</th><th>Department</th><th>Package</th><th>COI</th><th>Next action</th><th></th></tr></thead>
              <tbody>
                {assignments.map((a) => (
                  <tr key={a.id}>
                    <td className="font-semibold">{a.pilot?.name || a.package?.pilot_id || '—'}</td>
                    <td>{a.pilot?.startup_name || '—'}</td>
                    <td>{a.pilot?.department || '—'}</td>
                    <td><Badge value={a.package?.status || 'UNKNOWN'} /><div className="mono mt-0.5 text-ink-2">{a.package?.evidence_count ?? 0} evidence</div></td>
                    <td><Badge value={a.coi_status} /></td>
                    <td>{nextAction(a)}</td>
                    <td className="text-right">
                      <Link className="btn-primary btn-sm" to="/validation">Open validation ↗</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card eyebrow="Method note" title="What independence means here">
        <p className="text-[13px] leading-6 text-ink-2">
          You validate outcomes independently of the startup's claim and the officer's review:
          SHA-256 confirms file integrity, your findings compare claimed vs observed vs target
          values, and your report feeds the government decision — it does not make it.
        </p>
      </Card>
    </div>
  );
}

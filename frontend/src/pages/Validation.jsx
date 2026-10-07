import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, Modal } from '../components/ui';
import { label } from '../lib/format';

const FINDINGS = ['SUPPORTED', 'PARTIALLY_SUPPORTED', 'NOT_SUPPORTED', 'INSUFFICIENT_EVIDENCE',
  'CONTRADICTORY_EVIDENCE', 'UNVERIFIABLE', 'UNKNOWN'];
const VALIDATORS = [
  { id: 'U-VAL1', name: 'V. Deshpande — Independent Water Audit Collective (demo)' },
  { id: 'U-VAL2', name: 'S. Iyer — Cert-In Empanelled Auditor (demo)' },
];

export default function Validation({ notify }) {
  const [packages, setPackages] = useState(null);
  const [pilots, setPilots] = useState([]);
  const [pilotFilter, setPilotFilter] = useState('');
  const [active, setActive] = useState(null); // full package for findings/report modal
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api.get(`/api/validation/packages${pilotFilter ? `?pilot_id=${pilotFilter}` : ''}`)
      .then(setPackages).catch(setError);
  }, [pilotFilter]);
  useEffect(load, [load]);
  useEffect(() => { api.get('/api/pilots').then(setPilots).catch(() => {}); }, []);

  async function prepare() {
    const pilotId = prompt('Pilot ID to prepare for validation (e.g. P-WTR-001):');
    if (!pilotId) return;
    try { await api.post(`/api/validation/packages?pilot_id=${pilotId}`); notify('Validation package prepared from reviewed evidence'); load(); }
    catch (e) { notify(e.message); }
  }

  async function act(pkgId, fn, message) {
    try { await fn(); notify(message); load(); } catch (e) { notify(e.message); }
  }

  if (error) return <ErrorState error={error} />;

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Independent Validation · Claim → Observed → Validated</div>
          <h1 className="text-primary text-headline-lg font-bold">Validation</h1>
          <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
            Validators compare <strong>claimed</strong> vs <strong>observed</strong> vs <strong>validated</strong> values
            against targets. Findings are objective: the system never labels anyone fraudulent.
          </p>
        </div>
        <button className="btn-primary" onClick={prepare}>＋ Prepare Validation Package</button>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <select value={pilotFilter} onChange={(e) => setPilotFilter(e.target.value)}
          className="rounded border border-line bg-white px-3 py-2 text-[13px]">
          <option value="">All pilots</option>
          {pilots.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {!packages ? <Loading /> : packages.length === 0 ? (
        <EmptyState icon="✓" title="No validation packages yet"
          action={<button className="btn-primary mt-3" onClick={prepare}>Prepare from reviewed evidence</button>}>
          Review evidence items in the Evidence repository, mark them “Ready for validation”, then prepare a package.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {packages.map((pkg) => (
            <Card key={pkg.id}
              eyebrow={`Package ${pkg.id} · ${pkg.pilot_name}`}
              title={<div className="flex items-center gap-2"><Badge value={pkg.status} /></div>}
              right={
                <div className="flex flex-wrap gap-2">
                  {pkg.status === 'PREPARED' && (
                    <select className="rounded border border-line px-2 py-1 text-[12px]" defaultValue=""
                      onChange={(e) => e.target.value && act(pkg.id, () => api.post(`/api/validation/packages/${pkg.id}/assign?validator_id=${e.target.value}`), 'Validator assigned — COI required')}>
                      <option value="" disabled>Assign validator…</option>
                      {VALIDATORS.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                    </select>
                  )}
                  {pkg.status === 'VALIDATOR_ASSIGNED' && (
                    <button className="btn-secondary btn-sm" onClick={() => act(pkg.id, () => api.post(`/api/validation/packages/${pkg.id}/start`), 'Validation started')}>
                      Start validation (COI-gated)
                    </button>
                  )}
                  {pkg.status === 'IN_VALIDATION' && (
                    <button className="btn-gold btn-sm" onClick={() => setActive(pkg)}>Add findings / report ↗</button>
                  )}
                </div>
              }>
              <div className="grid gap-4 xl:grid-cols-2">
                <div>
                  <div className="eyebrow mb-1">Evidence in package ({pkg.evidence.length})</div>
                  <ul className="space-y-1 text-[13px]">
                    {pkg.evidence.map((e) => (
                      <li key={e.id} className="flex items-center justify-between rounded border border-hairline px-2 py-1.5">
                        <span className="truncate">{e.title}</span>
                        <span className="mono ml-2 shrink-0 text-ink-2" title={e.sha256}>{e.sha256.slice(0, 10)}…</span>
                        <Badge value={e.status} />
                      </li>
                    ))}
                  </ul>
                  <div className="eyebrow mb-1 mt-3">Validators</div>
                  {pkg.validators.length === 0 ? <p className="subtle">None assigned.</p> : (
                    <ul className="space-y-1 text-[13px]">
                      {pkg.validators.map((v) => (
                        <li key={v.id} className="flex items-center gap-2">
                          <strong>{v.name}</strong>
                          <Badge value={v.coi_status} />
                          <Badge value={v.status} />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <div className="eyebrow mb-1">Findings (Claim → Observed → Validated → Target)</div>
                  {pkg.findings.length === 0 ? <p className="subtle">No findings recorded yet.</p> : (
                    <div className="overflow-x-auto">
                      <table className="tbl">
                        <thead><tr><th>KPI</th><th>Claimed</th><th>Observed</th><th>Validated</th><th>Finding</th></tr></thead>
                        <tbody>
                          {pkg.findings.map((f) => (
                            <tr key={f.id}>
                              <td className="text-[12px]">{f.kpi_id || '—'}</td>
                              <td className="mono">{f.claimed}</td>
                              <td className="mono">{f.observed}</td>
                              <td className="mono font-bold text-primary">{f.validated_value}</td>
                              <td><Badge value={f.finding} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {pkg.report && (
                    <div className="successbox mt-3">
                      <strong>Validation report v{pkg.report.report_version} · {label(pkg.report.overall_finding)}</strong>
                      <p className="mt-1 text-[12px]">{pkg.report.summary}</p>
                      <p className="mono mt-1 text-[11px]">Report SHA-256: {pkg.report.sha256.slice(0, 24)}…</p>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {active && <WorkModal pkg={active} onClose={() => { setActive(null); load(); }} notify={notify} />}
    </div>
  );
}

function WorkModal({ pkg, onClose, notify }) {
  const [finding, setFinding] = useState({ kpi_id: '', claimed: '', observed: '', validated_value: '', target: '', finding: 'PARTIALLY_SUPPORTED', explanation: '' });
  const [report, setReport] = useState({ summary: '', overall_finding: 'PARTIALLY_SUPPORTED', validated_kpis: '{}' });
  const [coi, setCoi] = useState('NO_CONFLICT');
  const [error, setError] = useState('');

  async function addFinding() {
    try {
      await api.post(`/api/validation/packages/${pkg.id}/findings`, { ...finding, kpi_id: finding.kpi_id || null });
      notify('Finding recorded'); setError('');
    } catch (e) { setError(e.message); }
  }
  async function submitReport() {
    let kpis = {};
    try { kpis = JSON.parse(report.validated_kpis || '{}'); }
    catch { setError('Validated KPIs must be JSON, e.g. {"Leakage Reduction": "18%"}'); return; }
    try {
      await api.post(`/api/validation/packages/${pkg.id}/report`, { ...report, validated_kpis: kpis });
      notify('Validation report submitted — pilot KPIs updated'); onClose();
    } catch (e) { setError(e.message); }
  }

  return (
    <Modal wide eyebrow={`Validator workspace · ${pkg.id}`} title="Record findings & submit report" onClose={onClose}>
      {error && <div className="errorbox mb-3">{error}</div>}

      <div className="warnbox mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <strong>Validator COI</strong>
          <p className="text-[12px]">A confirmed conflict recuses you from this package (hard server-side gate).</p>
        </div>
        <button className="btn-secondary btn-sm"
          onClick={async () => {
            const a = pkg.validators[0];
            if (!a) return notify('No validator assigned to you');
            try { await api.post(`/api/validation/assignments/${a.id}/coi`, { status: coi }); notify('COI declared'); }
            catch (e) { notify(e.message); }
          }}>
          Declare COI ({label(coi)})
        </button>
        <select className="rounded border border-line px-2 py-1 text-[12px]" value={coi} onChange={(e) => setCoi(e.target.value)}>
          {['NO_CONFLICT', 'POTENTIAL_CONFLICT', 'CONFIRMED_CONFLICT'].map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-hairline p-4">
          <div className="eyebrow mb-3">Add KPI finding</div>
          <div className="grid gap-2">
            <label className="field"><span>Claimed (startup)</span><input value={finding.claimed} onChange={(e) => setFinding({ ...finding, claimed: e.target.value })} placeholder="21%" /></label>
            <label className="field"><span>Observed (instrumented)</span><input value={finding.observed} onChange={(e) => setFinding({ ...finding, observed: e.target.value })} placeholder="19%" /></label>
            <label className="field"><span>Validated (independent)</span><input value={finding.validated_value} onChange={(e) => setFinding({ ...finding, validated_value: e.target.value })} placeholder="18%" /></label>
            <label className="field"><span>Target / threshold</span><input value={finding.target} onChange={(e) => setFinding({ ...finding, target: e.target.value })} placeholder="≥18% / 20%" /></label>
            <label className="field"><span>Finding</span>
              <select value={finding.finding} onChange={(e) => setFinding({ ...finding, finding: e.target.value })}>
                {FINDINGS.map((f) => <option key={f} value={f}>{label(f)}</option>)}
              </select></label>
            <label className="field"><span>Explanation (objective language)</span>
              <textarea value={finding.explanation} onChange={(e) => setFinding({ ...finding, explanation: e.target.value })}
                placeholder="Describe what the evidence supports; do not characterise intent." /></label>
            <button className="btn-primary" onClick={addFinding}>＋ Record finding</button>
          </div>
        </div>

        <div className="rounded-lg border border-hairline p-4">
          <div className="eyebrow mb-3">Submit validation report</div>
          <div className="grid gap-2">
            <label className="field"><span>Overall finding</span>
              <select value={report.overall_finding} onChange={(e) => setReport({ ...report, overall_finding: e.target.value })}>
                {FINDINGS.map((f) => <option key={f} value={f}>{label(f)}</option>)}
              </select></label>
            <label className="field"><span>Summary</span>
              <textarea value={report.summary} onChange={(e) => setReport({ ...report, summary: e.target.value })}
                placeholder="What does the independent analysis support, at what values?" /></label>
            <label className="field"><span>Validated KPIs (JSON: name → validated value)</span>
              <textarea value={report.validated_kpis} onChange={(e) => setReport({ ...report, validated_kpis: e.target.value })}
                placeholder='{"Leakage Reduction": "18%"}' /></label>
            <button className="btn-gold" onClick={submitReport}>Submit report ↗</button>
            <p className="subtle">Requires at least one finding. Report content is hashed (SHA-256) and versioned; pilot KPI observed values update from validated numbers.</p>
          </div>
        </div>
      </div>
    </Modal>
  );
}

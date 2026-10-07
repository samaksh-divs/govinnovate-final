import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, ErrorState, Loading, Modal, Field } from '../components/ui';
import { label } from '../lib/format';

export default function Kpis({ notify }) {
  const { id } = useParams();
  const nav = useNavigate();
  const [kpis, setKpis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null); // kpi id
  const [draft, setDraft] = useState({ name: '', baseline: '', target: '', unit: '%',
    measurement_method: '', evidence_source: '', success_threshold: '', direction: 'reduce' });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.get(`/api/pilots/${id}`).then((p) => setKpis(p.kpis || [])).catch(setError)
      .finally(() => setLoading(false));
  }, [id]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (loading) return <Loading label="Loading KPIs…" />;

  const canEdit = ['government_officer', 'administrator', 'startup'].includes(
    (localStorage.getItem('gv_user') && JSON.parse(localStorage.getItem('gv_user')).role) || 'government_officer');

  async function save(kpi) {
    if (!kpi.name.trim()) { notify('KPI name is required'); return; }
    try { await api.patch(`/api/pilots/${id}/kpis/${kpi.id}`, kpi); load(); notify('KPI saved'); }
    catch (e) { notify(e.message); }
  }

  async function remove(kpiId) {
    if (!window.confirm('Delete this KPI?')) return;
    try { await api.del(`/api/pilots/${id}/kpis/${kpiId}`); load(); notify('KPI deleted'); }
    catch (e) { notify(e.message); }
  }

  async function handleSave() {
    if (!draft.name) { notify('KPI name is required'); return; }
    try {
      await api.patch(`/api/pilots/${id}/kpis/${editing}`, draft);
      setEditing(null); setDraft({ name: '', baseline: '', target: '', unit: '%',
        measurement_method: '', evidence_source: '', success_threshold: '', direction: 'reduce' });
      load(); notify('KPI saved');
    } catch (e) { notify(e.message); }
  }

  async function handleAdd() {
    if (!draft.name) { notify('KPI name is required'); return; }
    try {
      const res = await api.post(`/api/pilots/${id}/kpis`, draft);
      load(); setDraft({ name: '', baseline: '', target: '', unit: '%',
        measurement_method: '', evidence_source: '', success_threshold: '', direction: 'reduce' });
      notify('KPI added');
    } catch (e) { notify(e.message); }
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <button className="btn-quiet btn-sm mb-2" onClick={() => nav(`/pilots/${id}`)}>← Back to pilot record</button>
        <div className="eyebrow">Pilot KPI Monitoring</div>
        <h1 className="text-primary text-headline-lg font-bold">KPIs</h1>
        <p className="mt-1 text-[14px] text-ink-2">
          Every KPI has a baseline, target, measurement method and evidence source. Startup claims and
          instrumented observations are recorded separately (Claim ≠ Evidence ≠ Validation).
        </p>
      </header>

      {!kpis.length ? (
        <Card>
          <EmptyState title="No KPIs yet">
            Pilot KPIs are cloned from the challenge's KPI builder when the pilot is created. Add one below.
          </EmptyState>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>KPI</th><th>Baseline</th><th>Target</th><th>Unit</th>
                  <th>Measurement method</th><th>Evidence source</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {kpis.map((k) => (
                  <tr key={k.id}>
                    <td className="font-semibold">{k.name}</td>
                    <td>{k.baseline || '—'}</td>
                    <td><strong>{k.target}</strong> <span className="text-ink-2">{k.unit}</span></td>
                    <td className="text-ink-2">{k.unit}</td>
                    <td className="text-[12px] text-ink-2">{k.measurement_method || '—'}</td>
                    <td className="text-[12px] text-ink-2">{k.evidence_source || '—'}</td>
                    <td><Badge value={k.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {canEdit && (<p>Add a pilot-level KPI below. Pilot KPIs are monitored separately from challenge KPIs.</p>)}

      {canEdit && (
        <Card eyebrow="Add KPI">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="KPI name*"><input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></Field>
            <Field label="Baseline"><input value={draft.baseline} onChange={(e) => setDraft({ ...draft, baseline: e.target.value })} placeholder="12%" /></Field>
            <Field label="Target"><input value={draft.target} onChange={(e) => setDraft({ ...draft, target: e.target.value })} placeholder="20%" /></Field>
            <Field label="Unit"><input value={draft.unit} onChange={(e) => setDraft({ ...draft, unit: e.target.value })} /></Field>
            <Field label="Measurement method"><input value={draft.measurement_method} onChange={(e) => setDraft({ ...draft, measurement_method: e.target.value })} /></Field>
            <Field label="Evidence source"><input value={draft.evidence_source} onChange={(e) => setDraft({ ...draft, evidence_source: e.target.value })} /></Field>
            <Field label="Success threshold"><input value={draft.success_threshold} onChange={(e) => setDraft({ ...draft, success_threshold: e.target.value })} placeholder="≥ 18%" /></Field>
            <div className="flex gap-2">
              <button className="btn-primary" onClick={handleAdd} disabled={busy}>＋ Add KPI</button>
              {editing && (
                <>
                  <button className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
                  <button className="btn-primary" onClick={handleSave}>Save</button>
                </>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

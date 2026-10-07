import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, Modal, Field } from '../components/ui';
import { label } from '../lib/format';

const MILESTONE_STATUSES = ['NOT_STARTED', 'IN_PROGRESS', 'SUBMITTED', 'ACCEPTED', 'BLOCKED'];
const PAYMENT_STATUSES = ['NOT_ELIGIBLE', 'PENDING_APPROVAL', 'APPROVED', 'RELEASED'];

export default function Milestones({ notify }) {
  const { id } = useParams();
  const nav = useNavigate();
  const [milestones, setMilestones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState({ name: '', description: '', start_date: '', end_date: '',
    deliverable: '', kpi_dependency: '', payment_percentage: 0 });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.get(`/api/pilots/${id}`).then((p) => setMilestones(p.milestones || [])).catch(setError)
      .finally(() => setLoading(false));
  }, [id]);
  useEffect(load, [load]);

  if (error) return <ErrorState error={error} />;
  if (loading) return <Loading label="Loading milestones…" />;

  const canEdit = ['government_officer', 'administrator', 'startup'].includes(
    (localStorage.getItem('gv_user') && JSON.parse(localStorage.getItem('gv_user')).role) || 'government_officer');

  async function save(m) {
    if (!m.name.trim()) { notify('Milestone name is required'); return; }
    if (!m.payment_percentage) { notify('Payment percentage is required'); return; }
    try { await api.patch(`/api/pilots/${id}/milestones/${m.id}/status`, m); load(); notify('Milestone saved'); }
    catch (e) { notify(e.message); }
  }

  async function remove(mId) {
    if (!window.confirm('Delete this milestone?')) return;
    try { await api.del(`/api/pilots/${id}/milestones/${mId}`); load(); notify('Milestone deleted'); }
    catch (e) { notify(e.message); }
  }

  async function handleSave() {
    if (!draft.name) { notify('Milestone name is required'); return; }
    if (!draft.payment_percentage) { notify('Payment percentage is required'); return; }
    try {
      await api.patch(`/api/pilots/${id}/milestones/${editing}/status`, draft);
      setEditing(null); setDraft({ name: '', description: '', start_date: '', end_date: '',
        deliverable: '', kpi_dependency: '', payment_percentage: 0 });
      load(); notify('Milestone saved');
    } catch (e) { notify(e.message); }
  }

  async function handleAdd() {
    if (!draft.name) { notify('Milestone name is required'); return; }
    if (!draft.payment_percentage) { notify('Payment percentage is required'); return; }
    try {
      await api.post(`/api/pilots/${id}/milestones`, draft);
      load(); setDraft({ name: '', description: '', start_date: '', end_date: '',
        deliverable: '', kpi_dependency: '', payment_percentage: 0 });
      notify('Milestone added');
    } catch (e) { notify(e.message); }
  }

  const total = milestones.reduce((sum, m) => sum + (m.payment_percentage || 0), 0);

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header>
        <button className="btn-quiet btn-sm mb-2" onClick={() => nav(`/pilots/${id}`)}>← Back to pilot record</button>
        <div className="eyebrow">Pilot Milestone Management</div>
        <h1 className="text-primary text-headline-lg font-bold">Milestones & Payments</h1>
        <p className="mt-1 text-[14px] text-ink-2">
          Each milestone is a deliverable with an acceptance criterion and payment allocation. Payments are only eligible after the
          milestone is accepted with linked evidence (simulated workflow).
        </p>
      </header>

      <Card>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-primary text-headline-sm font-bold">Milestones</h2>
          <Badge value={total === 100 ? '✓ totals 100%' : `⚠ totals ${total}%`} />
        </div>
        {!milestones.length ? (
          <EmptyState title="No milestones yet">
            Milestones are created when the pilot is added in the pilot wizard. Add one below.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th><th>Deliverable</th><th>Start</th><th>End</th>
                  <th>Payment %</th><th>Payment</th><th>Status</th><th></th>
                </tr>
              </thead>
              <tbody>
                {milestones.map((m) => (
                  <tr key={m.id}>
                    <td className="font-semibold">{m.name}</td>
                    <td className="text-[12px] text-ink-2">{m.deliverable || '—'}</td>
                    <td className="text-[12px] text-ink-2">{m.start_date || '—'}</td>
                    <td className="text-[12px] text-ink-2">{m.end_date || '—'}</td>
                    <td className="mono text-[12px] font-bold">{m.payment_percentage}%</td>
                    <td className="text-[12px] text-ink-2">
                      {m.payment_status || '—'}
                    </td>
                    <td><Badge value={m.status} /></td>
                    <td className="text-right">
                      <button className="btn-danger btn-sm" onClick={() => remove(m.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {canEdit && (
        <Card eyebrow="Add Milestone">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Milestone name*"><input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></Field>
            <Field label="Start date"><input type="text" value={draft.start_date} onChange={(e) => setDraft({ ...draft, start_date: e.target.value })} placeholder="e.g. Week 1" /></Field>
            <Field label="End date"><input type="text" value={draft.end_date} onChange={(e) => setDraft({ ...draft, end_date: e.target.value })} placeholder="e.g. Week 2" /></Field>
            <Field label="Deliverable"><input value={draft.deliverable} onChange={(e) => setDraft({ ...draft, deliverable: e.target.value })} placeholder="e.g. 142 nodes live" /></Field>
            <Field label="KPI dependency"><input value={draft.kpi_dependency} onChange={(e) => setDraft({ ...draft, kpi_dependency: e.target.value })} placeholder="e.g. System Uptime" /></Field>
            <Field label="Payment percentage"><input type="number" min="0" max="100" value={draft.payment_percentage} onChange={(e) => setDraft({ ...draft, payment_percentage: Number(e.target.value) })} placeholder="e.g. 25" /></Field>
            <div className="flex gap-2">
              <button className="btn-primary" onClick={handleAdd} disabled={busy}>＋ Add Milestone</button>
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

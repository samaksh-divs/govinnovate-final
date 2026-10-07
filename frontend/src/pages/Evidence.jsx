import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Loading, Modal } from '../components/ui';
import { dt, label } from '../lib/format';

const EVIDENCE_TYPES = ['REPORT', 'TELEMETRY', 'PHOTO', 'CERTIFICATE', 'LOG', 'OTHER'];

export default function Evidence({ notify }) {
  const [rows, setRows] = useState(null);
  const [pilots, setPilots] = useState([]);
  const [kpis, setKpis] = useState([]);
  const [pilotFilter, setPilotFilter] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef();
  const formRef = useRef();

  const load = useCallback(() => {
    api.get(`/api/evidence${pilotFilter ? `?pilot_id=${pilotFilter}` : ''}`).then(setRows).catch(setError);
  }, [pilotFilter]);
  useEffect(load, [load]);
  useEffect(() => { api.get('/api/pilots').then(setPilots).catch(() => {}); }, []);

  useEffect(() => {
    if (pilotFilter) api.get(`/api/pilots/${pilotFilter}`).then((p) => setKpis(p.kpis)).catch(() => {});
    else setKpis([]);
  }, [pilotFilter]);

  async function upload(e) {
    e.preventDefault();
    const fd = new FormData(formRef.current);
    if (!fd.get('file').name) { notify('Choose a file first'); return; }
    try {
      await api.postForm(`/api/evidence`, fd);
      notify('Evidence uploaded — SHA-256 recorded (integrity, not truth)');
      setUploading(false); formRef.current?.reset(); load();
    } catch (err) { notify(err.message); }
  }

  async function review(evidenceId, status) {
    const note = status === 'NEEDS_CLARIFICATION' || status === 'REJECTED'
      ? prompt('Review note (required)') : '';
    if ((status === 'NEEDS_CLARIFICATION' || status === 'REJECTED') && !note) return;
    try {
      await api.patch(`/api/evidence/${evidenceId}/status?status=${status}&note=${encodeURIComponent(note || '')}`);
      notify(`Evidence marked ${label(status)}`); load();
    } catch (e) { notify(e.message); }
  }

  if (error) return <ErrorState error={error} />;

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Evidence Repository · Versioned & Checksummed</div>
          <h1 className="text-primary text-headline-lg font-bold">Evidence</h1>
          <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
            Every file receives a SHA-256 checksum. The checksum proves the file is unchanged since
            upload — it does <strong>not</strong> prove the content is truthful. Truth comes from
            independent validation.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setUploading(true)}>＋ Upload Evidence</button>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <select value={pilotFilter} onChange={(e) => setPilotFilter(e.target.value)}
          className="rounded border border-line bg-white px-3 py-2 text-[13px]">
          <option value="">All pilots</option>
          {pilots.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {rows && <span className="subtle">{rows.length} items</span>}
      </div>

      {!rows ? <Loading /> : rows.length === 0 ? (
        <EmptyState icon="▤" title="No evidence yet"
          action={<button className="btn-primary mt-3" onClick={() => setUploading(true)}>Upload the first evidence item</button>}>
          Evidence is submitted against pilots and KPIs, then reviewed and routed to validation.
        </EmptyState>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr>
                <th>Evidence</th><th>Pilot / KPI</th><th>Type</th><th>Claimed</th><th>SHA-256</th>
                <th>v</th><th>Status</th><th>Submitted</th><th>Review actions</th>
              </tr></thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <div className="font-semibold text-ink">{e.title}</div>
                      <div className="subtle max-w-[280px] truncate" title={e.description}>{e.description || e.file_name}</div>
                    </td>
                    <td className="text-[12px]">{e.pilot_name}<div className="subtle">{e.kpi_name || 'General'}</div></td>
                    <td><span className="badge-gray">{label(e.evidence_type)}</span></td>
                    <td className="mono text-ink-2">{e.claimed_value || '—'}</td>
                    <td className="mono max-w-[130px] truncate text-ink-2" title={`${e.sha256} — integrity only, not truth`}>{e.sha256.slice(0, 16)}…</td>
                    <td className="mono">{e.version}</td>
                    <td><Badge value={e.status} /></td>
                    <td className="text-[12px] text-ink-2">{e.submitted_by}<div>{dt(e.submission_date)}</div></td>
                    <td className="space-x-1 text-right whitespace-nowrap">
                      {e.status === 'UPLOADED' && <button className="btn-secondary btn-sm" onClick={() => review(e.id, 'UNDER_REVIEW')}>Review</button>}
                      {e.status === 'UNDER_REVIEW' && <>
                        <button className="btn-secondary btn-sm" onClick={() => review(e.id, 'ACCEPTED_FOR_MONITORING')}>Accept</button>
                        <button className="btn-secondary btn-sm" onClick={() => review(e.id, 'NEEDS_CLARIFICATION')}>Clarify</button>
                        <button className="btn-danger btn-sm" onClick={() => review(e.id, 'REJECTED')}>Reject</button>
                      </>}
                      {e.status === 'ACCEPTED_FOR_MONITORING' && <button className="btn-secondary btn-sm" onClick={() => review(e.id, 'READY_FOR_VALIDATION')}>Ready for validation</button>}
                      {e.status === 'NEEDS_CLARIFICATION' && <button className="btn-secondary btn-sm" onClick={() => review(e.id, 'UNDER_REVIEW')}>Re-review</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {uploading && (
        <Modal eyebrow="Secure upload" title="Upload Evidence" onClose={() => setUploading(false)}>
          <form ref={formRef} onSubmit={upload} className="space-y-3">
            <label className="field"><span>Pilot<span className="req">*</span></span>
              <select name="pilot_id" required defaultValue="">
                <option value="" disabled>Select pilot</option>
                {pilots.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select></label>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="field"><span>KPI (optional)</span>
                <select name="kpi_id" defaultValue="">
                  <option value="">General / not KPI-specific</option>
                  {kpis.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                </select></label>
              <label className="field"><span>Type</span>
                <select name="evidence_type" defaultValue="REPORT">
                  {EVIDENCE_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
                </select></label>
            </div>
            <label className="field"><span>Title<span className="req">*</span></span><input name="title" required /></label>
            <label className="field"><span>Description</span><textarea name="description" /></label>
            <label className="field"><span>Claimed value (e.g. 21% — stored as a claim, not a fact)</span><input name="claimed_value" /></label>
            <label className="field"><span>File<span className="req">*</span></span>
              <input ref={fileRef} type="file" name="file" required
                accept=".pdf,.png,.jpg,.jpeg,.csv,.xlsx,.docx,.txt,.json" />
              <span className="mt-1 block text-[12px] text-ink-2">Max 10MB. Allowed: pdf, png, jpg, jpeg, csv, xlsx, docx, txt, json. SHA-256 computed server-side.</span>
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-quiet" onClick={() => setUploading(false)}>Cancel</button>
              <button className="btn-primary">Upload ↗</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

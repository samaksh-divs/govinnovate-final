import { useCallback, useEffect, useState } from 'react';
import { api, getUser } from '../services/api';
import { Badge, Card, EmptyState, ErrorState, Modal } from '../components/ui';
import { DataProvenance, DataTag, Skeleton } from '../components/provenance';
import { dt } from '../lib/format';

export default function GovData({ notify }) {
  const [sources, setSources] = useState(null);
  const [datasets, setDatasets] = useState(null);
  const [logs, setLogs] = useState(null);
  const [meta, setMeta] = useState(null);   // dataset metadata modal payload
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const user = getUser();

  const load = useCallback(() => {
    api.get('/api/government-data/sources').then(setSources).catch(setError);
    api.get('/api/government-data/datasets').then(setDatasets).catch(setError);
    api.get('/api/government-data/refresh-status').then(setLogs).catch(() => {});
  }, []);

  useEffect(load, [load]);

  async function refreshAll() {
    setRefreshing(true);
    try {
      const res = await api.post('/api/government-data/refresh');
      notify(`Government data refreshed — ${res.imported.length} dataset operation(s); history preserved as new versions.`);
      load();
    } catch (e) {
      notify(e.status === 403
        ? 'Only an Administrator may refresh authoritative public datasets.'
        : e.message);
    } finally { setRefreshing(false); }
  }

  async function openMeta(id) {
    try { setMeta(await api.get(`/api/government-data/datasets/${id}/metadata`)); }
    catch (e) { notify(e.message); }
  }

  if (error) return <ErrorState error={error} />;

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow">Government Intelligence · Public Data Registry</div>
          <h1 className="text-primary text-headline-lg font-bold">Government Data</h1>
          <p className="mt-1 max-w-3xl text-[14px] text-ink-2">
            Connected public datasets power the ecosystem intelligence on the dashboard. Every figure is
            traceable to its source; snapshots are never presented as live feeds, and history is versioned —
            never overwritten.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DataTag kind="gov" />
          {user?.role === 'administrator' && (
            <button className="btn-primary btn-sm" disabled={refreshing} onClick={refreshAll}>
              {refreshing ? 'Refreshing…' : '↻ Refresh all (admin)'}
            </button>
          )}
        </div>
      </header>

      <div className="notice">
        <strong>Architecture:</strong> External Government Data → Ingestion providers (MSInS / OGD / DPIIT
        abstractions) → Versioned public-data models → Intelligence layer → Dashboard. This is kept strictly
        separate from GovInnovate workflow data (challenges → pilots → evidence → decisions).
        Refresh operations are administrator-only: officers cannot alter authoritative public data.
      </div>

      {/* ---------- sources ---------- */}
      <Card eyebrow="Connected sources" title="Provider registry">
        {!sources ? (
          <div className="space-y-2"><Skeleton w="60%" h={12} /><Skeleton w="80%" h={12} /><Skeleton w="70%" h={12} /></div>
        ) : sources.length === 0 ? (
          <EmptyState icon="⛁" title="No sources configured">Register a GovernmentDataProvider to import public datasets.</EmptyState>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {sources.map((s) => (
              <div key={s.id} className="rounded border border-hairline p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[13px] font-bold text-primary">{s.name}</div>
                  <span className={s.is_live_api ? 'tag-gov !min-h-[18px] !text-[9px]' : 'tag-ghost !min-h-[18px] !text-[9px]'}>
                    {s.is_live_api ? 'LIVE API' : 'SNAPSHOT'}
                  </span>
                </div>
                <div className="mt-1 text-[12px] text-ink-2">{s.organization}</div>
                <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="badge-gray">{s.domain}</span>
                  <span className="badge-gray">{s.geography}</span>
                  <span className="badge-gray">{s.datasets} dataset(s)</span>
                </div>
                {s.source_url && <a className="link mt-2 inline-block text-[12px]" href={s.source_url} target="_blank" rel="noreferrer">View source ↗</a>}
                <p className="mt-2 text-[11px] text-ink-2">{s.license_note}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ---------- datasets ---------- */}
      <Card eyebrow="Dataset registry" title="All imported public datasets">
        {!datasets ? (
          <div className="space-y-2"><Skeleton w="100%" h={12} /><Skeleton w="100%" h={12} /><Skeleton w="100%" h={12} /></div>
        ) : datasets.length === 0 ? (
          <EmptyState icon="⛁" title="No datasets imported">This dataset is currently unavailable from the configured public source.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr>
                <th>Dataset</th><th>Source Organization</th><th>Domain</th><th>Geography</th>
                <th>Data Type</th><th>Last Updated</th><th>Retrieval</th><th className="text-right">Records</th>
                <th>Status</th><th></th>
              </tr></thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div className="font-semibold text-ink">{d.title}</div>
                      {d.coverage_note && <div className="text-[11px] text-ink-2">{d.coverage_note}</div>}
                    </td>
                    <td className="text-[12px]">{d.source_organization}</td>
                    <td className="text-[12px]">{d.domain}</td>
                    <td className="text-[12px]">{d.geography}</td>
                    <td><span className="tag-gov !min-h-[18px] !px-1.5 !text-[9px]">{d.data_type}</span></td>
                    <td className="text-[12px]">{d.last_updated ? dt(d.last_updated) : <span className="text-ink-2">Not published</span>}</td>
                    <td className="text-[12px]">{dt(d.retrieved_at)}</td>
                    <td className="mono text-right">{d.records}</td>
                    <td>
                      <span className={d.status === 'LIVE' ? 'tag-gov' : 'tag-ghost'}>{d.status}</span>
                      <span className="mono ml-1 text-[10px] text-ink-2">v{d.current_version}</span>
                    </td>
                    <td className="whitespace-nowrap text-right">
                      <button className="btn-secondary btn-sm mr-1" onClick={() => openMeta(d.id)}>Metadata</button>
                      {d.provenance?.source_url && (
                        <a className="btn-quiet btn-sm" href={d.provenance.source_url} target="_blank" rel="noreferrer">View source ↗</a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="subtle mt-3">Status values: SNAPSHOT = static import (clearly not a live API) · IMPORTED =
          batch load · LIVE = direct API. A refresh by an administrator creates a new immutable version; the
          previous snapshot remains queryable.</p>
      </Card>

      {/* ---------- refresh activity ---------- */}
      <Card eyebrow="Refresh activity" title="DataRefreshLog (most recent first)">
        {!logs ? (
          <Skeleton w="100%" h={12} />
        ) : logs.length === 0 ? (
          <p className="subtle">No refresh operations recorded yet.</p>
        ) : (
          <table className="tbl">
            <thead><tr><th>When</th><th>Dataset</th><th>Provider</th><th>Outcome</th><th>Detail</th><th className="text-right">Duration</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="mono text-[11px]">{dt(l.at)}</td>
                  <td className="mono text-[11px]">{l.dataset_id}</td>
                  <td className="text-[12px]">{l.provider}</td>
                  <td><Badge value={l.outcome === 'SUCCESS' ? 'APPROVED' : l.outcome === 'FAILED' ? 'REJECTED' : 'DRAFT'}>{l.outcome}</Badge></td>
                  <td className="text-[12px] text-ink-2">{l.detail}</td>
                  <td className="mono text-right text-[11px]">{l.duration_ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* ---------- metadata modal ---------- */}
      {meta && (
        <Modal title={meta.provenance?.dataset || 'Dataset metadata'} eyebrow="Versioned snapshot metadata" onClose={() => setMeta(null)} wide>
          <DataProvenance p={meta.provenance} />
          <div className="mt-4">
            <div className="eyebrow mb-1">Description</div>
            <p className="text-[13px]">{meta.description || '—'}</p>
            <div className="eyebrow mb-1 mt-3">Update frequency</div>
            <p className="text-[13px]">{meta.update_frequency || '—'}</p>
            {meta.coverage_note && (<><div className="eyebrow mb-1 mt-3">Coverage</div><p className="text-[13px]">{meta.coverage_note}</p></>)}
            <div className="eyebrow mb-1 mt-3">Version history</div>
            <table className="tbl">
              <thead><tr><th>Version</th><th>Records</th><th>Retrieved</th><th>SHA-256 (integrity)</th></tr></thead>
              <tbody>
                {(meta.versions || []).map((v) => (
                  <tr key={v.version}>
                    <td className="mono font-bold">v{v.version}</td>
                    <td className="mono">{v.records}</td>
                    <td className="text-[12px]">{dt(v.retrieved_at)}</td>
                    <td className="mono text-[10px] text-ink-2" title={v.checksum}>{(v.checksum || '').slice(0, 24)}…</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="warnbox mt-3 text-[12px]">{meta.integrity_note}</div>
          </div>
        </Modal>
      )}
    </div>
  );
}

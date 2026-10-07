import { dt } from '../lib/format';

/**
 * Data Provenance strip — spec §DATA PROVENANCE MUST BE VISIBLE.
 * Renders Source / Dataset / Data Type / Last Updated / Retrieved / Coverage / Status.
 * Never invents dates: fields are shown only when the API provides them.
 */
export function DataProvenance({ p, compact = false }) {
  if (!p) return null;
  const statusTone =
    p.status === 'LIVE' ? 'tag-gov' : p.status === 'UNAVAILABLE' ? 'tag-demo' : 'tag-ghost';
  return (
    <div className={`prov ${compact ? 'text-[10px]' : ''}`}>
      {!compact && (
        <>
          <div className="prov-row"><span className="prov-k">Source:</span><span>{p.source}</span></div>
          <div className="prov-row"><span className="prov-k">Dataset:</span><span>{p.dataset}</span></div>
          <div className="prov-row"><span className="prov-k">Data Type:</span><span>{p.data_type}</span></div>
          <div className="prov-row">
            <span className="prov-k">Last Updated:</span>
            <span>{p.last_updated ? dt(p.last_updated) : 'Not published by source'}</span>
          </div>
          <div className="prov-row">
            <span className="prov-k">Retrieved:</span>
            <span>{p.retrieved ? dt(p.retrieved) : '—'}</span>
          </div>
          {p.coverage && <div className="prov-row"><span className="prov-k">Coverage:</span><span>{p.coverage}</span></div>}
        </>
      )}
      <div className="prov-row">
        <span className="prov-k">Status:</span>
        <span className={`${statusTone} !min-h-[18px] !px-1.5 !text-[10px]`}>{p.status || 'SNAPSHOT'}</span>
        {p.source_url && (
          <a className="link" href={p.source_url} target="_blank" rel="noreferrer">View source ↗</a>
        )}
      </div>
    </div>
  );
}

/** Data-status tag: GOVERNMENT PUBLIC DATA / PLATFORM / DEMO / SIMULATED PILOT. */
export function DataTag({ kind = 'demo', children }) {
  const map = {
    gov: ['tag-gov', 'GOVERNMENT PUBLIC DATA'],
    platform: ['tag-platform', 'PLATFORM DATA'],
    platformDemo: ['tag-platform', 'PLATFORM DEMO DATA'],
    demo: ['tag-demo', 'DEMO DATA'],
    pilot: ['tag-demo', 'SIMULATED PILOT'],
  };
  const [cls, text] = map[kind] || map.demo;
  return <span className={cls}>{children || text}</span>;
}

/** Skeleton block for dashboard metrics/charts/tables. */
export function Skeleton({ w = '100%', h = 16, className = '' }) {
  return <span className={`skel ${className}`} style={{ width: w, height: h }} />;
}

/** Card-sized skeleton for full panels. */
export function SkeletonCard({ h = 160 }) {
  return (
    <div className="card card-pad" style={{ minHeight: h }}>
      <Skeleton w="40%" h={10} className="mb-3" />
      <Skeleton w="70%" h={26} className="mb-4" />
      <Skeleton w="100%" h={10} className="mb-2" />
      <Skeleton w="92%" h={10} className="mb-2" />
      <Skeleton w="96%" h={10} />
    </div>
  );
}

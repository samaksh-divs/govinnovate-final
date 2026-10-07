import { toneFor, label } from '../lib/format';

export function Badge({ value, children, tone }) {
  const t = tone || toneFor(value);
  return <span className={`badge-${t === 'navy' ? 'navy' : t}`}>{children ?? label(value)}</span>;
}

export function StatusBadge({ value }) { return <Badge value={value} />; }

export function Card({ title, eyebrow, right, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {(title || eyebrow || right) && (
        <div className="card-head card-pad">
          <div>
            {eyebrow && <div className="eyebrow mb-0.5">{eyebrow}</div>}
            {title && <h2 className="card-title">{title}</h2>}
          </div>
          {right}
        </div>
      )}
      <div className={title || eyebrow ? 'p-5 pt-4' : 'card-pad'}>{children}</div>
    </section>
  );
}

export function MetricCard({ label: text, value, delta, tone = 'blue', attention }) {
  const toneMap = {
    blue: 'bg-azure-soft text-azure', teal: 'bg-emerald-soft text-emerald',
    green: 'bg-emerald-soft text-emerald', orange: 'bg-gold-soft text-[#7B341E]',
    red: 'bg-crimson-soft text-crimson', navy: 'bg-primary-soft text-primary',
  };
  return (
    <div className="card card-pad">
      <div className="flex items-center justify-between">
        <div className="eyebrow">{text}</div>
        <span className={`flex h-8 w-8 items-center justify-center rounded-md text-[15px] font-bold ${toneMap[tone]}`}>◆</span>
      </div>
      <div className="mt-1 text-[28px] font-bold leading-9 text-primary">{value}</div>
      {delta && (
        <div className={`mt-1 text-[12px] font-semibold ${attention ? 'text-crimson' : 'text-ink-2'}`}>
          {attention ? '⚠ ' : '↗ '}{delta}
        </div>
      )}
    </div>
  );
}

export function Loading({ label: text = 'Loading…' }) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center gap-3 text-ink-2">
      <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-line border-t-primary" />
      <span className="text-[13px]">{text}</span>
    </div>
  );
}

export function EmptyState({ icon = '◎', title, children, action }) {
  return (
    <div className="card flex min-h-[220px] flex-col items-center justify-center gap-2 p-10 text-center">
      <div className="mb-1 flex h-12 w-12 items-center justify-center rounded-lg bg-surface-2 text-[22px]">{icon}</div>
      <h3 className="text-[16px] font-bold text-primary">{title}</h3>
      <p className="max-w-md text-[13px] text-ink-2">{children}</p>
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="errorbox flex items-center justify-between gap-4">
      <div>
        <strong>Something went wrong.</strong>
        <div className="mt-0.5 text-[12px]">{String(error?.message || error)}</div>
      </div>
      {onRetry && <button className="btn-secondary btn-sm" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Modal({ title, eyebrow, onClose, children, wide }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 md:p-8"
         onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`card w-full ${wide ? 'max-w-4xl' : 'max-w-2xl'} shadow-overlay`}>
        <div className="card-head card-pad">
          <div>
            {eyebrow && <div className="eyebrow mb-0.5">{eyebrow}</div>}
            <h2 className="text-primary text-headline-sm font-bold">{title}</h2>
          </div>
          <button className="btn-quiet btn-sm" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="card-pad">{children}</div>
      </div>
    </div>
  );
}

/** Explainable score bar: label, weight, value, bar. */
export function ScoreBar({ label: text, value, weight, tone = 'bg-primary' }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-[12px]">
        <span className="font-semibold text-ink">{text}{weight ? ` · ${weight}%` : ''}</span>
        <span className="font-mono font-bold text-primary">{value}</span>
      </div>
      <div className="progress-track"><div className={`progress-fill ${tone}`} style={{ width: `${Math.min(100, value)}%` }} /></div>
    </div>
  );
}

export function Field({ label: text, required, hint, children }) {
  return (
    <label className="field">
      <span>{text}{required && <span className="req">*</span>}</span>
      {children}
      {hint && <span className="mt-1 block text-[12px] text-ink-2">{hint}</span>}
    </label>
  );
}

/** Statutory pipeline stepper (Stitch reference: 8-stage chain). */
const STAGES = ['Problem', 'Discover', 'Evaluate', 'Pilot', 'Evidence', 'Validate', 'Decision', 'Scale'];
export function PipelineStepper({ current = 1, statuses = {} }) {
  return (
    <div className="grid grid-cols-2 gap-1 sm:grid-cols-4 xl:grid-cols-8">
      {STAGES.map((s, i) => {
        const idx = i + 1;
        const state = statuses[s] || (idx < current ? 'done' : idx === current ? 'active' : 'todo');
        const cls = state === 'done' ? 'bg-emerald-soft text-emerald border-[#A3D9B1]'
          : state === 'active' ? 'bg-primary text-white border-primary'
          : state === 'alert' ? 'bg-crimson-soft text-crimson border-[#FEB2B2]'
          : state === 'gated' ? 'bg-surface-2 text-ink-2/50 border-line'
          : 'bg-surface-2 text-ink-2 border-line';
        return (
          <div key={s} className={`rounded border px-2 py-1.5 ${cls}`}>
            <div className="text-[11px] font-bold uppercase leading-tight tracking-wide">
              {String(idx).padStart(2, '0')}. {s}
            </div>
            <div className="text-[10px] uppercase">
              {state === 'done' ? '✓ Completed' : state === 'active' ? '● Active'
                : state === 'alert' ? '! Attention' : state === 'gated' ? 'Locked' : 'Pending'}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** The product rule strip: Claim ≠ Evidence ≠ Validation ≠ Decision. */
export function ProductRules() {
  const rules = ['Claim ≠ Evidence', 'Evidence ≠ Validation', 'Validation ≠ Government Decision',
    'Match Score ≠ Evidence Confidence', 'AI Recommendation ≠ Government Decision',
    'Checksum ≠ Truth'];
  return (
    <div className="flex flex-wrap items-center gap-2">
      {rules.map((r) => <span key={r} className="badge-blue">{r}</span>)}
    </div>
  );
}

export function Toast({ toast }) {
  if (!toast) return null;
  return (
    <div className="fixed bottom-5 right-5 z-[60] max-w-sm">
      <div className="flex items-start gap-2 rounded-md bg-primary px-4 py-3 text-white shadow-overlay">
        <span className="text-emerald-soft">✓</span><span className="text-[13px]">{toast}</span>
      </div>
    </div>
  );
}

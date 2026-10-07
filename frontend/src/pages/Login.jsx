import { useState } from 'react';
import { api } from '../services/api';

const DEMO_ACCOUNTS = [
  ['arjun.kulkarni@demo.gov.in', 'Government Officer — Arjun Kulkarni'],
  ['meera.deshmukh@demo.gov.in', 'Senior Authority — Meera Deshmukh'],
  ['founder@aquasense.demo.in', 'Startup (AquaSense demo) — Priya Nair'],
  ['r.kelkar@demo-expert.in', 'Expert Evaluator — Prof. R. Kelkar'],
  ['v.deshpande@demo-validator.in', 'Independent Validator — V. Deshpande'],
  ['admin@demo.gov.in', 'Administrator'],
];

export default function Login({ onLogin, notify }) {
  const [email, setEmail] = useState('arjun.kulkarni@demo.gov.in');
  const [password, setPassword] = useState('govinnovate-demo');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const res = await api.post('/api/auth/login', { email, password });
      onLogin(res.access_token, res.user);
      notify(`Welcome, ${res.user.name}`);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally { setBusy(false); }
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <div className="flex h-6 items-center justify-between bg-primary px-4 text-[11px] font-bold uppercase tracking-wider text-white">
        <span>Official Portal of Government of Maharashtra</span>
        <span className="text-gold">SIH26136 · Demo Environment</span>
      </div>
      <div className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-10 px-6 py-10 lg:grid-cols-2">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded bg-primary text-lg font-bold text-white">G+</div>
            <div>
              <div className="text-[22px] font-bold tracking-tight text-primary">GovInnovate Maharashtra</div>
              <div className="text-[13px] text-ink-2">From Government Problem to Proven Innovation</div>
            </div>
          </div>
          <h1 className="mt-8 text-[34px] font-bold leading-tight tracking-tight text-primary">
            Evidence-Gated Decision Intelligence
          </h1>
          <p className="mt-3 max-w-lg text-[14px] leading-6 text-ink-2">
            Government should not have to trust a startup's claim. GovInnovate helps departments
            discover the right startup, run a controlled pilot, collect evidence, independently
            validate the outcome, and then make an evidence-backed decision.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {['Claim ≠ Evidence', 'Evidence ≠ Validation', 'Validation ≠ Government Decision',
              'AI Recommendation ≠ Government Decision', 'Checksum ≠ Truth'].map((r) => (
              <span key={r} className="badge-blue">{r}</span>
            ))}
          </div>
          <div className="notice mt-6 max-w-lg">
            <strong>Demo notice:</strong> all data on this platform is fictional demo data for
            evaluation of SIH26136. No real startups, persons, or government datasets are represented.
          </div>
        </div>

        <div className="card card-pad">
          <h2 className="text-primary text-headline-sm font-bold">Sign in</h2>
          <p className="subtle mt-1">JWT-secured session · server-side RBAC enforced on every API.</p>
          <form onSubmit={submit} className="mt-4 space-y-4">
            <label className="field">
              <span>Official email<span className="req">*</span></span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </label>
            <label className="field">
              <span>Password<span className="req">*</span></span>
              <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
            </label>
            {error && <div className="errorbox">{error}</div>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>
          <div className="mt-5 border-t border-hairline pt-4">
            <div className="eyebrow mb-2">Demo accounts · password: govinnovate-demo</div>
            <div className="grid gap-1.5">
              {DEMO_ACCOUNTS.map(([mail, who]) => (
                <button key={mail}
                  className="flex items-center justify-between rounded px-2 py-1.5 text-left text-[12px] hover:bg-canvas"
                  onClick={() => { setEmail(mail); setPassword('govinnovate-demo'); }}>
                  <span className="font-semibold text-ink">{who}</span>
                  <span className="mono text-ink-2">{mail.split('@')[0]}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

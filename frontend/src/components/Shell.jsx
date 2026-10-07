import { useEffect, useRef, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { api, clearAuth, getUser } from '../services/api';

/**
 * Navigation mirrors the government workflow lifecycle (spec §SIDEBAR).
 * Items that live inside a module deep-link there; tooltips clarify.
 */
const NAV = [
  { group: 'Overview', items: [['/dashboard', 'Dashboard', '▦']] },
  {
    group: 'Challenge & Discovery',
    items: [
      ['/challenges', 'Challenges', '⚐'],
      ['/startups', 'Startups', '◎'],
      ['/matching', 'Matching', '⇄'],
    ],
  },
  {
    group: 'Evaluation',
    items: [
      ['/evaluations', 'Evaluations', '✔'],
      ['/evaluations', 'Conflict of Interest', '§', 'COI workflow · inside Evaluations'],
    ],
  },
  {
    group: 'Pilot Management',
    items: [
      ['/pilots', 'Pilots', '◈'],
      ['/pilots/:id/kpis', 'KPIs', '≔', 'Pilot KPIs · inside Pilot Records'],
      ['/pilots/:id/milestones', 'Milestones', '◫', 'Milestones & payments · inside Pilot Records'],
    ],
  },
  {
    group: 'Evidence & Validation',
    items: [
      ['/evidence', 'Evidence', '▤'],
      ['/validation', 'Validation', '✓'],
    ],
  },
  {
    group: 'Decision',
    items: [
      ['/decisions', 'Decisions', '⚖'],
      ['/scaleup', 'Scale-Up', '↥'],
      ['/repilots', 'Re-Pilot', '↻'],
    ],
  },
  { group: 'Procurement', items: [['/procurement', 'Procurement Preparation', '❑']] },
  { group: 'Knowledge', items: [['/knowledge', 'Knowledge Centre', '✦']] },
  {
    group: 'Government Intelligence',
    items: [
      ['/analytics', 'Analytics', '▥'],
      ['/govdata', 'Government Data', '⛁'],
      ['/audit', 'Audit', '≡'],
      ['/system', 'System Health', '⚙'],
    ],
  },
];

const ROLE_ORDER = ['government_officer', 'senior_authority', 'startup', 'expert', 'validator', 'administrator'];

export default function Shell({ children, onRoleSwitch, notify }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [results, setResults] = useState(null);
  const [demo, setDemo] = useState(null);
  const [roles, setRoles] = useState([]);
  const [bell, setBell] = useState(null); // { activity, bottlenecks }
  const [bellOpen, setBellOpen] = useState(false);
  const user = getUser();
  const nav = useNavigate();
  const timer = useRef();

  useEffect(() => {
    api.get('/api/demo/story').then(setDemo).catch(() => {});
    api.get('/api/auth/roles').then(setRoles).catch(() => {});
    api.get('/api/analytics/overview')
      .then((a) => setBell({ activity: a.recent_activity || [], bottlenecks: a.bottlenecks || [] }))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (q.trim().length < 2) { setResults(null); return; }
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      api.get(`/api/search?q=${encodeURIComponent(q)}`)
        .then((r) => setResults(r.results))
        .catch(() => setResults([]));
    }, 250);
  }, [q]);

  async function switchRole(roleId) {
    const emailFor = {
      government_officer: 'arjun.kulkarni@demo.gov.in',
      senior_authority: 'meera.deshmukh@demo.gov.in',
      startup: 'founder@aquasense.demo.in',
      expert: 'r.kelkar@demo-expert.in',
      validator: 'v.deshpande@demo-validator.in',
      administrator: 'admin@demo.gov.in',
    };
    try {
      const res = await api.post('/api/auth/login', { email: emailFor[roleId], password: 'govinnovate-demo' });
      clearAuth();
      localStorage.setItem('gv_token', res.access_token);
      localStorage.setItem('gv_user', JSON.stringify(res.user));
      onRoleSwitch(res.user);
      notify(`Switched to ${res.user.name} — ${res.user.role_label}`);
      nav('/dashboard');
    } catch (e) { notify(e.message); }
  }

  const kindTag = { challenge: 'PLATFORM', startup: 'DEMO', pilot: 'SIMULATED PILOT', evidence: 'PLATFORM', decision: 'PLATFORM', knowledge: 'PLATFORM', govdata: 'GOVT DATA' };

  return (
    <div className="min-h-screen bg-canvas">
      {/* statutory / information strip */}
      <div className="flex h-6 items-center justify-between bg-primary px-4 text-[11px] font-bold uppercase tracking-wider text-white lg:px-8">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate">Government of Maharashtra</span>
          <span className="hidden opacity-40 md:inline">·</span>
          <span className="hidden truncate text-gold md:inline">Maharashtra State Innovation Society</span>
          <span className="hidden opacity-40 lg:inline">·</span>
          <span className="hidden truncate opacity-80 lg:inline">Innovation &amp; Public Procurement Enablement</span>
        </div>
        <div className="flex items-center gap-4 text-[#B0C9E8]">
          <span className="hidden items-center gap-1 lg:flex"><span className="text-emerald-soft">🛡</span> SIH26136 · Evidence-Gated Framework</span>
          <span>State Portal Services</span>
        </div>
      </div>

      {/* header */}
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-3 border-b border-hairline bg-white px-4 shadow-card lg:px-8">
        <div className="flex items-center gap-3">
          <button className="btn-quiet btn-sm lg:hidden" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
          {/* emblem */}
          <div className="flex h-10 w-10 items-center justify-center rounded border-2 border-gold bg-primary text-[15px] font-bold text-white">ग</div>
          <div className="hidden border-l border-hairline pl-3 leading-tight xl:block">
            <div className="text-[10px] font-bold uppercase tracking-[0.06em] text-ink-2">Government of Maharashtra</div>
            <div className="text-[10px] text-ink-2">Maharashtra State Innovation Society</div>
          </div>
          <div className="border-l border-hairline pl-3 leading-tight">
            <div className="text-[16px] font-bold tracking-tight text-primary">GovInnovate Maharashtra</div>
            <div className="text-[11px] text-ink-2">Innovation Pilot &amp; Evidence Intelligence Platform</div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* global search */}
          <div className="relative hidden md:block">
            <input
              value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Search challenges, startups, pilots, datasets…"
              className="w-56 rounded border border-line bg-canvas px-3 py-1.5 text-[13px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-gold/50 lg:w-72"
            />
            {results && (
              <div className="absolute right-0 top-10 z-50 max-h-[420px] w-[420px] overflow-y-auto rounded-lg border border-line bg-white p-2 shadow-overlay">
                {results.length === 0 && <div className="px-3 py-2 text-[13px] text-ink-2">No matches found.</div>}
                {results.map((r, i) => (
                  <button key={`${r.kind}-${r.id}-${i}`}
                    className="flex w-full items-start gap-2 rounded px-3 py-2 text-left hover:bg-canvas"
                    onClick={() => { setQ(''); setResults(null); nav(routeFor(r.kind, r.id)); }}>
                    <span className={`mt-0.5 ${r.kind === 'govdata' ? 'tag-gov' : 'badge-gray'} !min-h-[18px] !px-1.5 !text-[10px]`}>
                      {kindTag[r.kind] || r.kind}
                    </span>
                    <span>
                      <span className="block text-[13px] font-semibold text-ink">{r.title}</span>
                      <span className="block text-[12px] text-ink-2">{r.subtitle}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* notifications */}
          <div className="relative hidden sm:block">
            <button className="btn-quiet btn-sm relative" aria-label="Notifications"
              onClick={() => setBellOpen(!bellOpen)}>
              🔔
              {bell && bell.bottlenecks.length > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-crimson px-1 text-[9px] font-bold text-white">
                  {bell.bottlenecks.length}
                </span>
              )}
            </button>
            {bellOpen && bell && (
              <div className="absolute right-0 top-9 z-50 w-96 rounded-lg border border-line bg-white p-3 shadow-overlay">
                <div className="eyebrow mb-2">Pipeline attention</div>
                {bell.bottlenecks.length === 0 && <p className="subtle">No bottlenecks detected.</p>}
                <ul className="mb-3 space-y-1.5">
                  {bell.bottlenecks.slice(0, 4).map((b, i) => (
                    <li key={i} className="text-[12px]"><span className="badge-amber mr-1.5 !text-[10px]">{b.stage}</span>{b.item} — <span className="text-ink-2">{b.issue}</span></li>
                  ))}
                </ul>
                <div className="eyebrow mb-2 border-t border-hairline pt-2">Recent activity</div>
                <ul className="space-y-1 text-[12px] text-ink-2">
                  {bell.activity.slice(0, 5).map((a, i) => (
                    <li key={i} className="flex justify-between gap-2">
                      <span className="text-ink">{a.action}</span><span className="whitespace-nowrap">{a.actor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <a className="btn-quiet btn-sm hidden lg:inline-flex" href="/docs" target="_blank" rel="noreferrer" title="OpenAPI documentation">Help</a>

          {demo && <span className="demo-tag hidden lg:inline-flex" title={demo.notice}>DEMO</span>}

          {/* role authority chip */}
          {user && (
            <div className="flex items-center gap-2 rounded bg-canvas px-3 py-1.5">
              <span className="h-2 w-2 rounded-full bg-gold" />
              <div className="hidden leading-tight sm:block">
                <div className="text-[10px] font-bold uppercase text-ink-2">Role Authority</div>
                <select
                  className="bg-transparent text-[12px] font-bold text-primary focus:outline-none"
                  value={user.role}
                  onChange={(e) => switchRole(e.target.value)}
                  aria-label="Switch demo role"
                >
                  {ROLE_ORDER.map((r) => {
                    const info = roles.find((x) => x.id === r);
                    return <option key={r} value={r}>{info?.label || r}</option>;
                  })}
                </select>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-soft text-[11px] font-bold text-primary">
                {user.name.split(' ').map((w) => w[0]).slice(0, 2).join('')}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* persistent demo-environment banner (component-level data tags appear beside real data) */}
      <div className="demo-banner">
        <span>⚠ Demo Environment</span>
        <span className="hidden font-normal normal-case opacity-80 md:inline">
          Workflow records and pilot results shown here are simulated for demonstration.
          Genuine public datasets are tagged <span className="tag-gov !mx-1 !min-h-[16px] !py-0 !text-[9px]">GOVERNMENT PUBLIC DATA</span> at component level.
        </span>
      </div>

      <div className="flex">
        {/* sidebar */}
        <aside className={`fixed bottom-0 left-0 top-[112px] z-30 w-64 overflow-y-auto border-r border-hairline bg-white pb-6 transition-transform lg:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full'}`}>
          <button className={`nav-close lg:hidden ${open ? '' : 'hidden'}`} onClick={() => setOpen(false)} />
          {NAV.map((g) => (
            <div key={g.group} className="pt-4">
              <div className="px-5 pb-1 text-[11px] font-bold uppercase tracking-wider text-ink-2">{g.group}</div>
              <nav className="flex flex-col gap-0.5 px-2">
                {g.items.map(([to, text, icon, title]) => (
                  <NavLink key={g.group + text} to={to} title={title || text}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded px-3 py-2 text-[13px] font-semibold transition-colors ${
                        isActive ? 'bg-primary-soft text-primary' : 'text-ink-2 hover:bg-canvas hover:text-ink'}`}
                    onClick={() => setOpen(false)}>
                    <span className="w-4 text-center" aria-hidden>{icon}</span>{text}
                  </NavLink>
                ))}
              </nav>
            </div>
          ))}
          <div className="mx-4 mt-6 rounded bg-canvas p-3">
            <div className="flex items-center gap-1 text-[11px] font-bold text-primary">🔒 Cryptographic Integrity</div>
            <p className="mono mt-1 text-ink-2">LEDGER: MH-PILOT-8821B</p>
            <p className="mt-1 text-[10px] leading-3 text-ink-2">SHA-256 = integrity, not truth.</p>
          </div>
          {demo?.shortcuts?.challenge && (
            <div className="mx-4 mt-3 rounded border border-gold/30 bg-gold-soft p-3">
              <div className="text-[11px] font-bold uppercase text-[#7B341E]">Demo Story</div>
              <button className="link mt-1 block text-left text-[12px]" onClick={() => nav(`/pilots/${demo.shortcuts.water_pilot?.id || ''}`)}>
                Open water pilot ↗
              </button>
              <button className="link block text-left text-[12px]" onClick={() => nav(`/challenges/${demo.shortcuts.challenge.id}`)}>
                Open demo challenge ↗
              </button>
            </div>
          )}
        </aside>

        {/* content */}
        <main className="min-h-[calc(100vh-112px)] w-full px-4 pb-12 pt-6 lg:ml-64 lg:max-w-[calc(100%-16rem)] lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function routeFor(kind, id) {
  return {
    challenge: `/challenges/${id}`, startup: `/startups/${id}`, pilot: `/pilots/${id}`,
    evidence: '/evidence', decision: '/decisions', knowledge: '/knowledge',
    govdata: '/govdata',
  }[kind] || '/dashboard';
}

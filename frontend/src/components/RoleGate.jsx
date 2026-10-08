import { Link, useLocation } from 'react-router-dom';
import { getUser } from '../services/api';
import { rolesForPath, PERSONA_META } from '../lib/personas';
import { Card } from './ui';

/**
 * Role-aware route protection. An unauthorized persona never crashes and never
 * sees broken UI: it gets an access-restricted state and a path back to its
 * own dashboard. The backend independently enforces every rule again (RBAC),
 * so this is UX, not security.
 */
export default function RoleGate({ children }) {
  const location = useLocation();
  const user = getUser();
  const allowed = rolesForPath(location.pathname);

  if (!allowed || !user || allowed.includes(user.role)) return children;

  const meta = PERSONA_META[user.role] || {};
  return (
    <Card eyebrow="Access restricted" title="This area belongs to a different role">
      <p className="text-[13px] leading-6 text-ink-2">
        You are signed in as <strong className="text-ink">{meta.label || user.role_label || user.role}</strong>{' '}
        ({meta.tagline || 'persona'}). The page <code className="mono">{location.pathname}</code> is reserved
        for: {allowed.map((r) => PERSONA_META[r]?.label || r).join(', ')}.
      </p>
      <p className="mt-2 text-[12px] text-ink-2">
        Role authority is enforced server-side on every API; this page is outside your role's scope.
      </p>
      <div className="mt-4 flex gap-2">
        <Link className="btn-primary btn-sm" to="/dashboard">Go to my dashboard</Link>
        <Link className="btn-secondary btn-sm" to="/knowledge">Open Knowledge Centre</Link>
      </div>
    </Card>
  );
}

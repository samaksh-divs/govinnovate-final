import { StrictMode, useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import './index.css';
import { api, clearAuth, getToken, getUser, setAuth } from './services/api';
import Shell from './components/Shell';
import { Loading, Toast } from './components/ui';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ChallengeList from './pages/ChallengeList';
import ChallengeWizard from './pages/ChallengeWizard';
import ChallengeDetail from './pages/ChallengeDetail';
import Startups from './pages/Startups';
import StartupDetail from './pages/StartupDetail';
import Matching from './pages/Matching';
import Evaluations from './pages/Evaluations';
import PilotList from './pages/PilotList';
import PilotDetail from './pages/PilotDetail';
import Kpis from './pages/Kpis';
import Milestones from './pages/Milestones';
import Evidence from './pages/Evidence';
import Validation from './pages/Validation';
import Decisions from './pages/Decisions';
import DecisionDetail from './pages/DecisionDetail';
import ScaleUp from './pages/ScaleUp';
import ScaleDetail from './pages/ScaleDetail';
import Procurement from './pages/Procurement';
import ProcurementDetail from './pages/ProcurementDetail';
import Repilots from './pages/Repilots';
import Knowledge from './pages/Knowledge';
import Analytics from './pages/Analytics';
import GovData from './pages/GovData';
import Audit from './pages/Audit';
import SystemHealth from './pages/SystemHealth';

function App() {
  const [user, setUser] = useState(getUser());
  const [authed, setAuthed] = useState(!!getToken());
  const [toast, setToast] = useState('');
  const location = useLocation();

  const notify = useCallback((m) => {
    setToast(m);
    window.clearTimeout(window.__gvToast);
    window.__gvToast = window.setTimeout(() => setToast(''), 3500);
  }, []);

  useEffect(() => {
    const onLogout = () => { setAuthed(false); setUser(null); };
    window.addEventListener('gv-logout', onLogout);
    return () => window.removeEventListener('gv-logout', onLogout);
  }, []);

  function handleLogin(token, u) {
    setAuth(token, u);
    setAuthed(true);
    setUser(u);
  }
  function handleRoleSwitch(u) { setUser(u); setAuthed(true); }

  if (!authed) return <Login onLogin={handleLogin} notify={notify} />;

  return (
    <Shell onRoleSwitch={handleRoleSwitch} notify={notify}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard notify={notify} />} />
        <Route path="/challenges" element={<ChallengeList notify={notify} />} />
        <Route path="/challenges/new" element={<ChallengeWizard notify={notify} />} />
        <Route path="/challenges/:id" element={<ChallengeDetail notify={notify} />} />
        <Route path="/startups" element={<Startups notify={notify} />} />
        <Route path="/startups/:id" element={<StartupDetail notify={notify} />} />
        <Route path="/matching" element={<Matching notify={notify} />} />
        <Route path="/matching/:challengeId" element={<Matching notify={notify} />} />
        <Route path="/evaluations" element={<Evaluations notify={notify} />} />
        <Route path="/pilots" element={<PilotList notify={notify} />} />
        <Route path="/pilots/:id/kpis" element={<Kpis notify={notify} />} />
        <Route path="/pilots/:id/milestones" element={<Milestones notify={notify} />} />
        <Route path="/pilots/:id" element={<PilotDetail notify={notify} />} />
        <Route path="/evidence" element={<Evidence notify={notify} />} />
        <Route path="/validation" element={<Validation notify={notify} />} />
        <Route path="/decisions" element={<Decisions notify={notify} />} />
        <Route path="/decisions/:pilotId" element={<DecisionDetail notify={notify} />} />
        <Route path="/scaleup" element={<ScaleUp notify={notify} />} />
        <Route path="/scaleup/:pilotId" element={<ScaleDetail notify={notify} />} />
        <Route path="/procurement" element={<Procurement notify={notify} />} />
        <Route path="/procurement/:pilotId" element={<ProcurementDetail notify={notify} />} />
        <Route path="/repilots" element={<Repilots notify={notify} />} />
        <Route path="/knowledge" element={<Knowledge notify={notify} />} />
        <Route path="/analytics" element={<Analytics notify={notify} />} />
        <Route path="/govdata" element={<GovData notify={notify} />} />
        <Route path="/audit" element={<Audit notify={notify} />} />
        <Route path="/system" element={<SystemHealth notify={notify} />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toast toast={toast} />
      {/* keep location referenced for future breadcrumbs */}
      <span className="hidden">{location.pathname}</span>
    </Shell>
  );
}

// silence unused import warning for Loading (used inside pages)
void Loading;

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);

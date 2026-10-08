import { getUser } from '../services/api';
import OfficerDashboard from './dashboards/OfficerDashboard';
import SeniorAuthorityDashboard from './dashboards/SeniorAuthorityDashboard';
import ExpertDashboard from './dashboards/ExpertDashboard';
import StartupDashboard from './dashboards/StartupDashboard';
import ValidatorDashboard from './dashboards/ValidatorDashboard';
import AdminDashboard from './dashboards/AdminDashboard';

/**
 * ONE dashboard route → the active persona's own view of the SAME platform.
 * Every role view reads from the same shared backend records; switching persona
 * never resets data (see Shell.switchRole → JWT re-login, then this dispatch).
 */
export default function Dashboard({ notify }) {
  const role = getUser()?.role;
  const View = {
    senior_authority: SeniorAuthorityDashboard,
    startup: StartupDashboard,
    expert: ExpertDashboard,
    validator: ValidatorDashboard,
    administrator: AdminDashboard,
  }[role] || OfficerDashboard;
  return <View notify={notify} />;
}

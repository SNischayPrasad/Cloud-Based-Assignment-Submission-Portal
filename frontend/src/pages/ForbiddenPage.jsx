import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLE_HOME, ROLE_LABELS } from '../utils/constants';

export default function ForbiddenPage({ requiredRoles = [] }) {
  const { user } = useAuth();
  const needed = requiredRoles.map((r) => ROLE_LABELS[r].toLowerCase()).join(' or ');
  return (
    <div className="status-page">
      <span className="stamp stamp--denied stamp--big">403 · Access denied</span>
      <h1 className="page-title">This page is for {needed || 'other'} accounts.</h1>
      <p className="muted">
        You are logged in as a {ROLE_LABELS[user?.role]?.toLowerCase()}. The server enforces the same rule, so this
        data cannot be reached through the API either.
      </p>
      <Link className="btn btn--primary" to={ROLE_HOME[user?.role] || '/'}>
        Go to your dashboard
      </Link>
    </div>
  );
}

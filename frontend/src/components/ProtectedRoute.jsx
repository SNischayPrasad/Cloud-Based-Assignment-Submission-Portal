import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ForbiddenPage from '../pages/ForbiddenPage';

/**
 * Route guard.
 * - Not logged in  -> redirect to /login (and come back afterwards)
 * - Wrong role     -> show the 403 page
 *
 * This only improves the user experience. Real protection is on the API:
 * every endpoint re-checks the token and role on the server.
 */
export default function ProtectedRoute({ roles, children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <ForbiddenPage requiredRoles={roles} />;
  return children;
}

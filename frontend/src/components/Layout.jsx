import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLE_HOME, ROLE_LABELS } from '../utils/constants';

const NAV = {
  student: [
    ['/student', 'Dashboard'],
    ['/assignments', 'Assignments'],
    ['/submissions', 'My submissions'],
    ['/courses', 'Courses'],
  ],
  teacher: [
    ['/teacher', 'Dashboard'],
    ['/assignments', 'Assignments'],
    ['/assignments/new', 'New assignment'],
    ['/courses', 'Courses'],
  ],
  admin: [
    ['/teacher', 'Overview'],
    ['/assignments', 'Assignments'],
    ['/courses', 'Courses'],
    ['/admin', 'Users & audit'],
  ],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar__inner">
          <NavLink to={ROLE_HOME[user.role]} className="brand" aria-label="Handin home">
            <span className="brand__mark" aria-hidden="true">✓</span>
            <span className="brand__name">Handin</span>
          </NavLink>
          <nav className="nav" aria-label="Main">
            {NAV[user.role].map(([to, label]) => (
              <NavLink key={to} to={to} end className={({ isActive }) => `nav__link${isActive ? ' is-active' : ''}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="whoami">
            <span className="whoami__name">{user.name}</span>
            <span className="whoami__role">{ROLE_LABELS[user.role]}</span>
            <button type="button" className="btn btn--ghost btn--sm" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}

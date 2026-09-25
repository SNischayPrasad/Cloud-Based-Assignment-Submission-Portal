import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Alert } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { getErrorMessage } from '../services/api';
import { ROLE_HOME } from '../utils/constants';
import AuthShell from './AuthShell';

const DEMO_ACCOUNTS = [
  ['Teacher', 'meera.iyer@portal.dev'],
  ['Student', 'priya@portal.dev'],
  ['Admin', 'admin@portal.dev'],
];

export default function LoginPage() {
  const { user, login, sessionNotice, clearSessionNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const loggedIn = await login(email.trim(), password);
      const from = location.state?.from;
      navigate(from && from !== '/' ? from : ROLE_HOME[loggedIn.role], { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, 'Could not log in.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="card form" onSubmit={handleSubmit} noValidate>
        <h2 className="form__title">Log in</h2>
        <Alert kind="info" onClose={clearSessionNotice}>{sessionNotice}</Alert>
        <Alert>{error}</Alert>

        <label className="field">
          <span className="field__label">Email</span>
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Password</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className="btn btn--primary btn--block" disabled={busy || !email || !password}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
        <p className="form__alt">
          New student? <Link to="/register">Create an account</Link>
        </p>

        {import.meta.env.DEV && (
          <details className="demo">
            <summary>Demo accounts (after running the seed script)</summary>
            <ul>
              {DEMO_ACCOUNTS.map(([role, demoEmail]) => (
                <li key={demoEmail}>
                  <button type="button" className="linklike" onClick={() => setEmail(demoEmail)}>
                    {demoEmail}
                  </button>
                  <span className="muted"> · {role}</span>
                </li>
              ))}
            </ul>
            <p className="muted small">Password: the SEED_DEMO_PASSWORD value from your .env</p>
          </details>
        )}
      </form>
    </AuthShell>
  );
}

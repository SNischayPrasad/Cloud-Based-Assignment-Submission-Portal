import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Alert } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { getErrorMessage } from '../services/api';
import { authService } from '../services/authService';
import { ROLE_HOME } from '../utils/constants';
import AuthShell from './AuthShell';

function validate({ name, email, password, confirm }) {
  if (name.trim().length < 2) return 'Enter your full name.';
  if (!/^\S+@\S+\.\S+$/.test(email)) return 'Enter a valid email address.';
  if (password.length < 8) return 'Password must be at least 8 characters.';
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return 'Password needs at least one letter and one number.';
  if (password !== confirm) return 'The two passwords do not match.';
  return '';
}

export default function RegisterPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    const problem = validate(form);
    if (problem) return setError(problem);
    setError('');
    setBusy(true);
    try {
      await authService.register({ name: form.name.trim(), email: form.email.trim(), password: form.password });
      await login(form.email.trim(), form.password);
      navigate('/courses', { replace: true, state: { welcome: true } });
    } catch (err) {
      setError(getErrorMessage(err, 'Could not create your account.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="card form" onSubmit={handleSubmit} noValidate>
        <h2 className="form__title">Create a student account</h2>
        <p className="muted small">Teacher accounts are created by the portal administrator.</p>
        <Alert>{error}</Alert>

        <label className="field">
          <span className="field__label">Full name</span>
          <input autoComplete="name" value={form.name} onChange={update('name')} required />
        </label>
        <label className="field">
          <span className="field__label">Email</span>
          <input type="email" autoComplete="email" value={form.email} onChange={update('email')} required />
        </label>
        <label className="field">
          <span className="field__label">Password</span>
          <input type="password" autoComplete="new-password" value={form.password} onChange={update('password')} required />
          <span className="field__hint">8+ characters with a letter and a number.</span>
        </label>
        <label className="field">
          <span className="field__label">Confirm password</span>
          <input type="password" autoComplete="new-password" value={form.confirm} onChange={update('confirm')} required />
        </label>
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="form__alt">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </AuthShell>
  );
}

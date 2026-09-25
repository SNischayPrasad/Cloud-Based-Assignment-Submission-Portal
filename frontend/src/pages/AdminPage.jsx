import { useState } from 'react';
import { Alert, Loading, PageHeader } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import useLoad from '../hooks/useLoad';
import { getErrorMessage } from '../services/api';
import { adminService } from '../services/adminService';
import { formatDateTime } from '../utils/format';

export default function AdminPage() {
  const [tab, setTab] = useState('users');
  return (
    <>
      <PageHeader eyebrow="Administration" title="Users & audit log" />
      <div className="tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'users'} className={`tab${tab === 'users' ? ' is-active' : ''}`} onClick={() => setTab('users')}>
          Users
        </button>
        <button type="button" role="tab" aria-selected={tab === 'audit'} className={`tab${tab === 'audit' ? ' is-active' : ''}`} onClick={() => setTab('audit')}>
          Audit log
        </button>
      </div>
      {tab === 'users' ? <UsersPanel /> : <AuditPanel />}
    </>
  );
}

function UsersPanel() {
  const { user: me } = useAuth();
  const { data: users, error, loading, reload } = useLoad(() => adminService.users(), []);
  const [actionError, setActionError] = useState('');
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'teacher' });
  const [notice, setNotice] = useState('');

  const change = async (id, changes) => {
    setActionError('');
    try {
      await adminService.updateUser(id, changes);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const create = async (event) => {
    event.preventDefault();
    setActionError('');
    try {
      const created = await adminService.createUser(form);
      setNotice(`Created ${created.role} account for ${created.email}.`);
      setForm({ name: '', email: '', password: '', role: 'teacher' });
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  return (
    <>
      <form className="card form form--wide" onSubmit={create}>
        <h2 className="section-title">Create an account</h2>
        <div className="form-grid form-grid--4">
          <label className="field"><span className="field__label">Name</span>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label className="field"><span className="field__label">Email</span>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label>
          <label className="field"><span className="field__label">Temporary password</span>
            <input type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></label>
          <label className="field"><span className="field__label">Role</span>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="teacher">Teacher</option><option value="student">Student</option><option value="admin">Admin</option>
            </select></label>
        </div>
        <div className="button-row"><button type="submit" className="btn btn--primary">Create account</button></div>
        <Alert kind="success" onClose={() => setNotice('')}>{notice}</Alert>
      </form>

      <Alert>{error || actionError}</Alert>
      {loading && !users && <Loading />}
      {users && (
        <div className="card table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.user_id} className={u.is_active ? '' : 'is-muted'}>
                  <td>{u.name}</td>
                  <td className="mono small">{u.email}</td>
                  <td>
                    <select aria-label={`Role for ${u.name}`} value={u.role} disabled={u.user_id === me.user_id}
                      onChange={(e) => change(u.user_id, { role: e.target.value })}>
                      <option value="student">Student</option><option value="teacher">Teacher</option><option value="admin">Admin</option>
                    </select>
                  </td>
                  <td>
                    <button type="button" className="btn btn--ghost btn--sm" disabled={u.user_id === me.user_id}
                      onClick={() => change(u.user_id, { is_active: !u.is_active })}>
                      {u.is_active ? 'Deactivate' : 'Reactivate'}
                    </button>
                  </td>
                  <td className="nowrap">{formatDateTime(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function AuditPanel() {
  const { data: logs, error, loading, reload } = useLoad(() => adminService.auditLogs(150), []);
  return (
    <>
      <div className="button-row"><button type="button" className="btn btn--ghost btn--sm" onClick={reload}>Refresh</button></div>
      <Alert>{error}</Alert>
      {loading && !logs && <Loading />}
      {logs && (
        <div className="card table-wrap">
          <table className="table table--dense">
            <thead><tr><th>When</th><th>Action</th><th>User</th><th>Entity</th><th>IP</th><th>Details</th></tr></thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.audit_id}>
                  <td className="nowrap">{formatDateTime(log.created_at)}</td>
                  <td><span className={`audit-action ${log.action.includes('FAILED') ? 'is-bad' : ''}`}>{log.action}</span></td>
                  <td>{log.user_id ?? '—'}</td>
                  <td className="nowrap">{log.entity_type ? `${log.entity_type} #${log.entity_id}` : '—'}</td>
                  <td className="mono small">{log.ip_address || '—'}</td>
                  <td className="mono small break">{log.details || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

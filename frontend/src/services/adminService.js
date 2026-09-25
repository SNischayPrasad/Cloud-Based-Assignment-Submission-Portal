import api from './api';

export const adminService = {
  users: () => api.get('/admin/users').then((r) => r.data),
  createUser: (payload) => api.post('/admin/users', payload).then((r) => r.data),
  updateUser: (id, changes) => api.patch(`/admin/users/${id}`, changes).then((r) => r.data),
  auditLogs: (limit = 100) => api.get('/admin/audit-logs', { params: { limit } }).then((r) => r.data),
};

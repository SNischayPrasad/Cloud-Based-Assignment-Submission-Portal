import api from './api';

export const assignmentService = {
  list: (courseId) => api.get('/assignments', { params: courseId ? { course_id: courseId } : {} }).then((r) => r.data),
  get: (id) => api.get(`/assignments/${id}`).then((r) => r.data),
  create: (payload) => api.post('/assignments', payload).then((r) => r.data),
  update: (id, payload) => api.put(`/assignments/${id}`, payload).then((r) => r.data),
  remove: (id, force = false) => api.delete(`/assignments/${id}`, { params: { force } }).then((r) => r.data),
  submissions: (id) => api.get(`/assignments/${id}/submissions`).then((r) => r.data),
};

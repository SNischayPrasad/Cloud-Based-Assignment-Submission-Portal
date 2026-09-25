import api from './api';

export const courseService = {
  list: () => api.get('/courses').then((r) => r.data),
  create: (payload) => api.post('/courses', payload).then((r) => r.data),
  join: (joinCode) => api.post('/courses/join', { join_code: joinCode }).then((r) => r.data),
  roster: (courseId) => api.get(`/courses/${courseId}/students`).then((r) => r.data),
  enroll: (courseId, email) => api.post(`/courses/${courseId}/students`, { email }).then((r) => r.data),
};

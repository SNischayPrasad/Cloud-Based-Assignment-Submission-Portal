import api from './api';

export const dashboardService = {
  student: () => api.get('/dashboard/student').then((r) => r.data),
  teacher: () => api.get('/dashboard/teacher').then((r) => r.data),
};

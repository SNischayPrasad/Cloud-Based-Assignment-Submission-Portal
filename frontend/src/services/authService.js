import api from './api';

export const authService = {
  register: (payload) => api.post('/register', payload).then((r) => r.data),
  login: (email, password) => api.post('/login', { email, password }).then((r) => r.data),
  logout: () => api.post('/logout').then((r) => r.data),
  me: () => api.get('/me').then((r) => r.data),
};

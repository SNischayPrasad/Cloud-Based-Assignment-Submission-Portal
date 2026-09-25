/**
 * Shared HTTP client for the REST API.
 *
 * - Adds the JWT as "Authorization: Bearer <token>" to every request.
 * - When the server answers 401 for a logged-in user (expired / revoked
 *   token), clears the session and notifies the app so it can redirect
 *   to the login page.
 */
import axios from 'axios';

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const TOKEN_KEY = 'handin.token';
const USER_KEY = 'handin.user';

export const sessionStore = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser: () => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  },
  save: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  saveUser: (user) => localStorage.setItem(USER_KEY, JSON.stringify(user)),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

const api = axios.create({ baseURL: `${API_BASE_URL}/api`, timeout: 30000 });

api.interceptors.request.use((config) => {
  const token = sessionStore.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && sessionStore.getToken()) {
      sessionStore.clear();
      window.dispatchEvent(
        new CustomEvent('handin:session-ended', { detail: error.response.data?.detail || 'Your session has ended.' }),
      );
    }
    return Promise.reject(error);
  },
);

/** Turn any API/network error into one readable sentence. */
export function getErrorMessage(error, fallback = 'Something went wrong. Try again.') {
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED') return 'The request timed out. Check your connection and try again.';
    return 'Cannot reach the server. Check your internet connection or that the API is running.';
  }
  const { detail } = error.response.data || {};
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ');
  return fallback;
}

export default api;

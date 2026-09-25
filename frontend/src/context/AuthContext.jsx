import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { sessionStore } from '../services/api';
import { authService } from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (sessionStore.getToken() ? sessionStore.getUser() : null));
  const [sessionNotice, setSessionNotice] = useState('');

  // On load, confirm the stored token is still valid and refresh the role
  // from the server (the server is the source of truth, not localStorage).
  useEffect(() => {
    if (!sessionStore.getToken()) return;
    authService
      .me()
      .then((fresh) => {
        sessionStore.saveUser(fresh);
        setUser(fresh);
      })
      .catch(() => {});
  }, []);

  // api.js fires this when the server rejects our token (expired / logged out).
  useEffect(() => {
    const onEnded = (event) => {
      setUser(null);
      setSessionNotice(event.detail);
    };
    window.addEventListener('handin:session-ended', onEnded);
    return () => window.removeEventListener('handin:session-ended', onEnded);
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await authService.login(email, password);
    sessionStore.save(data.access_token, data.user);
    setSessionNotice('');
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout(); // revoke the token on the server
    } catch {
      // Even if the API is unreachable, forget the token locally.
    }
    sessionStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, login, logout, sessionNotice, clearSessionNotice: () => setSessionNotice('') }),
    [user, login, logout, sessionNotice],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}

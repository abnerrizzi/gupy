import { useCallback, useEffect, useState } from 'react';
import { ApiError, fetchJSON } from '../utils/api';

export default function useAuth() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');

  const refresh = useCallback(async () => {
    try {
      const data = await fetchJSON('/auth/me');
      setUser(data.user);
      setStatus('authenticated');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
        setStatus('anonymous');
        return;
      }
      setStatus('anonymous');
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = useCallback(async (username, password) => {
    const data = await fetchJSON('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setUser(data.user);
    setStatus('authenticated');
    return data.user;
  }, []);

  const register = useCallback(async (username, password) => {
    const data = await fetchJSON('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setUser(data.user);
    setStatus('authenticated');
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetchJSON('/auth/logout', { method: 'POST' });
    } catch {
      // ignore — local state is what matters for the SPA
    }
    setUser(null);
    setStatus('anonymous');
  }, []);

  return { user, status, login, register, logout, refresh };
}

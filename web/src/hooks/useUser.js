import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'jh_user';
const DEFAULT_USER = { name: '', email: '' };

const readInitial = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_USER, ...JSON.parse(raw) } : DEFAULT_USER;
  } catch {
    return DEFAULT_USER;
  }
};

export default function useUser() {
  const [user, setUserState] = useState(readInitial);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } catch {
      // ignore
    }
  }, [user]);

  const setUser = useCallback((next) => {
    setUserState((prev) => ({ ...prev, ...next }));
  }, []);

  return { user, setUser };
}

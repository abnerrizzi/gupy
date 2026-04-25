import { useCallback, useRef, useState } from 'react';

const DEFAULT_TIMEOUT = 4000;

export default function useToasts() {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  const dismiss = useCallback((id) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((toast) => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const next = {
      id,
      type: toast.type || 'error',
      message: typeof toast === 'string' ? toast : toast.message,
    };
    setToasts((prev) => [...prev, next]);
    const timer = setTimeout(() => dismiss(id), toast.timeout || DEFAULT_TIMEOUT);
    timersRef.current.set(id, timer);
    return id;
  }, [dismiss]);

  return { toasts, push, dismiss };
}

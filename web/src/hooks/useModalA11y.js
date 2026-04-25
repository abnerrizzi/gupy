import { useEffect, useRef } from 'react';

export default function useModalA11y({ isOpen, onClose, labelledBy }) {
  const closeBtnRef = useRef(null);
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    previousFocusRef.current = document.activeElement;
    closeBtnRef.current?.focus();

    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      if (previousFocusRef.current && previousFocusRef.current.focus) {
        previousFocusRef.current.focus();
      }
    };
  }, [isOpen, onClose]);

  return {
    closeBtnRef,
    dialogProps: {
      role: 'dialog',
      'aria-modal': 'true',
      ...(labelledBy ? { 'aria-labelledby': labelledBy } : {}),
    },
  };
}

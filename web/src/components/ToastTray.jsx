import React from 'react';
import PropTypes from 'prop-types';

function ToastTray({ toasts, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div className="toast-tray" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span>{t.message}</span>
          <button type="button" className="toast-close" aria-label="Fechar" onClick={() => onDismiss(t.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

ToastTray.propTypes = {
  toasts: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    type: PropTypes.string,
    message: PropTypes.string.isRequired,
  })).isRequired,
  onDismiss: PropTypes.func.isRequired,
};

export default ToastTray;

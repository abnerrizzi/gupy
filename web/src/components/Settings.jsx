import React from 'react';
import PropTypes from 'prop-types';

function Settings({ user, setUser, onLogout }) {
  return (
    <>
      <div className="page-head">
        <div>
          <h2>Configurações</h2>
          <p>Suas preferências são salvas localmente.</p>
        </div>
      </div>
      <div className="card card-pad" style={{ maxWidth: 600 }}>
        <div className="field">
          <label htmlFor="settings-name">Nome</label>
          <input
            id="settings-name"
            value={user.name}
            onChange={(e) => setUser({ name: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-email">Email</label>
          <input
            id="settings-email"
            type="email"
            value={user.email}
            onChange={(e) => setUser({ email: e.target.value })}
          />
        </div>
        <button type="button" className="btn btn-ghost" onClick={onLogout} style={{ marginTop: '0.5rem' }}>
          Sair
        </button>
      </div>
    </>
  );
}

Settings.propTypes = {
  user: PropTypes.shape({
    name: PropTypes.string,
    email: PropTypes.string,
  }).isRequired,
  setUser: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
};

export default Settings;

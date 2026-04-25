import React from 'react';
import PropTypes from 'prop-types';

function Settings({ user }) {
  return (
    <>
      <div className="page-head">
        <div>
          <h2>Configurações</h2>
          <p>Conta logada e preferências do dispositivo.</p>
        </div>
      </div>
      <div className="card card-pad" style={{ maxWidth: 600 }}>
        <div className="field">
          <label>Usuário</label>
          <input value={user?.username || ''} readOnly />
        </div>
        <div className="field">
          <label>Nome</label>
          <input value={user?.name || ''} readOnly />
        </div>
        <div className="field">
          <label>Sobrenome</label>
          <input value={user?.surname || ''} readOnly />
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--jh-fg-muted)', margin: '0.5rem 0 0' }}>
          Mais opções (alterar senha, edição de dados) em breve.
        </p>
      </div>
    </>
  );
}

Settings.propTypes = {
  user: PropTypes.shape({
    id: PropTypes.number,
    username: PropTypes.string,
    name: PropTypes.string,
    surname: PropTypes.string,
  }),
};

Settings.defaultProps = {
  user: null,
};

export default Settings;

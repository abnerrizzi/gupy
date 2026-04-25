import React, { useState } from 'react';
import PropTypes from 'prop-types';

function Login({ initialName, onEnter }) {
  const [name, setName] = useState(initialName || '');

  const submit = (e) => {
    e.preventDefault();
    onEnter({ name: name.trim() || 'Visitante' });
  };

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={submit}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1.5rem' }}>
          <img src="/logo-monogram.svg" style={{ width: 36, height: 36, borderRadius: 8 }} alt="" />
          <div style={{ fontWeight: 800, letterSpacing: '-0.025em', fontSize: '1.125rem' }}>
            JobHub<span style={{ color: 'var(--jh-primary)' }}>Mine</span>
          </div>
        </div>
        <h2>Entre para acompanhar suas vagas</h2>
        <p className="lede">Suas candidaturas ficam salvas neste dispositivo. Sem cadastro.</p>
        <div className="field">
          <label htmlFor="login-name">Como podemos te chamar?</label>
          <input
            id="login-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>
        <button type="submit" className="btn btn-primary btn-block">Começar</button>
        <p style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--jh-fg-subtle)', textAlign: 'center' }}>
          Nenhum dado é enviado para servidores.
        </p>
      </form>
    </div>
  );
}

Login.propTypes = {
  initialName: PropTypes.string,
  onEnter: PropTypes.func.isRequired,
};

Login.defaultProps = {
  initialName: '',
};

export default Login;

import React, { useState } from 'react';
import PropTypes from 'prop-types';

function Login({ onLogin, onRegister }) {
  const [mode, setMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isRegister = mode === 'register';

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isRegister) {
        await onRegister(username.trim(), password);
      } else {
        await onLogin(username.trim(), password);
      }
    } catch (err) {
      setError(err.message || 'Falha na operação');
    } finally {
      setSubmitting(false);
    }
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
        <h2>{isRegister ? 'Criar conta' : 'Entrar'}</h2>
        <p className="lede">
          {isRegister
            ? 'Crie uma conta para salvar suas vagas e acompanhar candidaturas.'
            : 'Acesse sua conta para ver suas vagas salvas e seu pipeline.'}
        </p>

        <div className="field">
          <label htmlFor="login-username">Usuário</label>
          <input
            id="login-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </div>
        <div className="field">
          <label htmlFor="login-password">Senha</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
            minLength={isRegister ? 8 : undefined}
          />
        </div>

        {error && (
          <div role="alert" style={{ marginBottom: '0.75rem', color: 'var(--jh-danger)', fontSize: '0.8125rem' }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={submitting}
        >
          {submitting ? '…' : (isRegister ? 'Criar conta' : 'Entrar')}
        </button>

        <p style={{ marginTop: '1rem', fontSize: '0.75rem', textAlign: 'center', color: 'var(--jh-fg-muted)' }}>
          {isRegister ? 'Já tem uma conta?' : 'Ainda não tem uma conta?'}{' '}
          <button
            type="button"
            className="link-btn"
            onClick={() => { setError(null); setMode(isRegister ? 'login' : 'register'); }}
          >
            {isRegister ? 'Entrar' : 'Criar conta'}
          </button>
        </p>
      </form>
    </div>
  );
}

Login.propTypes = {
  onLogin: PropTypes.func.isRequired,
  onRegister: PropTypes.func.isRequired,
};

export default Login;

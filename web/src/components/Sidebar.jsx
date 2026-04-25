import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';

function NavItem({ icon, label, count, active, onClick }) {
  return (
    <button type="button" className={'nav-item' + (active ? ' active' : '')} onClick={onClick}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            width: 18,
            display: 'inline-block',
            textAlign: 'center',
            color: active ? 'var(--jh-primary)' : 'var(--jh-fg-subtle)',
          }}
        >
          {icon}
        </span>
        {label}
      </span>
      {count != null && <span className="nav-count">{count}</span>}
    </button>
  );
}

NavItem.propTypes = {
  icon: PropTypes.node.isRequired,
  label: PropTypes.string.isRequired,
  count: PropTypes.number,
  active: PropTypes.bool,
  onClick: PropTypes.func.isRequired,
};

NavItem.defaultProps = {
  count: undefined,
  active: false,
};

function Sidebar({ page, setPage, counts, user, onLogout }) {
  const initial = (user.name?.trim()?.[0] || '?').toUpperCase();
  const [menuOpen, setMenuOpen] = useState(false);
  const footRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDocClick = (e) => {
      if (footRef.current && !footRef.current.contains(e.target)) setMenuOpen(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="/logo-monogram.svg" alt="" />
        <h1>JobHub<span>Mine</span></h1>
      </div>
      <NavItem icon="◫" label="Dashboard" active={page === 'dashboard'} onClick={() => setPage('dashboard')} />
      <NavItem icon="⌕" label="Buscar vagas" active={page === 'browse'} onClick={() => setPage('browse')} />
      <div className="nav-group-label">Minha jornada</div>
      <NavItem icon="♥" label="Salvas" count={counts.saved} active={page === 'saved'} onClick={() => setPage('saved')} />
      <NavItem icon="▦" label="Pipeline" count={counts.pipeline} active={page === 'pipeline'} onClick={() => setPage('pipeline')} />

      <div className="sidebar-foot" ref={footRef}>
        <button
          type="button"
          className={'sidebar-foot-user' + (menuOpen ? ' is-open' : '')}
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          onClick={() => setMenuOpen((v) => !v)}
        >
          <div className="avatar">{initial}</div>
          <div className="sidebar-foot-user-text">
            <div style={{ fontWeight: 600, color: 'var(--jh-fg)' }}>{user.name || 'Visitante'}</div>
            <div>{user.email || ''}</div>
          </div>
          <span className="sidebar-foot-caret" aria-hidden="true">{menuOpen ? '▾' : '▸'}</span>
        </button>
        {menuOpen && (
          <div className="sidebar-foot-actions" role="menu">
            <NavItem
              icon="⚙"
              label="Configurações"
              active={page === 'settings'}
              onClick={() => { setMenuOpen(false); setPage('settings'); }}
            />
            <NavItem
              icon="⏻"
              label="Sair"
              onClick={() => { setMenuOpen(false); onLogout(); }}
            />
          </div>
        )}
      </div>
    </aside>
  );
}

Sidebar.propTypes = {
  page: PropTypes.string.isRequired,
  setPage: PropTypes.func.isRequired,
  counts: PropTypes.shape({
    saved: PropTypes.number.isRequired,
    pipeline: PropTypes.number.isRequired,
  }).isRequired,
  user: PropTypes.shape({
    name: PropTypes.string,
    email: PropTypes.string,
  }).isRequired,
  onLogout: PropTypes.func.isRequired,
};

export default Sidebar;

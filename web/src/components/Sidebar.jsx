import React from 'react';
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

      <div className="sidebar-foot">
        <div className="sidebar-foot-user">
          <div className="avatar">{initial}</div>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--jh-fg)' }}>{user.name || 'Visitante'}</div>
            <div>{user.email || ''}</div>
          </div>
        </div>
        <div className="sidebar-foot-actions">
          <NavItem
            icon="⚙"
            label="Configurações"
            active={page === 'settings'}
            onClick={() => setPage('settings')}
          />
          <NavItem icon="⏻" label="Sair" onClick={onLogout} />
        </div>
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

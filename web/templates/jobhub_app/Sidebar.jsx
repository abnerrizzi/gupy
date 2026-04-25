// Sidebar.jsx — left nav with brand + page links + counts
const NavItem = ({ icon, label, count, active, onClick }) => (
  <div className={'nav-item' + (active ? ' active' : '')} onClick={onClick}>
    <span style={{display:'flex',alignItems:'center',gap:8}}>
      <span style={{width:18,display:'inline-block',textAlign:'center',color:active?'var(--jh-primary)':'var(--jh-fg-subtle)'}}>{icon}</span>
      {label}
    </span>
    {count != null && <span className="nav-count">{count}</span>}
  </div>
);

const Sidebar = ({ page, setPage, counts }) => (
  <aside className="sidebar">
    <div className="sidebar-brand">
      <img src="../../assets/logo-monogram.svg" alt="" />
      <h1>JobHub<span>Mine</span></h1>
    </div>
    <NavItem icon="◫" label="Dashboard" active={page==='dashboard'} onClick={() => setPage('dashboard')} />
    <NavItem icon="⌕" label="Buscar vagas" active={page==='browse'} onClick={() => setPage('browse')} />
    <div className="nav-group-label">Minha jornada</div>
    <NavItem icon="♥" label="Salvas" count={counts.saved} active={page==='saved'} onClick={() => setPage('saved')} />
    <NavItem icon="▦" label="Pipeline" count={counts.pipeline} active={page==='pipeline'} onClick={() => setPage('pipeline')} />
    <div className="nav-group-label">Conta</div>
    <NavItem icon="⚙" label="Configurações" active={page==='settings'} onClick={() => setPage('settings')} />
    <div className="sidebar-foot">
      <div className="avatar">M</div>
      <div><div style={{fontWeight:600,color:'var(--jh-fg)'}}>Maria Souza</div><div>maria@exemplo.com</div></div>
    </div>
  </aside>
);

window.Sidebar = Sidebar;

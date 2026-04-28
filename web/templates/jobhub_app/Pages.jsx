// Pages.jsx — Dashboard, Saved, Pipeline (Kanban), JobDetailWithTimeline, Settings, Login
const STAGE_META = {
  salva:    { label: 'Salva',     cls: 'stage-salva',    dot: '#94a3b8' },
  aplicada: { label: 'Aplicada',  cls: 'stage-aplicada', dot: '#2563eb' },
  entrev:   { label: 'Entrevista',cls: 'stage-entrev',   dot: '#d97706' },
  prop:     { label: 'Proposta',  cls: 'stage-prop',     dot: '#10b981' },
  encer:    { label: 'Encerrada', cls: 'stage-encer',    dot: '#ef4444' },
};
const STAGE_ORDER = ['salva','aplicada','entrev','prop','encer'];

// ---- Dashboard ----
const Dashboard = ({ jobs, onOpen }) => {
  const counts = STAGE_ORDER.reduce((a, k) => (a[k] = jobs.filter(j=>j.stage===k).length, a), {});
  const recent = jobs.slice(0, 5);
  return (
    <>
      <div className="page-head">
        <div><h2>Olá, Maria</h2><p>Acompanhe sua jornada de candidaturas.</p></div>
        <button className="btn btn-primary">+ Nova candidatura</button>
      </div>
      <div className="stat-grid">
        <div className="stat"><div className="stat-label">Salvas</div><div className="stat-value">{counts.salva}</div><div className="stat-delta">+2 esta semana</div></div>
        <div className="stat"><div className="stat-label">Aplicadas</div><div className="stat-value">{counts.aplicada}</div><div className="stat-delta">+3 esta semana</div></div>
        <div className="stat"><div className="stat-label">Em entrevista</div><div className="stat-value">{counts.entrev}</div><div className="stat-delta" style={{color:'var(--jh-fg-muted)'}}>1 amanhã</div></div>
        <div className="stat"><div className="stat-label">Propostas</div><div className="stat-value">{counts.prop}</div><div className="stat-delta">aguardando resposta</div></div>
      </div>
      <div className="dash-cols">
        <div className="card card-pad">
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'0.5rem'}}>
            <h4 style={{margin:0,fontSize:'0.875rem',fontWeight:700,letterSpacing:'-0.01em'}}>Atividade recente</h4>
            <a href="#" style={{fontSize:'0.75rem',fontWeight:600}}>Ver tudo →</a>
          </div>
          {recent.map(j => (
            <div className="list-row" key={j.id} onClick={() => onOpen(j)} style={{cursor:'pointer'}}>
              <div>
                <div className="title">{j.title}</div>
                <div className="meta">{j.company} · {j.location}</div>
              </div>
              <span className={'stage ' + STAGE_META[j.stage].cls}>{STAGE_META[j.stage].label}</span>
            </div>
          ))}
        </div>
        <div className="card card-pad">
          <h4 style={{margin:'0 0 0.75rem',fontSize:'0.875rem',fontWeight:700}}>Próximos eventos</h4>
          <div className="list-row"><div><div className="title">Entrevista técnica · Stone</div><div className="meta">Amanhã, 14:00</div></div></div>
          <div className="list-row"><div><div className="title">Devolutiva RH · iFood</div><div className="meta">Sexta, 10:30</div></div></div>
          <div className="empty" style={{padding:'1.25rem 0 0',fontSize:'0.75rem'}}>Sincronize seu calendário em Configurações.</div>
        </div>
      </div>
    </>
  );
};

// ---- Saved list ----
const SavedJobs = ({ jobs, onOpen, onApply, onRemove }) => {
  const saved = jobs.filter(j => j.stage === 'salva');
  return (
    <>
      <div className="page-head">
        <div><h2>Vagas salvas</h2><p>{saved.length} {saved.length===1?'vaga salva':'vagas salvas'} · armazenadas localmente neste dispositivo</p></div>
      </div>
      <div className="card">
        {saved.length === 0 ? (
          <div className="empty"><div className="big">Nenhuma vaga salva ainda.</div>Use o ♥ na busca para começar.</div>
        ) : saved.map(j => (
          <div className="saved-row" key={j.id}>
            <div onClick={() => onOpen(j)} style={{cursor:'pointer'}}>
              <div className="title">{j.title}</div>
              <div className="meta">
                <span>{j.company}</span>·<span>{j.location}</span>·<span className="tag" style={{background:'#dbeafe',color:'#1e40af',padding:'1px 8px'}}>{j.source.toUpperCase()}</span>
              </div>
            </div>
            <button className="btn btn-primary btn-sm" onClick={() => onApply(j)}>Marcar como aplicada</button>
            <button className="icon-btn" title="Remover" onClick={() => onRemove(j)}>×</button>
          </div>
        ))}
      </div>
    </>
  );
};

// ---- Pipeline (Kanban) ----
const Pipeline = ({ jobs, onOpen, onMove }) => {
  const byStage = STAGE_ORDER.reduce((a,k) => (a[k] = jobs.filter(j => j.stage === k), a), {});
  const onDrop = (e, stage) => { e.preventDefault(); const id = +e.dataTransfer.getData('id'); onMove(id, stage); };
  return (
    <>
      <div className="page-head">
        <div><h2>Pipeline</h2><p>Arraste cartões para mover entre estágios.</p></div>
        <button className="btn btn-ghost btn-sm">Exportar CSV</button>
      </div>
      <div className="kanban">
        {STAGE_ORDER.map(k => (
          <div className="kanban-col" key={k}
               onDragOver={(e)=>e.preventDefault()}
               onDrop={(e)=>onDrop(e,k)}>
            <div className="kanban-col-head">
              <div className="name"><span className="dot" style={{background:STAGE_META[k].dot}}></span>{STAGE_META[k].label}</div>
              <span className="count">{byStage[k].length}</span>
            </div>
            {byStage[k].map(j => (
              <div className="kanban-card" key={j.id} draggable
                   onDragStart={(e)=>e.dataTransfer.setData('id', j.id)}
                   onClick={() => onOpen(j)}>
                <div className="title">{j.title}</div>
                <div className="company">{j.company}</div>
                <div className="footer">
                  <span className="tag" style={{background:'#f1f5f9',color:'#475569'}}>{j.location.split(',')[1]?.trim() || j.location}</span>
                  <span className="ago">{j.ago}</span>
                </div>
              </div>
            ))}
            {byStage[k].length === 0 && <div className="empty" style={{padding:'1rem 0',fontSize:'0.75rem'}}>—</div>}
          </div>
        ))}
      </div>
    </>
  );
};

// ---- Job detail w/ timeline + notes (modal) ----
const JobDetailModal = ({ job, onClose, onAdvance, onNotes }) => {
  if (!job) return null;
  const events = job.events || [];
  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,0.7)',backdropFilter:'blur(4px)',display:'flex',alignItems:'center',justifyContent:'center',padding:'1.5rem',zIndex:100}} onClick={onClose}>
      <div style={{background:'#fff',borderRadius:'1rem',maxWidth:780,width:'100%',maxHeight:'90vh',overflow:'auto',boxShadow:'var(--jh-shadow-modal)'}} onClick={e=>e.stopPropagation()}>
        <div style={{padding:'2rem 2rem 1rem',borderBottom:'1px solid var(--jh-border)',display:'flex',justifyContent:'space-between',gap:'1rem',alignItems:'flex-start'}}>
          <div>
            <span className={'stage ' + STAGE_META[job.stage].cls}>{STAGE_META[job.stage].label}</span>
            <h2 style={{margin:'0.5rem 0 0.25rem',fontSize:'1.375rem',fontWeight:700,letterSpacing:'-0.025em'}}>{job.title}</h2>
            <div style={{color:'var(--jh-fg-muted)',fontSize:'0.875rem'}}>{job.company} · {job.location}</div>
          </div>
          <button className="icon-btn" onClick={onClose}>×</button>
        </div>
        <div style={{padding:'1.5rem 2rem 2rem'}} className="detail-grid">
          <div>
            <h4 style={{margin:'0 0 0.5rem',fontSize:'0.75rem',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.05em',color:'var(--jh-fg-strong)'}}>Descrição</h4>
            <p style={{margin:'0 0 1rem',fontSize:'0.875rem',color:'#334155',lineHeight:1.55}}>Procuramos profissional para integrar o time de plataforma. Trabalhará com sistemas distribuídos, contribuindo com arquitetura, código e mentoria.</p>
            <h4 style={{margin:'1rem 0 0.5rem',fontSize:'0.75rem',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.05em',color:'var(--jh-fg-strong)'}}>Minhas anotações</h4>
            <textarea className="notes" placeholder="Anote contatos, perguntas para entrevista, links..." defaultValue={job.notes || ''} onBlur={e => onNotes(job.id, e.target.value)} />
            <div style={{display:'flex',gap:'0.5rem',marginTop:'1rem'}}>
              <button className="btn btn-primary" onClick={() => onAdvance(job)}>Avançar estágio →</button>
              <a className="btn btn-ghost" href="#">Ver vaga original</a>
            </div>
          </div>
          <div>
            <h4 style={{margin:'0 0 0.5rem',fontSize:'0.75rem',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.05em',color:'var(--jh-fg-strong)'}}>Linha do tempo</h4>
            <div className="timeline">
              {events.map((e,i) => (
                <div key={i} className={'timeline-item' + (i === events.length-1 ? '' : ' muted')}>
                  <div className="when">{e.when}</div>
                  <div className="what">{e.what}</div>
                </div>
              ))}
              {events.length === 0 && <div style={{fontSize:'0.75rem',color:'var(--jh-fg-muted)',padding:'0.5rem 0'}}>Sem eventos ainda.</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ---- Settings ----
const Settings = () => (
  <>
    <div className="page-head"><div><h2>Configurações</h2><p>Suas preferências são salvas localmente.</p></div></div>
    <div className="card card-pad" style={{maxWidth:600}}>
      <div className="field"><label>Nome</label><input defaultValue="Maria Souza" /></div>
      <div className="field"><label>Email</label><input defaultValue="maria@exemplo.com" /></div>
      <div className="field"><label>Estágios padrão (separados por vírgula)</label><input defaultValue="Salva, Aplicada, Entrevista, Proposta, Encerrada" /></div>
      <button className="btn btn-primary" style={{marginTop:'0.5rem'}}>Salvar alterações</button>
    </div>
  </>
);

// ---- Login ----
const Login = ({ onEnter }) => (
  <div className="login-shell">
    <div className="login-card">
      <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:'1.5rem'}}>
        <img src="../../assets/logo-monogram.svg" style={{width:36,height:36,borderRadius:8}} alt="" />
        <div style={{fontWeight:800,letterSpacing:'-0.025em',fontSize:'1.125rem'}}>JobHub<span style={{color:'var(--jh-primary)'}}>Mine</span></div>
      </div>
      <h2>Entre para acompanhar suas vagas</h2>
      <p className="lede">Suas candidaturas ficam salvas neste dispositivo. Sem cadastro.</p>
      <div className="field"><label>Como podemos te chamar?</label><input defaultValue="Maria Souza" /></div>
      <button className="btn btn-primary btn-block" onClick={onEnter}>Começar</button>
      <p style={{marginTop:'1rem',fontSize:'0.75rem',color:'var(--jh-fg-subtle)',textAlign:'center'}}>Nenhum dado é enviado para servidores.</p>
    </div>
  </div>
);

window.STAGE_META = STAGE_META; window.STAGE_ORDER = STAGE_ORDER;
window.Dashboard = Dashboard; window.SavedJobs = SavedJobs; window.Pipeline = Pipeline;
window.JobDetailModal = JobDetailModal; window.Settings = Settings; window.Login = Login;

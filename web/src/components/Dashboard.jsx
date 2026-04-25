import React from 'react';
import PropTypes from 'prop-types';
import { STAGE_META, STAGE_ORDER } from '../constants/stages';

function Dashboard({ trackedJobs, user, onOpen, onGoBrowse }) {
  const counts = STAGE_ORDER.reduce((acc, k) => {
    acc[k] = trackedJobs.filter((j) => j.stage === k).length;
    return acc;
  }, {});
  const recent = trackedJobs.slice(-5).reverse();

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Olá, {user.name || 'Visitante'}</h2>
          <p>Acompanhe sua jornada de candidaturas.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={onGoBrowse}>+ Buscar vagas</button>
      </div>

      <div className="stat-grid">
        <div className="stat"><div className="stat-label">Salvas</div><div className="stat-value">{counts.salva}</div></div>
        <div className="stat"><div className="stat-label">Aplicadas</div><div className="stat-value">{counts.aplicada}</div></div>
        <div className="stat"><div className="stat-label">Em entrevista</div><div className="stat-value">{counts.entrev}</div></div>
        <div className="stat"><div className="stat-label">Propostas</div><div className="stat-value">{counts.prop}</div></div>
      </div>

      <div className="dash-cols">
        <div className="card card-pad">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 700, letterSpacing: '-0.01em' }}>Atividade recente</h4>
            <button type="button" className="link-btn" onClick={onGoBrowse}>Buscar mais →</button>
          </div>
          {recent.length === 0 ? (
            <div className="empty-shell" style={{ padding: '1.5rem 0' }}>
              <div className="big">Nada por aqui ainda.</div>
              Salve uma vaga em <strong>Buscar vagas</strong> para começar.
            </div>
          ) : recent.map((j) => (
            <button
              type="button"
              key={j.id}
              className="list-row"
              onClick={() => onOpen(j)}
              style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left' }}
            >
              <div>
                <div className="title">{j.title}</div>
                <div className="meta">{j.company} · {j.location}</div>
              </div>
              <span className={'stage ' + STAGE_META[j.stage].cls}>{STAGE_META[j.stage].label}</span>
            </button>
          ))}
        </div>
        <div className="card card-pad">
          <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', fontWeight: 700 }}>Resumo do pipeline</h4>
          {STAGE_ORDER.map((k) => (
            <div key={k} className="list-row">
              <div>
                <div className="title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: STAGE_META[k].dot }} />
                  {STAGE_META[k].label}
                </div>
              </div>
              <span style={{ fontWeight: 700, color: 'var(--jh-fg-muted)' }}>{counts[k]}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

Dashboard.propTypes = {
  trackedJobs: PropTypes.array.isRequired,
  user: PropTypes.shape({ name: PropTypes.string }).isRequired,
  onOpen: PropTypes.func.isRequired,
  onGoBrowse: PropTypes.func.isRequired,
};

export default Dashboard;

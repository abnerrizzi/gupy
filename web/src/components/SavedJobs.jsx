import React from 'react';
import PropTypes from 'prop-types';

function SavedJobs({ trackedJobs, onOpen, onApply, onRemove }) {
  const saved = trackedJobs.filter((j) => j.stage === 'salva');
  return (
    <>
      <div className="page-head">
        <div>
          <h2>Vagas salvas</h2>
          <p>{saved.length} {saved.length === 1 ? 'vaga salva' : 'vagas salvas'} · armazenadas localmente neste dispositivo</p>
        </div>
      </div>
      <div className="card">
        {saved.length === 0 ? (
          <div className="empty-shell">
            <div className="big">Nenhuma vaga salva ainda.</div>
            Use o ♥ na busca para começar.
          </div>
        ) : saved.map((j) => (
          <div className="saved-row" key={j.id}>
            <button
              type="button"
              onClick={() => onOpen(j)}
              style={{ background: 'none', border: 'none', textAlign: 'left', cursor: 'pointer', padding: 0, font: 'inherit', color: 'inherit' }}
            >
              <div className="title">{j.title}</div>
              <div className="meta">
                <span>{j.company}</span>·<span>{j.location}</span>·
                <span className="tag" style={{ background: '#dbeafe', color: '#1e40af', padding: '1px 8px' }}>
                  {(j.source || '').toUpperCase()}
                </span>
              </div>
            </button>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => onApply(j)}>
              Marcar como aplicada
            </button>
            <button type="button" className="icon-btn" title="Remover" aria-label="Remover" onClick={() => onRemove(j)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

SavedJobs.propTypes = {
  trackedJobs: PropTypes.array.isRequired,
  onOpen: PropTypes.func.isRequired,
  onApply: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
};

export default SavedJobs;

import React from 'react';
import PropTypes from 'prop-types';
import { STAGE_META, STAGE_NEXT } from '../constants/stages';
import useModalA11y from '../hooks/useModalA11y';

function TrackedJobModal({ job, onClose, onAdvance, onNotes, onOpenSearchDetail }) {
  const { closeBtnRef, dialogProps } = useModalA11y({
    isOpen: !!job,
    onClose,
    labelledBy: 'tracker-modal-title',
  });

  if (!job) return null;
  const events = job.events || [];
  const canAdvance = STAGE_NEXT[job.stage] && STAGE_NEXT[job.stage] !== job.stage;

  return (
    <div className="tracker-modal-overlay" onClick={onClose}>
      <div className="tracker-modal" onClick={(e) => e.stopPropagation()} {...dialogProps}>
        <div className="tracker-modal-head">
          <div>
            <span className={'stage ' + STAGE_META[job.stage].cls}>{STAGE_META[job.stage].label}</span>
            <h2 id="tracker-modal-title" className="tracker-modal-title">{job.title}</h2>
            <div className="tracker-modal-sub">{job.company} · {job.location}</div>
          </div>
          <button ref={closeBtnRef} type="button" className="icon-btn" aria-label="Fechar" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="tracker-modal-body detail-grid-tracker">
          <div>
            <h4 className="tracker-section-h">Minhas anotações</h4>
            <textarea
              className="notes"
              placeholder="Anote contatos, perguntas para entrevista, links..."
              defaultValue={job.notes || ''}
              onBlur={(e) => onNotes(job.id, e.target.value)}
            />
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
              {canAdvance && (
                <button type="button" className="btn btn-primary" onClick={() => onAdvance(job)}>
                  Avançar para {STAGE_META[STAGE_NEXT[job.stage]].label} →
                </button>
              )}
              <button type="button" className="btn btn-ghost" onClick={() => onOpenSearchDetail(job)}>
                Ver detalhes da vaga
              </button>
            </div>
          </div>
          <div>
            <h4 className="tracker-section-h">Linha do tempo</h4>
            <div className="timeline">
              {events.map((e, i) => (
                <div key={i} className={'timeline-item' + (i === events.length - 1 ? '' : ' muted')}>
                  <div className="when">{e.when}</div>
                  <div className="what">{e.what}</div>
                </div>
              ))}
              {events.length === 0 && (
                <div style={{ fontSize: '0.75rem', color: 'var(--jh-fg-muted)', padding: '0.5rem 0' }}>
                  Sem eventos ainda.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

TrackedJobModal.propTypes = {
  job: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    company: PropTypes.string,
    location: PropTypes.string,
    stage: PropTypes.string.isRequired,
    notes: PropTypes.string,
    events: PropTypes.array,
  }),
  onClose: PropTypes.func.isRequired,
  onAdvance: PropTypes.func.isRequired,
  onNotes: PropTypes.func.isRequired,
  onOpenSearchDetail: PropTypes.func.isRequired,
};

TrackedJobModal.defaultProps = {
  job: null,
};

export default TrackedJobModal;

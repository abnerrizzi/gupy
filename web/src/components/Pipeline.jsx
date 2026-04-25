import React from 'react';
import PropTypes from 'prop-types';
import { STAGE_META, STAGE_ORDER } from '../constants/stages';

function Pipeline({ trackedJobs, onOpen, onMove }) {
  const byStage = STAGE_ORDER.reduce((acc, k) => {
    acc[k] = trackedJobs.filter((j) => j.stage === k);
    return acc;
  }, {});

  const onDrop = (e, stage) => {
    e.preventDefault();
    const id = e.dataTransfer.getData('id');
    if (id) onMove(id, stage);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Pipeline</h2>
          <p>Arraste cartões ou use o seletor para mover entre estágios.</p>
        </div>
      </div>
      <div className="kanban">
        {STAGE_ORDER.map((k) => (
          <div
            className="kanban-col"
            key={k}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => onDrop(e, k)}
          >
            <div className="kanban-col-head">
              <div className="name">
                <span className="dot" style={{ background: STAGE_META[k].dot }} />
                {STAGE_META[k].label}
              </div>
              <span className="count">{byStage[k].length}</span>
            </div>
            {byStage[k].map((j) => (
              <div
                key={j.id}
                className="kanban-card"
                draggable
                onDragStart={(e) => e.dataTransfer.setData('id', j.id)}
                onClick={() => onOpen(j)}
              >
                <div className="title">{j.title}</div>
                <div className="company">{j.company}</div>
                <div className="footer">
                  <span className="tag" style={{ background: '#f1f5f9', color: '#475569' }}>
                    {j.location ? (j.location.split(',')[1]?.trim() || j.location) : ''}
                  </span>
                  <span className="ago">{j.ago || ''}</span>
                </div>
                <select
                  className="kanban-card-move"
                  aria-label={`Mover ${j.title} para outro estágio`}
                  value={j.stage}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => onMove(j.id, e.target.value)}
                >
                  {STAGE_ORDER.map((s) => (
                    <option key={s} value={s}>{STAGE_META[s].label}</option>
                  ))}
                </select>
              </div>
            ))}
            {byStage[k].length === 0 && (
              <div className="empty-shell" style={{ padding: '1rem 0', fontSize: '0.75rem' }}>—</div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

Pipeline.propTypes = {
  trackedJobs: PropTypes.array.isRequired,
  onOpen: PropTypes.func.isRequired,
  onMove: PropTypes.func.isRequired,
};

export default Pipeline;

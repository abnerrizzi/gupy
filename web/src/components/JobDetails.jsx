import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import DOMPurify from 'dompurify';
import JsonTree from './JsonTree';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';
import { extractCommonFacts, formatRelative } from '../utils/detailFields';

function pickRawJson(detail) {
  if (!detail) return null;
  if (detail.source === 'gupy') return detail.next_data || null;
  if (detail.source === 'inhire') return detail.raw_payload || null;
  return null;
}

function renderHtmlBlock(html) {
  if (!html) return null;
  return (
    <div
      className="detail-html"
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }}
    />
  );
}

function renderTextBlock(text) {
  if (!text) return null;
  return <div className="detail-text">{text}</div>;
}

function sourceBlocks(detail) {
  if (detail.source === 'gupy') {
    return [
      ['Descrição', renderHtmlBlock(detail.description_html)],
      ['Responsabilidades', renderHtmlBlock(detail.responsibilities_html)],
      ['Pré-requisitos', renderHtmlBlock(detail.prerequisites_html)],
    ];
  }
  if (detail.source === 'inhire') {
    return [
      ['Descrição', renderHtmlBlock(detail.description_html)],
      ['Sobre a empresa', renderHtmlBlock(detail.about_html)],
    ];
  }
  if (detail.source === 'linkedin') {
    return [['Descrição', renderTextBlock(detail.description)]];
  }
  return [];
}

function SourceDetail({ detail }) {
  if (!detail) return null;
  const facts = extractCommonFacts(detail);
  const blocks = sourceBlocks(detail).filter(([, body]) => body !== null);
  const rawJson = pickRawJson(detail);
  const syncedAgo = formatRelative(detail.fetched_at);

  return (
    <>
      {facts.length > 0 && (
        <div className="detail-grid">
          {facts.map(({ label, value }) => (
            <div key={label} className="info-item">
              <strong>{label}:</strong>
              <span>{value}</span>
            </div>
          ))}
        </div>
      )}
      {blocks.map(([label, body]) => (
        <section key={label} className="detail-section">
          <h4>{label}</h4>
          {body}
        </section>
      ))}
      {syncedAgo && (
        <p className="detail-meta">Sincronizado {syncedAgo}</p>
      )}
      {rawJson && (
        <details className="json-details">
          <summary>JSON completo da fonte</summary>
          <JsonTree raw={rawJson} />
        </details>
      )}
    </>
  );
}

SourceDetail.propTypes = {
  detail: PropTypes.object,
};

function JobDetails({ job, detail, loading, error, company, onSync, onClose }) {
  useEffect(() => {
    if (!job) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [job, onClose]);

  if (!job) return null;

  return (
    <div className="job-details-overlay" onClick={onClose}>
      <div className="job-details-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-button" onClick={onClose}>&times;</button>

        <div className="job-details-header">
          {company?.logo_url && (
            <img src={company.logo_url} alt={company.name} className="company-logo" />
          )}
          <div>
            <h2>{job.job_title}</h2>
            <h3>{job.company_name}</h3>
            {job.job_department && (
              <p className="job-department">{job.job_department}</p>
            )}
          </div>
        </div>

        <div className="job-details-body">
          <div className="info-grid">
            <div className="info-item">
              <strong>Localização:</strong>
              <span>
                {job.workplace_city && job.workplace_state
                  ? `${job.workplace_city}, ${job.workplace_state}`
                  : job.workplace_city || job.workplace_state || 'N/A'}
              </span>
            </div>
            <div className="info-item">
              <strong>Tipo de Vaga:</strong>
              <span>{formatJobType(job.job_type)}</span>
            </div>
            <div className="info-item">
              <strong>Modalidade:</strong>
              <span>{formatWorkplaceType(job.workplace_type)}</span>
            </div>
            <div className="info-item">
              <strong>Fonte:</strong>
              <span>{(job.source || 'gupy').toUpperCase()}</span>
            </div>
          </div>

          {job.job_url && (
            <div className="job-action">
              <a
                href={job.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="apply-button"
              >
                Ver vaga no site original
              </a>
            </div>
          )}

          <div className="detail-section-wrapper">
            {error && <p className="detail-error">{error}</p>}
            {loading && <p className="detail-loading">Carregando detalhe...</p>}
            {!loading && !detail && (
              <button
                type="button"
                className="sync-button"
                onClick={onSync}
              >
                Sincronizar detalhe
              </button>
            )}
            {!loading && detail && <SourceDetail detail={detail} />}
          </div>
        </div>
      </div>
    </div>
  );
}

JobDetails.propTypes = {
  job: PropTypes.shape({
    job_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    job_title: PropTypes.string.isRequired,
    job_url: PropTypes.string,
    company_name: PropTypes.string,
    company_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    workplace_city: PropTypes.string,
    workplace_state: PropTypes.string,
    job_department: PropTypes.string,
    workplace_type: PropTypes.string,
    job_type: PropTypes.string,
    source: PropTypes.string,
  }),
  detail: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  company: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    logo_url: PropTypes.string,
  }),
  onSync: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default JobDetails;

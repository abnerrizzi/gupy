import React from 'react';
import PropTypes from 'prop-types';
import DOMPurify from 'dompurify';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

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

function SourceDetail({ detail }) {
  if (!detail) return null;
  const fields = [];
  const blocks = [];

  if (detail.source === 'gupy') {
    if (detail.published_at) fields.push(['Publicado em', detail.published_at]);
    if (detail.country) fields.push(['País', detail.country]);
    blocks.push(['Descrição', renderHtmlBlock(detail.description_html)]);
    blocks.push(['Responsabilidades', renderHtmlBlock(detail.responsibilities_html)]);
    blocks.push(['Pré-requisitos', renderHtmlBlock(detail.prerequisites_html)]);
  } else if (detail.source === 'inhire') {
    if (detail.contract_type) fields.push(['Contrato', detail.contract_type]);
    if (detail.location) fields.push(['Localização', detail.location]);
    if (detail.location_complement) fields.push(['Complemento', detail.location_complement]);
    if (detail.published_at) fields.push(['Publicado em', detail.published_at]);
    blocks.push(['Descrição', renderHtmlBlock(detail.description_html)]);
    blocks.push(['Sobre a empresa', renderHtmlBlock(detail.about_html)]);
  } else if (detail.source === 'linkedin') {
    if (detail.seniority) fields.push(['Nível', detail.seniority]);
    if (detail.employment_type) fields.push(['Tipo', detail.employment_type]);
    blocks.push(['Descrição', renderTextBlock(detail.description)]);
  }

  return (
    <>
      {fields.length > 0 && (
        <div className="detail-grid">
          {fields.map(([label, value]) => (
            <div key={label} className="info-item">
              <strong>{label}:</strong>
              <span>{value}</span>
            </div>
          ))}
        </div>
      )}
      {blocks.filter(([, body]) => body !== null).map(([label, body]) => (
        <section key={label} className="detail-section">
          <h4>{label}</h4>
          {body}
        </section>
      ))}
      {detail.fetched_at && (
        <p className="detail-meta">Sincronizado em {detail.fetched_at}</p>
      )}
    </>
  );
}

SourceDetail.propTypes = {
  detail: PropTypes.object,
};

function JobDetails({ job, detail, loading, error, company, onSync, onClose }) {
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

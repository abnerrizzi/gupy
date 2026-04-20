import React, { useEffect, useRef } from 'react';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobDetails({ job, company, onClose }) {
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    
    // Focus management
    const previousFocus = document.activeElement;
    closeButtonRef.current?.focus();

    return () => {
      window.removeEventListener('keydown', handleEscape);
      previousFocus?.focus();
    };
  }, [onClose]);

  if (!job) return null;

  return (
    <div 
      className="JobDetails-overlay" 
      onClick={onClose}
      role="presentation"
    >
      <div 
        className="JobDetails" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="job-details-title"
        ref={modalRef}
      >
        <button 
          className="JobDetails-close" 
          onClick={onClose}
          aria-label="Fechar detalhes"
          ref={closeButtonRef}
        >
          &times;
        </button>

        {company?.logo_url && (
          <div className="JobDetails-logo">
            <img src={company.logo_url} alt={`Logo da ${company.name || job.company_name}`} />
          </div>
        )}

        <h2 id="job-details-title">{job.job_title}</h2>

        <div className="JobDetails-info">
          <div>
            <label>Empresa:</label>
            {company?.name || job.company_name || job.company_id}
          </div>
          <div>
            <label>Local:</label>
            {job.workplace_city}, {job.workplace_state}
          </div>
          <div>
            <label>Departamento:</label>
            {job.job_department}
          </div>
          <div>
            <label>Tipo de trabalho:</label>
            {formatWorkplaceType(job.workplace_type)}
          </div>
          <div>
            <label>Tipo de vaga:</label>
            {formatJobType(job.job_type)}
          </div>
          <div>
            <label>Fonte:</label>
            <strong>{job.source?.toUpperCase() || 'N/A'}</strong>
          </div>
        </div>

        <a
          className="JobDetails-apply"
          href={job.job_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Candidatar-se na {job.source === 'gupy' ? 'Gupy' : 'Inhire'}
        </a>
      </div>
    </div>
  );
}

export default JobDetails;
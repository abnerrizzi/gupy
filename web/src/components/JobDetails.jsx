import React from 'react';
import PropTypes from 'prop-types';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobDetails({ job, company, onClose }) {
  if (!job) return null;

  return (
    <div className="job-details-overlay">
      <div className="job-details-modal">
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
              <strong>Departamento:</strong>
              <span>{job.job_department || 'N/A'}</span>
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
              <span>{job.source || 'Gupy'}</span>
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
  company: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    logo_url: PropTypes.string,
  }),
  onClose: PropTypes.func.isRequired,
};

export default JobDetails;

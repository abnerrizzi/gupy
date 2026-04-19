import React from 'react';

function JobDetails({ job, company, onClose }) {
  if (!job) return null;

  const formatWorkplaceType = (type) => {
    if (!type) return 'N/A';
    switch (type.toLowerCase()) {
      case 'on-site':
      case 'presencial':
        return 'Presencial';
      case 'remote':
      case 'remoto':
      case 'home office':
        return 'Remoto';
      case 'hybrid':
      case 'híbrido':
        return 'Híbrido';
      default:
        return type;
    }
  };

  const formatJobType = (type) => {
    if (!type) return 'N/A';
    switch (type.toLowerCase()) {
      case 'vacancy_type_effective':
      case 'efetivo':
      case 'full-time':
        return 'Efetiva';
      case 'vacancy_type_talent_pool':
      case 'banco de talentos':
        return 'Banco de Talentos';
      case 'estágio':
      case 'internship':
        return 'Estágio';
      default:
        return type;
    }
  };

  return (
    <div className="JobDetails-overlay" onClick={onClose}>
      <div className="JobDetails" onClick={(e) => e.stopPropagation()}>
        <button className="JobDetails-close" onClick={onClose}>
          &times;
        </button>

        {company?.logo_url && (
          <div className="JobDetails-logo">
            <img src={company.logo_url} alt={company.name} />
          </div>
        )}

        <h2>{job.job_title}</h2>

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
            <strong>{job.source?.toUpperCase()}</strong>
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
import React from 'react';

function JobDetails({ job, company, onClose }) {
  if (!job) return null;

  const formatWorkplaceType = (type) => {
    switch (type) {
      case 'on-site':
        return 'Presencial';
      case 'remote':
        return 'Remoto';
      case 'hybrid':
        return 'Híbrido';
      default:
        return type;
    }
  };

  const formatJobType = (type) => {
    switch (type) {
      case 'vacancy_type_effective':
        return 'Efetiva';
      case 'vacancy_type_talent_pool':
        return 'Banco de Talentos';
      default:
        return type;
    }
  };

  const getJobUrl = () => {
    if (!company || !company.career_page_url) return '#';
    const url = new URL(company.career_page_url);
    const baseUrl = `${url.protocol}//${url.host}`;
    return `${baseUrl}/jobs/${job.id}`;
  };

  return (
    <div className="JobDetails-overlay" onClick={onClose}>
      <div className="JobDetails" onClick={(e) => e.stopPropagation()}>
        <button className="JobDetails-close" onClick={onClose}>
          &times;
        </button>

        <h2>{job.title}</h2>

        <div className="JobDetails-info">
          <div>
            <label>Empresa:</label>
            {company?.name || job.company_id}
          </div>
          <div>
            <label>Local:</label>
            {job.workplace_city}, {job.workplace_state}
          </div>
          <div>
            <label>Departamento:</label>
            {job.department}
          </div>
          <div>
            <label>Tipo de trabalho:</label>
            {formatWorkplaceType(job.workplace_type)}
          </div>
          <div>
            <label>Tipo de vaga:</label>
            {formatJobType(job.type)}
          </div>
        </div>

        <a
          className="JobDetails-apply"
          href={getJobUrl()}
          target="_blank"
          rel="noopener noreferrer"
        >
          Candidatar-se
        </a>
      </div>
    </div>
  );
}

export default JobDetails;
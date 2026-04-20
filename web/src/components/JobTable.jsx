import React from 'react';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobTable({ jobs, companies, loading, page, totalPages, onJobClick, onPageChange }) {
  const getCompanyName = (companyId) => {
    const company = companies.find(c => c.id === companyId);
    return company ? company.name : companyId;
  };

  const handleKeyDown = (e, job) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onJobClick(job);
    }
  };

  return (
    <div className="JobTable">
      <table>
        <thead>
          <tr>
            <th>Vaga</th>
            <th>Empresa</th>
            <th>Local</th>
            <th>Departamento</th>
            <th>Tipo</th>
            <th>Fonte</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan="6" className="loading">Carregando...</td>
            </tr>
          ) : jobs.length === 0 ? (
            <tr>
              <td colSpan="6" className="loading">Nenhuma vaga encontrada</td>
            </tr>
          ) : (
            jobs.map((job) => (
              <tr 
                key={job.job_id} 
                onClick={() => onJobClick(job)}
                onKeyDown={(e) => handleKeyDown(e, job)}
                role="button"
                tabIndex="0"
                aria-label={`Ver detalhes da vaga ${job.job_title}`}
              >
                <td>
                  <a href={job.job_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                    {job.job_title}
                  </a>
                </td>
                <td>{job.company_name || getCompanyName(job.company_id)}</td>
                <td>
                  {job.workplace_city}, {job.workplace_state}
                </td>
                <td>{job.job_department}</td>
                <td>
                  <span className={`type-${job.workplace_type}`}>
                    {formatWorkplaceType(job.workplace_type)}
                  </span>
                  {' / '}
                  <span className={`type-${job.job_type}`}>
                    {formatJobType(job.job_type)}
                  </span>
                </td>
                <td>
                  <span className={`source-badge source-${job.source}`}>
                    {job.source?.toUpperCase() || 'N/A'}
                  </span>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            disabled={page === 0}
            onClick={() => onPageChange(page - 1)}
            aria-label="Página anterior"
          >
            Anterior
          </button>
          <span>
            Página {page + 1} de {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => onPageChange(page + 1)}
            aria-label="Próxima página"
          >
           Próxima
          </button>
        </div>
      )}
    </div>
  );
}

export default JobTable;
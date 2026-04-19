import React from 'react';

function JobTable({ jobs, companies, loading, page, totalPages, onJobClick, onPageChange }) {
  const getCompanyName = (companyId) => {
    const company = companies.find(c => c.id === companyId);
    return company ? company.name : companyId;
  };

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
    <div className="JobTable">
      <table>
        <thead>
          <tr>
            <th>Vaga</th>
            <th>Empresa</th>
            <th>Local</th>
            <th>Departamento</th>
            <th>Tipo / Fonte</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan="5" className="loading">Carregando...</td>
            </tr>
          ) : jobs.length === 0 ? (
            <tr>
              <td colSpan="5" className="loading">Nenhuma vaga encontrada</td>
            </tr>
          ) : (
            jobs.map((job) => (
              <tr key={job.job_id} onClick={() => onJobClick(job)}>
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
                  <div>
                    <span className={`type-${job.workplace_type}`}>
                      {formatWorkplaceType(job.workplace_type)}
                    </span>
                    {' / '}
                    <span className={`type-${job.job_type}`}>
                      {formatJobType(job.job_type)}
                    </span>
                  </div>
                  <div className="job-source">
                    <small>Fonte: <strong>{job.source}</strong></small>
                  </div>
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
          >
            Anterior
          </button>
          <span>
            Página {page + 1} de {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => onPageChange(page + 1)}
          >
           Próxima
          </button>
        </div>
      )}
    </div>
  );
}

export default JobTable;
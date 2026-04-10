import React from 'react';

function JobTable({ jobs, companies, loading, page, totalPages, onJobClick, onPageChange }) {
  const getCompanyName = (companyId) => {
    const company = companies.find(c => c.id === companyId);
    return company ? company.name : companyId;
  };

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
              <tr key={job.id} onClick={() => onJobClick(job)}>
                <td>{job.title}</td>
                <td>{getCompanyName(job.company_id)}</td>
                <td>
                  {job.workplace_city}, {job.workplace_state}
                </td>
                <td>{job.department}</td>
                <td>
                  <span className={`type-${job.workplace_type}`}>
                    {formatWorkplaceType(job.workplace_type)}
                  </span>
                  {' / '}
                  <span className={`type-${job.type}`}>
                    {formatJobType(job.type)}
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
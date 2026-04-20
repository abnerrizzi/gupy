import React from 'react';
import PropTypes from 'prop-types';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobTable({ jobs, companies, loading, page, totalPages, onJobClick, onPageChange }) {
  if (loading && jobs.length === 0) {
    return <div className="loading">Carregando vagas...</div>;
  }

  if (!loading && jobs.length === 0) {
    return <div className="no-jobs">Nenhuma vaga encontrada para os filtros selecionados.</div>;
  }

  return (
    <div className="job-table-container">
      <table className="job-table">
        <thead>
          <tr>
            <th>Título</th>
            <th>Empresa</th>
            <th>Localização</th>
            <th>Tipo</th>
            <th>Modalidade</th>
            <th>Fonte</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.job_id} onClick={() => onJobClick(job)} className="job-row">
              <td>{job.job_title}</td>
              <td>{job.company_name}</td>
              <td>
                {job.workplace_city && job.workplace_state
                  ? `${job.workplace_city}, ${job.workplace_state}`
                  : job.workplace_city || job.workplace_state || 'N/A'}
              </td>
              <td>{formatJobType(job.job_type)}</td>
              <td>{formatWorkplaceType(job.workplace_type)}</td>
              <td>
                <span className={`tag tag-source-${(job.source || 'gupy').toLowerCase()}`}>
                  {(job.source || 'Gupy').toUpperCase()}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </button>
        <span>Página {page + 1} de {totalPages || 1}</span>
        <button
          disabled={page >= totalPages - 1}
          onClick={() => onPageChange(page + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}

JobTable.propTypes = {
  jobs: PropTypes.arrayOf(PropTypes.shape({
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
  })).isRequired,
  companies: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
  })).isRequired,
  loading: PropTypes.bool.isRequired,
  page: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  onJobClick: PropTypes.func.isRequired,
  onPageChange: PropTypes.func.isRequired,
};

export default JobTable;

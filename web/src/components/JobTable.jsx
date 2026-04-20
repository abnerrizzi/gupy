import React from 'react';
import PropTypes from 'prop-types';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobTable({ jobs, companies, loading, page, totalPages, sortKey, sortOrder, onJobClick, onPageChange, onSort }) {
  if (loading && jobs.length === 0) {
    return <div className="loading">Carregando vagas...</div>;
  }

  const renderSortIcon = (key) => {
    if (sortKey !== key) return null;
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div className="job-table-container">
      <table className="job-table">
        <thead>
          <tr>
            <th onClick={() => onSort('job_title')} style={{ cursor: 'pointer' }}>
              Título{renderSortIcon('job_title')}
            </th>
            <th onClick={() => onSort('company_name')} style={{ cursor: 'pointer' }}>
              Empresa{renderSortIcon('company_name')}
            </th>
            <th onClick={() => onSort('workplace_city')} style={{ cursor: 'pointer' }}>
              Localização{renderSortIcon('workplace_city')}
            </th>
            <th onClick={() => onSort('job_type')} style={{ cursor: 'pointer' }}>
              Tipo{renderSortIcon('job_type')}
            </th>
            <th onClick={() => onSort('workplace_type')} style={{ cursor: 'pointer' }}>
              Modalidade{renderSortIcon('workplace_type')}
            </th>
            <th onClick={() => onSort('source')} style={{ cursor: 'pointer' }}>
              Fonte{renderSortIcon('source')}
            </th>
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
              <td>
                <span className={`tag tag-workplace-${(job.workplace_type || 'na').toLowerCase().replace('-', '')}`}>
                  {formatWorkplaceType(job.workplace_type)}
                </span>
              </td>
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
  sortKey: PropTypes.string.isRequired,
  sortOrder: PropTypes.string.isRequired,
  onJobClick: PropTypes.func.isRequired,
  onPageChange: PropTypes.func.isRequired,
  onSort: PropTypes.func.isRequired,
};

export default JobTable;

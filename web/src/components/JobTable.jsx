import React from 'react';
import PropTypes from 'prop-types';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobTable({ jobs, companies, loading, page, totalPages, onJobClick, onPageChange }) {
...
  return (
...
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
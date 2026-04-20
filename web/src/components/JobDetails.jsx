import React, { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function JobDetails({ job, company, onClose }) {
...
  return (
...
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
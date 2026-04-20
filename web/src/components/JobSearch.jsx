import React from 'react';
import PropTypes from 'prop-types';

function JobSearch({ value, onChange }) {
  return (
    <div className="JobSearch">
      <input
        type="text"
        placeholder="Buscar vagas por título..."
        aria-label="Buscar vagas por título"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

JobSearch.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
};

export default JobSearch;
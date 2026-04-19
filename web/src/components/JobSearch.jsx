import React from 'react';

function JobSearch({ value, onChange }) {
  return (
    <div className="JobSearch">
      <input
        type="text"
        placeholder="Buscar vagas por título..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export default JobSearch;
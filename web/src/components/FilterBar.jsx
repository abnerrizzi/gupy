import React from 'react';
import PropTypes from 'prop-types';
import { formatWorkplaceType, formatJobType } from '../utils/formatters';

function FilterBar({ companies, filters, selected, onChange, onReset, onApply }) {
  const handleChange = (key) => (e) => {
    onChange(key, e.target.value);
  };

  return (
    <div className="FilterBar">
      <select
        className="filter-select filter-select-wide"
        value={selected.companyId}
        onChange={handleChange('companyId')}
        aria-label="Filtrar por empresa"
      >
        <option value="">Todas as empresas</option>
        {companies.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={selected.city}
        onChange={handleChange('city')}
        aria-label="Filtrar por cidade"
      >
        <option value="">Todas as cidades</option>
        {filters.cities?.map((city) => (
          <option key={city} value={city}>
            {city}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={selected.state}
        onChange={handleChange('state')}
        aria-label="Filtrar por estado"
      >
        <option value="">Todos os estados</option>
        {filters.states?.map((state) => (
          <option key={state} value={state}>
            {state}
          </option>
        ))}
      </select>

      <select
        className="filter-select filter-select-wide"
        value={selected.department}
        onChange={handleChange('department')}
        aria-label="Filtrar por departamento"
      >
        <option value="">Todos os departamentos</option>
        {filters.departments?.map((dept) => (
          <option key={dept} value={dept}>
            {dept}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={selected.workplaceType}
        onChange={handleChange('workplaceType')}
        aria-label="Filtrar por tipo de ambiente"
      >
        <option value="">Todos os tipos</option>
        {Array.from(new Set(filters.workplace_types?.map(formatWorkplaceType)))
          .filter(Boolean)
          .sort()
          .map((label) => (
            <option key={label} value={label}>
              {label}
            </option>
          ))}
      </select>

      <select
        className="filter-select"
        value={selected.jobType}
        onChange={handleChange('jobType')}
        aria-label="Filtrar por tipo de vaga"
      >
        <option value="">Todas as vagas</option>
        {Array.from(new Set(filters.job_types?.map(formatJobType)))
          .filter(Boolean)
          .sort()
          .map((label) => (
            <option key={label} value={label}>
              {label}
            </option>
          ))}
      </select>

      <select
        className="filter-select"
        value={selected.source}
        onChange={handleChange('source')}
        aria-label="Filtrar por fonte"
      >
        <option value="">Todas as fontes</option>
        {filters.sources?.map((source) => (
          <option key={source} value={source}>
            {source.toUpperCase()}
          </option>
        ))}
      </select>

      <button className="filter-apply-button" onClick={onApply} aria-label="Aplicar filtros / atualizar">
        Aplicar
      </button>

      <button className="reset-button" onClick={onReset}>
        Limpar Filtros
      </button>
    </div>
  );
}

FilterBar.propTypes = {
  companies: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
  })).isRequired,
  filters: PropTypes.shape({
    cities: PropTypes.arrayOf(PropTypes.string),
    states: PropTypes.arrayOf(PropTypes.string),
    departments: PropTypes.arrayOf(PropTypes.string),
    workplace_types: PropTypes.arrayOf(PropTypes.string),
    job_types: PropTypes.arrayOf(PropTypes.string),
    sources: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  selected: PropTypes.shape({
    companyId: PropTypes.string,
    city: PropTypes.string,
    state: PropTypes.string,
    department: PropTypes.string,
    workplaceType: PropTypes.string,
    jobType: PropTypes.string,
    source: PropTypes.string,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  onReset: PropTypes.func.isRequired,
  onApply: PropTypes.func.isRequired,
};

export default FilterBar;

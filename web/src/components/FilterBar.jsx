import React from 'react';

function FilterBar({ companies, filters, selected, onChange, onReset }) {
  const handleChange = (key) => (e) => {
    onChange(key, e.target.value);
  };

  return (
    <div className="FilterBar">
      <select value={selected.companyId} onChange={handleChange('companyId')}>
        <option value="">Todas as empresas</option>
        {companies.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>

      <select value={selected.city} onChange={handleChange('city')}>
        <option value="">Todas as cidades</option>
        {filters.cities.map((city) => (
          <option key={city} value={city}>
            {city}
          </option>
        ))}
      </select>

      <select value={selected.state} onChange={handleChange('state')}>
        <option value="">Todos os estados</option>
        {filters.states.map((state) => (
          <option key={state} value={state}>
            {state}
          </option>
        ))}
      </select>

      <select value={selected.department} onChange={handleChange('department')}>
        <option value="">Todos os departamentos</option>
        {filters.departments.map((dept) => (
          <option key={dept} value={dept}>
            {dept}
          </option>
        ))}
      </select>

      <select value={selected.workplaceType} onChange={handleChange('workplaceType')}>
        <option value="">Todos os tipos</option>
        {filters.workplace_types.map((type) => (
          <option key={type} value={type}>
            {type === 'on-site' ? 'Presencial' : type === 'remote' ? 'Remoto' : type === 'hybrid' ? 'Híbrido' : type}
          </option>
        ))}
      </select>

      <select value={selected.jobType} onChange={handleChange('jobType')}>
        <option value="">Todas as vagas</option>
        {filters.job_types.map((type) => (
          <option key={type} value={type}>
            {type === 'vacancy_type_effective' ? 'Efetiva' : type === 'vacancy_type_talent_pool' ? 'Banco de Talentos' : type}
          </option>
        ))}
      </select>

      <select value={selected.source} onChange={handleChange('source')}>
        <option value="">Todas as fontes</option>
        {filters.sources && filters.sources.map((source) => (
          <option key={source} value={source}>
            {source.toUpperCase()}
          </option>
        ))}
      </select>

      <button className="reset-button" onClick={onReset}>
        Limpar Filtros
      </button>
    </div>
  );
}

export default FilterBar;
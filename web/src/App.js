import React, { useState, useEffect } from 'react';
import JobSearch from './components/JobSearch';
import FilterBar from './components/FilterBar';
import JobTable from './components/JobTable';
import JobDetails from './components/JobDetails';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const PAGE_SIZE = 100;

function App() {
  const [jobs, setJobs] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [filters, setFilters] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);

  const [search, setSearch] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [department, setDepartment] = useState('');
  const [workplaceType, setWorkplaceType] = useState('');
  const [jobType, setJobType] = useState('');
  const [source, setSource] = useState('');

  useEffect(() => {
    fetchFilters();
    fetchCompanies();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(search);
    }, 200);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    fetchJobs();
  }, [searchDebounced, companyId, city, state, department, workplaceType, jobType, source, page]);

  const fetchFilters = async () => {
    try {
      const res = await fetch(`${API_URL}/filters`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setFilters(data);
    } catch (err) {
      console.error('Failed to fetch filters:', err);
      setError('Falha ao carregar filtros. Verifique se a API está online.');
    }
  };

  const fetchCompanies = async () => {
    try {
      const res = await fetch(`${API_URL}/companies`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setCompanies(data.companies);
    } catch (err) {
      console.error('Failed to fetch companies:', err);
      setError('Falha ao carregar lista de empresas.');
    }
  };

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchDebounced) params.append('search', searchDebounced);
      if (companyId) params.append('company_id', companyId);
      if (city) params.append('city', city);
      if (state) params.append('state', state);
      if (department) params.append('department', department);
      if (workplaceType) params.append('workplace_type', workplaceType);
      if (jobType) params.append('type', jobType);
      if (source) params.append('source', source);
      params.append('offset', page * PAGE_SIZE);
      params.append('limit', PAGE_SIZE);

      const res = await fetch(`${API_URL}/jobs?${params}`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setJobs(data.jobs);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
      setError('Erro ao buscar vagas. Tente novamente mais tarde.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value) => {
    setSearch(value);
    setPage(0);
  };

  const handleFilterChange = (key, value) => {
    switch (key) {
      case 'companyId':
        setCompanyId(value);
        break;
      case 'city':
        setCity(value);
        break;
      case 'state':
        setState(value);
        break;
      case 'department':
        setDepartment(value);
        break;
      case 'workplaceType':
        setWorkplaceType(value);
        break;
      case 'jobType':
        setJobType(value);
        break;
      case 'source':
        setSource(value);
        break;
      default:
        break;
    }
    setPage(0);
  };

  const handleResetFilters = () => {
    setSearch('');
    setCompanyId('');
    setCity('');
    setState('');
    setDepartment('');
    setWorkplaceType('');
    setJobType('');
    setSource('');
    setPage(0);
  };

  const handleJobClick = (job) => {
    setSelectedJob(job);
  };

  const handleCloseDetails = () => {
    setSelectedJob(null);
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Job Search</h1>
        <p>{total} vagas encontradas</p>
      </header>

      <main className="App-main">
        {error && (
          <div className="App-error">
            {error}
            <button onClick={() => { setError(null); fetchFilters(); fetchCompanies(); fetchJobs(); }}>
              Tentar novamente
            </button>
          </div>
        )}

        <JobSearch value={search} onChange={handleSearch} />

        {filters && (
          <FilterBar
            companies={companies}
            filters={filters}
            selected={{
              companyId,
              city,
              state,
              department,
              workplaceType,
              jobType,
              source
            }}
            onChange={handleFilterChange}
            onReset={handleResetFilters}
          />
        )}

        <JobTable
          jobs={jobs}
          companies={companies}
          loading={loading}
          page={page}
          totalPages={totalPages}
          onJobClick={handleJobClick}
          onPageChange={handlePageChange}
        />

        {selectedJob && (
          <JobDetails
            job={selectedJob}
            company={companies.find(c => c.id === selectedJob.company_id)}
            onClose={handleCloseDetails}
          />
        )}
      </main>
    </div>
  );
}

export default App;
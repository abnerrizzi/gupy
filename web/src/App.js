import React, { useCallback, useEffect, useRef, useState } from 'react';
import JobSearch from './components/JobSearch';
import FilterBar from './components/FilterBar';
import JobTable from './components/JobTable';
import JobDetails from './components/JobDetails';
import Sidebar from './components/Sidebar';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import SavedJobs from './components/SavedJobs';
import Pipeline from './components/Pipeline';
import Settings from './components/Settings';
import TrackedJobModal from './components/TrackedJobModal';
import WordCloud from './components/WordCloud';
import ToastTray from './components/ToastTray';
import useTrackedJobs from './hooks/useTrackedJobs';
import useUser from './hooks/useUser';
import useAuth from './hooks/useAuth';
import useToasts from './hooks/useToasts';
import useTheme from './hooks/useTheme';
import { STAGE_NEXT } from './constants/stages';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const PAGE_SIZE = 100;

function jobRowToTracked(job) {
  return {
    id: String(job.job_id),
    title: job.job_title,
    company: job.company_name || '',
    company_id: job.company_id,
    location: [job.workplace_city, job.workplace_state].filter(Boolean).join(', '),
    source: job.source || '',
    ago: 'agora',
    job_url: job.job_url,
    workplace_city: job.workplace_city,
    workplace_state: job.workplace_state,
    workplace_type: job.workplace_type,
    job_type: job.job_type,
    job_department: job.job_department,
  };
}

function trackedToSelectedJob(t) {
  return {
    job_id: t.id,
    job_title: t.title,
    company_name: t.company,
    company_id: t.company_id,
    source: t.source,
    job_url: t.job_url,
    workplace_city: t.workplace_city,
    workplace_state: t.workplace_state,
    workplace_type: t.workplace_type,
    job_type: t.job_type,
    job_department: t.job_department,
  };
}

function App() {
  const auth = useAuth();
  const { user, setUser } = useUser();
  const { theme, toggle: toggleTheme } = useTheme();
  const { toasts: toastList, push: pushToast, dismiss: dismissToast } = useToasts();
  const pushError = useCallback((message) => pushToast({ type: 'error', message }), [pushToast]);
  const { trackedJobs, addJob, updateStage, updateNotes, removeJob, isTracked } =
    useTrackedJobs(auth.status, pushError);

  useEffect(() => {
    if (auth.user) {
      const displayName = [auth.user.name, auth.user.surname].filter(Boolean).join(' ')
        || auth.user.username;
      setUser({ name: displayName, email: '' });
    }
  }, [auth.user, setUser]);

  const authed = auth.status === 'authenticated';
  const [page, setPage] = useState('dashboard');

  const [jobs, setJobs] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [filters, setFilters] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetail, setJobDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [total, setTotal] = useState(0);
  const [grandTotal, setGrandTotal] = useState(0);
  const [pageNum, setPageNum] = useState(0);
  const [sortKey, setSortKey] = useState('job_title');
  const [sortOrder, setSortOrder] = useState('asc');

  const [search, setSearch] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [department, setDepartment] = useState('');
  const [workplaceType, setWorkplaceType] = useState('');
  const [jobType, setJobType] = useState('');
  const [source, setSource] = useState('');

  const [trackedOpen, setTrackedOpen] = useState(null);
  const [browseVisited, setBrowseVisited] = useState(false);
  const trackedFetchSeq = useRef(0);

  const fetchFilters = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/filters`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      setFilters(await res.json());
    } catch (err) {
      console.error('Failed to fetch filters:', err);
      setError('Falha ao carregar filtros. Verifique se a API está online.');
    }
  }, []);

  const fetchCompanies = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/companies`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setCompanies(data.companies);
    } catch (err) {
      console.error('Failed to fetch companies:', err);
      setError('Falha ao carregar lista de empresas.');
    }
  }, []);

  const fetchJobs = useCallback(async (signal) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchDebounced) params.append('search', searchDebounced);
      if (companyId) params.append('company_id', companyId);
      if (city) params.append('city', city);
      if (state) params.append('state', state);
      if (department) params.append('department', department);
      if (workplaceType) params.append('workplaceType', workplaceType);
      if (jobType) params.append('jobType', jobType);
      if (source) params.append('source', source);
      params.append('sort', sortKey);
      params.append('order', sortOrder);
      params.append('offset', pageNum * PAGE_SIZE);
      params.append('limit', PAGE_SIZE);

      const res = await fetch(`${API_URL}/jobs?${params}`, { signal });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setJobs(data.jobs);
      setTotal(data.total);
      if (typeof data.grand_total === 'number') setGrandTotal(data.grand_total);
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Failed to fetch jobs:', err);
      setError('Erro ao buscar vagas. Tente novamente mais tarde.');
    } finally {
      setLoading(false);
    }
  }, [searchDebounced, companyId, city, state, department, workplaceType, jobType, source, sortKey, sortOrder, pageNum]);

  useEffect(() => {
    if (!authed || !browseVisited) return;
    fetchFilters();
    fetchCompanies();
  }, [authed, browseVisited, fetchFilters, fetchCompanies]);

  useEffect(() => {
    setSelectedJob(null);
    setTrackedOpen(null);
    if (page === 'browse') setBrowseVisited(true);
  }, [page]);

  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounced(search), 200);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!authed || !browseVisited) return undefined;
    const controller = new AbortController();
    fetchJobs(controller.signal);
    return () => controller.abort();
  }, [authed, browseVisited, fetchJobs]);

  useEffect(() => {
    if (!selectedJob) return undefined;
    const controller = new AbortController();
    setJobDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    (async () => {
      try {
        const res = await fetch(`${API_URL}/jobs/${selectedJob.job_id}/detail`, { signal: controller.signal });
        if (res.status === 404) {
          setJobDetail(null);
        } else if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        } else {
          setJobDetail(await res.json());
        }
      } catch (err) {
        if (err.name === 'AbortError') return;
        setDetailError('Não foi possível carregar o detalhe.');
      } finally {
        setDetailLoading(false);
      }
    })();
    return () => controller.abort();
  }, [selectedJob]);

  const handleSyncDetail = async () => {
    if (!selectedJob) return;
    setDetailLoading(true);
    setDetailError(null);
    try {
      const res = await fetch(`${API_URL}/jobs/${selectedJob.job_id}/detail/fetch`, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      setJobDetail(await res.json());
    } catch (err) {
      setDetailError(`Falha ao sincronizar: ${err.message}`);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleToggleSave = useCallback((job) => {
    const id = String(job.job_id);
    if (isTracked(id)) {
      removeJob(id);
    } else {
      addJob(jobRowToTracked(job));
    }
  }, [isTracked, removeJob, addJob]);
  const isJobSaved = useCallback((id) => isTracked(String(id)), [isTracked]);

  const openTrackedJobDetail = useCallback(async (trackedJob) => {
    setTrackedOpen(null);
    const seq = ++trackedFetchSeq.current;
    setSelectedJob(trackedToSelectedJob(trackedJob));
    try {
      const res = await fetch(`${API_URL}/jobs/${trackedJob.id}`);
      if (!res.ok) return;
      const fresh = await res.json();
      if (seq === trackedFetchSeq.current) setSelectedJob(fresh);
    } catch {
      // keep the synthesized fallback
    }
  }, []);
  const openTrackerNotes = useCallback((job) => {
    const tj = trackedJobs.find((t) => t.id === String(job.job_id));
    if (tj) setTrackedOpen(tj);
  }, [trackedJobs]);
  const advanceTracked = (job) => {
    const next = STAGE_NEXT[job.stage];
    if (next && next !== job.stage) updateStage(job.id, next);
    setTrackedOpen(null);
  };
  const trackedFresh = trackedOpen ? trackedJobs.find((j) => j.id === trackedOpen.id) || null : null;

  const handleLogout = async () => {
    await auth.logout();
    setUser({ name: '', email: '' });
  };

  if (auth.status === 'loading') {
    return <div className="login-shell"><div className="login-card">Carregando…</div></div>;
  }
  if (!authed) {
    return <Login onLogin={auth.login} onRegister={auth.register} />;
  }

  const counts = {
    saved: trackedJobs.filter((j) => j.stage === 'salva').length,
    pipeline: trackedJobs.length,
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="app">
      <Sidebar
        page={page}
        setPage={setPage}
        counts={counts}
        user={user}
        onLogout={handleLogout}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <ToastTray toasts={toastList} onDismiss={dismissToast} />
      <main className="main">
        {page === 'dashboard' && (
          <Dashboard
            trackedJobs={trackedJobs}
            user={user}
            onOpen={openTrackedJobDetail}
            onGoBrowse={() => setPage('browse')}
          />
        )}

        <div style={{ display: page === 'browse' ? 'block' : 'none' }}>
          <div className="page-head">
            <div>
              <h2>Buscar vagas</h2>
              <p>
                {total.toLocaleString('pt-BR')} vagas encontradas
                {grandTotal > 0 && grandTotal !== total && (
                  <> de {grandTotal.toLocaleString('pt-BR')} totais</>
                )}
              </p>
            </div>
          </div>

          {error && (
            <div className="App-error">
              {error}
              <button type="button" onClick={() => { setError(null); fetchFilters(); fetchCompanies(); fetchJobs(); }}>
                Tentar novamente
              </button>
            </div>
          )}

          <JobSearch
            value={search}
            onChange={(v) => { setSearch(v); setPageNum(0); }}
          />

          {filters && (
            <FilterBar
              companies={companies}
              filters={filters}
              selected={{ companyId, city, state, department, workplaceType, jobType, source }}
              onChange={(key, value) => {
                switch (key) {
                  case 'companyId': setCompanyId(value); break;
                  case 'city': setCity(value); break;
                  case 'state': setState(value); break;
                  case 'department': setDepartment(value); break;
                  case 'workplaceType': setWorkplaceType(value); break;
                  case 'jobType': setJobType(value); break;
                  case 'source': setSource(value); break;
                  default: break;
                }
                setPageNum(0);
              }}
              onReset={() => {
                setSearch(''); setCompanyId(''); setCity(''); setState('');
                setDepartment(''); setWorkplaceType(''); setJobType(''); setSource('');
                setPageNum(0);
              }}
              onApply={() => fetchJobs()}
            />
          )}

          <JobTable
            jobs={jobs}
            companies={companies}
            loading={loading}
            page={pageNum}
            totalPages={totalPages}
            sortKey={sortKey}
            sortOrder={sortOrder}
            onJobClick={setSelectedJob}
            onPageChange={setPageNum}
            onSort={(key) => {
              if (key === sortKey) {
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
              } else {
                setSortKey(key);
                setSortOrder('asc');
              }
              setPageNum(0);
            }}
            onToggleSave={handleToggleSave}
            isJobSaved={isJobSaved}
          />
        </div>

        {page === 'saved' && (
          <SavedJobs
            trackedJobs={trackedJobs}
            onOpen={openTrackedJobDetail}
            onApply={(j) => updateStage(j.id, 'aplicada')}
            onRemove={(j) => removeJob(j.id)}
          />
        )}

        {page === 'pipeline' && (
          <Pipeline
            trackedJobs={trackedJobs}
            onOpen={openTrackedJobDetail}
            onMove={updateStage}
          />
        )}

        {page === 'wordcloud' && (
          <WordCloud
            onWordClick={(word) => {
              setSearch(word);
              setPage('browse');
            }}
          />
        )}

        {page === 'settings' && (
          <Settings user={auth.user} />
        )}
      </main>

      {selectedJob && (
        <JobDetails
          job={selectedJob}
          detail={jobDetail}
          loading={detailLoading}
          error={detailError}
          company={companies.find((c) => c.id === selectedJob.company_id)}
          onSync={handleSyncDetail}
          onClose={() => { setSelectedJob(null); setJobDetail(null); setDetailError(null); }}
          onToggleSave={handleToggleSave}
          isSaved={isJobSaved(selectedJob.job_id)}
          onOpenTrackerNotes={openTrackerNotes}
        />
      )}

      <TrackedJobModal
        job={trackedFresh}
        onClose={() => setTrackedOpen(null)}
        onAdvance={advanceTracked}
        onNotes={updateNotes}
      />
    </div>
  );
}

export default App;

import { useCallback, useEffect, useState } from 'react';
import { ApiError, fetchJSON } from '../utils/api';

const trackedToLocal = (t) => ({
  id: String(t.job_id),
  title: t.title,
  company: t.company_name || '',
  company_id: t.company_id,
  location: t.location || '',
  source: t.source || '',
  ago: t.created_at ? '' : 'agora',
  job_url: t.job_url,
  workplace_city: t.workplace_city,
  workplace_state: t.workplace_state,
  workplace_type: t.workplace_type,
  job_type: t.job_type,
  job_department: t.job_department,
  stage: t.stage,
  notes: t.notes || '',
  events: Array.isArray(t.events) ? t.events : [],
});

const localToServer = (job) => ({
  job_id: job.id,
  source: job.source,
  title: job.title,
  company_name: job.company,
  company_id: job.company_id,
  location: job.location,
  job_url: job.job_url,
  job_type: job.job_type,
  job_department: job.job_department,
  workplace_type: job.workplace_type,
  workplace_city: job.workplace_city,
  workplace_state: job.workplace_state,
});

export default function useTrackedJobs(authStatus, onError) {
  const [trackedJobs, setTrackedJobs] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const reportError = useCallback((message) => {
    if (typeof onError === 'function') onError(message);
  }, [onError]);

  useEffect(() => {
    if (authStatus !== 'authenticated') {
      setTrackedJobs([]);
      setLoaded(false);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchJSON('/me/tracked');
        if (cancelled) return;
        setTrackedJobs((data?.tracked || []).map(trackedToLocal));
        setLoaded(true);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) return;
        reportError('Falha ao carregar vagas salvas.');
      }
    })();
    return () => { cancelled = true; };
  }, [authStatus, reportError]);

  const addJob = useCallback(async (job) => {
    if (trackedJobs.some((j) => j.id === job.id)) return;
    const optimistic = {
      ...job,
      stage: 'salva',
      notes: '',
      events: [{ when: 'agora', what: 'Vaga salva' }],
    };
    setTrackedJobs((prev) => [...prev, optimistic]);
    try {
      const data = await fetchJSON('/me/tracked', {
        method: 'POST',
        body: JSON.stringify(localToServer(job)),
      });
      const fresh = trackedToLocal(data.tracked);
      setTrackedJobs((prev) => prev.map((j) => (j.id === fresh.id ? fresh : j)));
    } catch (err) {
      setTrackedJobs((prev) => prev.filter((j) => j.id !== job.id));
      reportError(`Não foi possível salvar a vaga: ${err.message}`);
    }
  }, [trackedJobs, reportError]);

  const updateStage = useCallback(async (id, stage) => {
    const prevSnapshot = trackedJobs;
    setTrackedJobs((prev) => prev.map((j) => (j.id === id ? { ...j, stage } : j)));
    try {
      const data = await fetchJSON(`/me/tracked/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        body: JSON.stringify({ stage }),
      });
      const fresh = trackedToLocal(data.tracked);
      setTrackedJobs((prev) => prev.map((j) => (j.id === fresh.id ? fresh : j)));
    } catch (err) {
      setTrackedJobs(prevSnapshot);
      reportError(`Não foi possível atualizar o estágio: ${err.message}`);
    }
  }, [trackedJobs, reportError]);

  const updateNotes = useCallback(async (id, notes) => {
    const prevSnapshot = trackedJobs;
    setTrackedJobs((prev) => prev.map((j) => (j.id === id ? { ...j, notes } : j)));
    try {
      const data = await fetchJSON(`/me/tracked/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        body: JSON.stringify({ notes }),
      });
      const fresh = trackedToLocal(data.tracked);
      setTrackedJobs((prev) => prev.map((j) => (j.id === fresh.id ? fresh : j)));
    } catch (err) {
      setTrackedJobs(prevSnapshot);
      reportError(`Não foi possível salvar as anotações: ${err.message}`);
    }
  }, [trackedJobs, reportError]);

  const removeJob = useCallback(async (id) => {
    const prevSnapshot = trackedJobs;
    setTrackedJobs((prev) => prev.filter((j) => j.id !== id));
    try {
      await fetchJSON(`/me/tracked/${encodeURIComponent(id)}`, { method: 'DELETE' });
    } catch (err) {
      setTrackedJobs(prevSnapshot);
      reportError(`Não foi possível remover: ${err.message}`);
    }
  }, [trackedJobs, reportError]);

  const isTracked = useCallback((id) => trackedJobs.some((j) => j.id === String(id)), [trackedJobs]);

  return { trackedJobs, addJob, updateStage, updateNotes, removeJob, isTracked, loaded };
}

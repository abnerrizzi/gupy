import { useCallback, useEffect, useState } from 'react';
import { STAGE_META } from '../constants/stages';

const STORAGE_KEY = 'jh_jobs';

const readInitial = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const todayLabel = () => new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });

export default function useTrackedJobs() {
  const [trackedJobs, setTrackedJobs] = useState(readInitial);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trackedJobs));
    } catch {
      // QuotaExceededError or storage disabled — silently drop the persist.
    }
  }, [trackedJobs]);

  const addJob = useCallback((job) => {
    setTrackedJobs((prev) => {
      if (prev.some((j) => j.id === job.id)) return prev;
      return [...prev, {
        stage: 'salva',
        notes: '',
        events: [{ when: todayLabel(), what: 'Vaga salva' }],
        ...job,
      }];
    });
  }, []);

  const updateStage = useCallback((id, stage) => {
    setTrackedJobs((prev) => prev.map((j) => (
      j.id === id
        ? {
            ...j,
            stage,
            events: [
              ...(j.events || []),
              { when: todayLabel(), what: `Movida para ${STAGE_META[stage]?.label || stage}` },
            ],
          }
        : j
    )));
  }, []);

  const updateNotes = useCallback((id, notes) => {
    setTrackedJobs((prev) => prev.map((j) => (j.id === id ? { ...j, notes } : j)));
  }, []);

  const removeJob = useCallback((id) => {
    setTrackedJobs((prev) => prev.filter((j) => j.id !== id));
  }, []);

  const isTracked = useCallback((id) => trackedJobs.some((j) => j.id === id), [trackedJobs]);

  return { trackedJobs, addJob, updateStage, updateNotes, removeJob, isTracked };
}

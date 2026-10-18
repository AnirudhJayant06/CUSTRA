import { useCallback, useEffect, useState } from 'react';

import { api } from '../api/client.js';

function pause(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener('abort', () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    }, { once: true });
  });
}

export default function useCaseProgress(caseId) {
  const [complaint, setComplaint] = useState(null);
  const [events, setEvents] = useState([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((current) => current + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const path = `/api/complaints/${encodeURIComponent(caseId)}`;
    setError('');
    setPending(false);

    async function run() {
      let [saved, history] = await Promise.all([
        api(path, { signal }), api(`${path}/events`, { signal }),
      ]);
      if (signal.aborted) return;
      setComplaint(saved);
      setEvents(history);
      let sequence = history.at(-1)?.sequence || 0;
      let resumeError = attempt > 0;
      for (let step = 0; step < (saved.scenarioId === 'natural' ? 30 : 5); step += 1) {
        if (saved.status !== 'PROCESSING' && !(resumeError && saved.status === 'ERROR' && saved.recoveryPhase === 'advance')) break;
        resumeError = false;
        const version = saved.currentVersion;
        try {
          setPending(true);
          saved = await api(`${path}/advance`, { method: 'POST', signal, body: { expectedVersion: version } });
        } catch (failure) {
          if (failure.status !== 409 || /retry limit/i.test(failure.message)) throw failure;
          setPending(false);
          const deadline = Date.now() + 65_000;
          do {
            await pause(1000, signal);
            saved = await api(path, { signal });
          } while (saved.currentVersion === version && Date.now() < deadline);
          if (saved.currentVersion === version) throw new Error('The saved step is still pending. Retry shortly.');
        }
        const additions = await api(`${path}/events?after=${sequence}`, { signal });
        if (signal.aborted) return;
        history = [...history, ...additions].filter((event, index, all) =>
          all.findIndex((item) => item.eventId === event.eventId) === index);
        sequence = history.at(-1)?.sequence || sequence;
        setEvents(history);
        setComplaint(saved);
        setPending(false);
      }
    }

    run().catch((failure) => {
      if (!signal.aborted) setError(failure.message || 'Could not load saved progress.');
    }).finally(() => { if (!signal.aborted) setPending(false); });
    return () => controller.abort();
  }, [caseId, attempt]);

  return { complaint, events, pending, error, retry, setComplaint };
}

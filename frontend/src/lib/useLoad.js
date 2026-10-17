import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
export default function useLoad(paths) {
  const key = paths.join('|');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    Promise.all(key.split('|').map((path) => api(path, { signal: controller.signal })))
      .then((results) => { if (!controller.signal.aborted) setData(results); })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [key, version]);
  return { data, error, reload: () => setVersion((v) => v + 1) };
}

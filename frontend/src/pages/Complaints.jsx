import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client.js';

export default function Complaints({ productId }) {
  const [cases, setCases] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const query = productId ? `?productId=${encodeURIComponent(productId)}` : '';
    api(`/api/complaints${query}`, { signal: controller.signal })
      .then(setCases).catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); });
    return () => controller.abort();
  }, [productId]);

  return <section className="form-card">
    <h1>{productId ? 'Product complaints' : 'Complaints'}</h1>
    <Link className="record-action" to={`/complaints/new${productId ? `?productId=${encodeURIComponent(productId)}` : ''}`}>Start a complaint</Link>
    {error ? <p className="error" role="alert">{error}</p> : null}
    {cases === null ? <p role="status">Loading complaints…</p> : cases.length ? <ul className="record-list">
      {cases.map((complaint) => <li key={complaint.id}><Link to={`/complaints/${complaint.id}`}>{complaint.issueSummary}</Link><br />{complaint.status.replaceAll('_', ' ')}</li>)}
    </ul> : <p>No complaints yet.</p>}
  </section>;
}

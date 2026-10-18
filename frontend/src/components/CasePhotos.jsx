import { useEffect, useState } from 'react';

import { api } from '../api/client.js';
import DocumentUpload from './DocumentUpload.jsx';
import Icon from './Icon.jsx';

export default function CasePhotos({ caseId, complaint, onUpdated }) {
  const [photos, setPhotos] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dismissed, setDismissed] = useState([]);
  const [error, setError] = useState('');
  const path = `/api/complaints/${encodeURIComponent(caseId)}/documents`;

  useEffect(() => {
    const controller = new AbortController();
    api(path, { signal: controller.signal }).then(setPhotos)
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [path]);

  async function useDocument(documentId) {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const saved = await api(`/api/complaints/${encodeURIComponent(caseId)}/input`, { method: 'POST',
        body: { expectedVersion: complaint.currentVersion, documentId } });
      onUpdated?.(saved);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  async function saveToProduct(documentId) {
    if (busy) return;
    setBusy(true); setError('');
    try {
      await api(`${path}/${encodeURIComponent(documentId)}/save-to-product`, { method: 'POST', body: {} });
      setDismissed(current => [...current, documentId]);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <section className="case-documents" aria-label="Case documents">
    <DocumentUpload path={path} onUploaded={(saved) => { setPhotos((current) => [...current, saved]); onUpdated?.(); }} />
    {error ? <p className="error" role="alert">{error}</p> : null}
    <ul className="plain-list">{photos.map((photo) => {
      const contentUrl = `/api/documents/${encodeURIComponent(photo.id)}/content`;
      return <li className="document-row" key={photo.id}><Icon name="file" />
        <a href={contentUrl} target="_blank" rel="noopener noreferrer">{photo.originalName}</a>
        {photo.mediaType.startsWith('image/') ? <img className="document-preview" src={contentUrl} alt={`Stored ${photo.originalName}`} loading="lazy" /> : null}
        {complaint?.status === 'AWAITING_USER' && complaint.pendingUserRequest?.kind !== 'share' ? <button className="secondary" type="button" disabled={busy} onClick={() => useDocument(photo.id)}>Use this to answer</button> : null}
        {complaint?.suggestedProductDocument === photo.id && !dismissed.includes(photo.id) ? <div><p>Save this document to the product for future use?</p><button className="secondary" type="button" disabled={busy} onClick={() => saveToProduct(photo.id)}>Save to product</button><button className="text-button" type="button" onClick={() => setDismissed(current => [...current, photo.id])}>Not now</button></div> : null}
      </li>;
    })}</ul>
  </section>;
}

import { useEffect, useState } from 'react';

import { api } from '../api/client.js';
import DocumentUpload from './DocumentUpload.jsx';
import Icon from './Icon.jsx';

export default function CasePhotos({ caseId }) {
  const [photos, setPhotos] = useState([]);
  const [error, setError] = useState('');
  const path = `/api/complaints/${encodeURIComponent(caseId)}/documents`;

  useEffect(() => {
    const controller = new AbortController();
    api(path, { signal: controller.signal }).then(setPhotos)
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [path]);

  return <section className="case-documents" aria-label="Case documents">
    <DocumentUpload path={path} onUploaded={(saved) => setPhotos((current) => [...current, saved])} />
    {error ? <p className="error" role="alert">{error}</p> : null}
    <ul className="plain-list">{photos.map((photo) => {
      const contentUrl = `/api/documents/${encodeURIComponent(photo.id)}/content`;
      return <li className="document-row" key={photo.id}><Icon name="file" />
        <a href={contentUrl} target="_blank" rel="noopener noreferrer">{photo.originalName}</a>
        {photo.mediaType.startsWith('image/') ? <img className="document-preview" src={contentUrl} alt={`Stored ${photo.originalName}`} loading="lazy" /> : null}
      </li>;
    })}</ul>
  </section>;
}

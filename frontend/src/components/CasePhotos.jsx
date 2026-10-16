import { useEffect, useState } from 'react';

import { api, upload } from '../api/client.js';

export default function CasePhotos({ caseId }) {
  const [photos, setPhotos] = useState([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const path = `/api/complaints/${encodeURIComponent(caseId)}/documents`;

  useEffect(() => {
    const controller = new AbortController();
    api(path, { signal: controller.signal }).then(setPhotos)
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [path]);

  async function savePhoto(event) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    setPending(true);
    setError('');
    try {
      const saved = await upload(path, new FormData(form));
      setPhotos((current) => [...current, saved]);
      form.reset();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setPending(false);
    }
  }

  return <section aria-labelledby="case-photos-title">
    <h2 id="case-photos-title">Case photos</h2>
    <p className="hint">Optional JPEG or PNG files, up to 5 MB each. Photos are stored privately and are not analyzed by the agent.</p>
    <form onSubmit={savePhoto}>
      <fieldset disabled={pending}>
        <label htmlFor="case-photo">Choose a case photo</label>
        <input id="case-photo" name="file" type="file" required accept=".jpg,.jpeg,.png,image/jpeg,image/png" />
        <button className="secondary record-action" type="submit">{pending ? 'Uploading…' : 'Upload photo'}</button>
      </fieldset>
    </form>
    {error ? <p className="error" role="alert">{error}</p> : null}
    <ul className="record-list">{photos.map((photo) => {
      const contentUrl = `/api/documents/${encodeURIComponent(photo.id)}/content`;
      return <li key={photo.id}>
        <a href={contentUrl} target="_blank" rel="noopener noreferrer">{photo.originalName}</a>
        <img className="document-preview" src={contentUrl} alt={`Stored ${photo.originalName}`} loading="lazy" />
      </li>;
    })}</ul>
  </section>;
}

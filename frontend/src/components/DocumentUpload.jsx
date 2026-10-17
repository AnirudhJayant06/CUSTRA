import { useState } from 'react';
import { upload } from '../api/client.js';
import AttachmentPicker from './AttachmentPicker.jsx';

// Persisted products and cases share this upload flow. Product creation reuses
// AttachmentPicker alone until it has a saved ID to attach the document to.
export default function DocumentUpload({ path, onUploaded }) {
  const [file, setFile] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    if (!file || pending) return;
    setPending(true); setError('');
    try {
      const data = new FormData(); data.append('file', file);
      const saved = await upload(path, data);
      setFile(null); onUploaded(saved);
    } catch (failure) { setError(failure.message); }
    finally { setPending(false); }
  }
  return <form className="document-upload" onSubmit={submit}><fieldset disabled={pending}>
    <AttachmentPicker file={file} disabled={pending} onChange={(next) => { setFile(next); setError(''); }} />
    {file ? <button type="submit" className="secondary record-action">{pending ? 'Uploading…' : 'Upload document'}</button> : null}
    {error ? <p className="error" role="alert">{error}</p> : null}
  </fieldset></form>;
}

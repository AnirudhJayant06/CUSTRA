import { useEffect, useRef, useState } from 'react';
import Modal from './Modal.jsx';
import Icon from './Icon.jsx';
export default function AttachmentPicker({ file, onChange, disabled = false }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState('');
  const camera = useRef(null);
  const photos = useRef(null);
  const files = useRef(null);
  useEffect(() => {
    if (!file || !file.type.startsWith('image/')) { setPreview(''); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  function select(event) {
    const next = event.target.files?.[0];
    event.target.value = '';
    if (!next) return;
    setError('');
    if (next.size > 5_000_000) { setError('This file is over 5 MB. Choose a smaller photo or PDF.'); return; }
    if (!['application/pdf', 'image/jpeg', 'image/png'].includes(next.type) && !/\.(pdf|jpe?g|png)$/i.test(next.name)) {
      setError('Choose a JPG, PNG or PDF. For HEIC photos, export as JPG first.'); return;
    }
    onChange(next);
  }
  function choose(ref) { setOpen(false); ref.current?.click(); }
  return <div className="attachment-picker">
    <input ref={camera} hidden type="file" accept="image/*" capture="environment" onChange={select} aria-label="Take document photo" />
    <input ref={photos} hidden type="file" accept="image/*" onChange={select} aria-label="Choose document photo" />
    <input ref={files} hidden type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={select} aria-label="Choose document file" />
    {file ? <div className="attachment-selection">{preview ? <img src={preview} alt="Selected document" className="attachment-preview" /> : <Icon name="file" />}<span className="filename">{file.name}</span><div className="attachment-actions"><button type="button" className="text-button" disabled={disabled} onClick={() => setOpen(true)}>Replace document</button><button type="button" className="text-button" disabled={disabled} onClick={() => { onChange(null); setError(''); }}>Remove document</button></div></div> : <button className="attachment-trigger" aria-label="Add document" type="button" disabled={disabled} onClick={() => setOpen(true)}><Icon name="plus" /><span>Add document <small>optional</small></span><Icon name="arrow" /></button>}
    {error ? <p className="error" role="alert">{error}</p> : null}
    {open ? <Modal title="Add document" onClose={() => setOpen(false)}><div className="attachment-options"><button className="slim-row" type="button" onClick={() => choose(camera)}><Icon name="camera" /><span>Take photo</span><Icon name="arrow" /></button><button className="slim-row" type="button" onClick={() => choose(photos)}><Icon name="photo" /><span>Choose photo</span><Icon name="arrow" /></button><button className="slim-row" type="button" onClick={() => choose(files)}><Icon name="file" /><span>Upload file</span><Icon name="arrow" /></button></div><p className="hint">JPG, PNG or PDF · up to 5 MB. Camera options depend on your device; uploading a file is always available.</p></Modal> : null}
  </div>;
}

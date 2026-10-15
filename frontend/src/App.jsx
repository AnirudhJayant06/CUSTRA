import { useEffect, useRef, useState } from 'react';

export default function App() {
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState('');
  const [photoError, setPhotoError] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInput = useRef(null);
  const request = useRef(null);

  useEffect(() => {
    if (!photo) { setPreview(''); return; }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  useEffect(() => () => request.current?.abort(), []);

  function selectPhoto(event) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    setPhotoError('');
    if (!selected.type.startsWith('image/')) {
      setPhotoError('Please select an image file.');
      event.target.value = '';
      return;
    }
    setPhoto(selected);
  }

  async function submit(event) {
    event.preventDefault();
    if (request.current) return;
    const form = event.currentTarget;
    const fields = new FormData(form);
    const payload = {
      product_name: fields.get('product_name').trim(),
      description: fields.get('description').trim(),
    };
    for (const name of ['product_name', 'description']) {
      const input = form.elements.namedItem(name);
      input.setCustomValidity(payload[name] ? '' : 'Please enter more than spaces.');
    }
    if (!form.reportValidity()) return;
    setPending(true);
    setError('');
    setResult(null);
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('/api/test-issue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = Array.isArray(body?.detail)
          ? body.detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join('; ')
          : body?.detail;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}).`);
      }
      if (body?.success !== true || typeof body.message !== 'string') {
        throw new Error('The server returned an unexpected response.');
      }
      setResult(body);
    } catch (failure) {
      setError(failure.name === 'AbortError'
        ? 'The request timed out. Please try again.'
        : failure instanceof TypeError
          ? 'Could not reach Custra. Check your connection and try again.'
          : failure.message);
    } finally {
      clearTimeout(timeout);
      request.current = null;
      setPending(false);
    }
  }

  return (
    <div className="shell">
      <header className="brand"><span className="brand-mark" aria-hidden="true">c.</span><span>custra<span className="brand-dot">.</span></span><span className="demo-label">DEMO</span></header>
      <main>
        <section className="intro" aria-labelledby="intro-title">
          <p className="eyebrow">ON YOUR SIDE. EVERY STEP.</p>
          <h1 id="intro-title">Your AI representative<br />across every brand.</h1>
          <p className="intro-copy">Product trouble? Start here. Tell us what happened in a few simple steps.</p>
          <div className="demo-note"><span className="status-dot" aria-hidden="true" /><p><strong>A small preview of Custra</strong><br />This demo confirms your submission. It doesn’t save a case or contact a brand.</p></div>
        </section>
        <section className="form-card" aria-labelledby="form-title">
          <p className="eyebrow">LET’S GET THE DETAILS</p>
          <h2 id="form-title">Report a Product Issue</h2>
          <p className="form-intro">Fields marked <span aria-hidden="true">*</span> are required.</p>
          <form onSubmit={submit}>
            <fieldset disabled={pending}>
              <label htmlFor="product">Product Name <span aria-hidden="true">*</span></label>
              <input id="product" name="product_name" placeholder="e.g. Samsung Washing Machine" required maxLength={120} onChange={(event) => event.target.setCustomValidity('')} />
              <label htmlFor="description">Issue Description <span aria-hidden="true">*</span></label>
              <textarea id="description" name="description" placeholder="What went wrong? Share a few details…" required maxLength={2000} rows={5} onChange={(event) => event.target.setCustomValidity('')} aria-describedby="description-help" />
              <p className="hint" id="description-help">Up to 2,000 characters.</p>
              <label htmlFor="photo">Photo Evidence <span className="optional">Optional</span></label>
              <div className="photo-box">
                <input ref={fileInput} id="photo" type="file" accept="image/*" onChange={selectPhoto} aria-describedby="photo-help" />
                {preview ? <div className="preview"><img src={preview} alt="Selected product evidence" onError={() => setPhotoError('This image format cannot be previewed in your browser. Try a JPEG or PNG.')} /><p>{photo?.name}</p><button type="button" className="secondary" onClick={() => { setPhoto(null); setPhotoError(''); fileInput.current.value = ''; }}>Remove photo</button></div> : null}
                <p className="hint" id="photo-help">Choose from your camera or gallery where supported. Photos stay on this device and aren’t included in test submissions.</p>
                {photoError ? <p className="error" role="alert">{photoError}</p> : null}
              </div>
              <button className="submit" type="submit">{pending ? 'Submitting…' : error ? 'Try Again' : 'Submit Issue'}<span aria-hidden="true">→</span></button>
            </fieldset>
            <div aria-live="polite" aria-atomic="true">
              {pending ? <p className="hint">Sending your text details to Custra…</p> : null}
              {error ? <p className="error response" role="alert">{error} Your details are still here so you can retry.</p> : null}
              {result ? <div className="response success"><h3>{result.message}</h3><dl><dt>Product</dt><dd>{result.product_name}</dd><dt>Description</dt><dd>{result.description}</dd><dt>Status</dt><dd>{result.status}</dd></dl><p className="hint">Test only. No case has been saved.</p></div> : null}
            </div>
          </form>
        </section>
      </main>
      <footer>Customer Unified Support, Tracking &amp; Resolution Agent<span>Built for AI Builder Cup 2026</span></footer>
    </div>
  );
}

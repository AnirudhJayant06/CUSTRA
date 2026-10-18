import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

const labels = {
  'product.brand': 'Brand', 'product.model': 'Model number', 'product.serialNumber': 'Serial number',
  'product.purchaseDate': 'Purchase date', 'product.invoiceNumber': 'Invoice number',
  'product.seller': 'Seller', 'product.sellerBranch': 'Seller branch',
  'product.warrantyMonths': 'Warranty months', 'product.warrantyExpiry': 'Warranty expiry',
  'profile.name': 'Contact name', 'profile.phone': 'Phone for this complaint', 'profile.email': 'Contact email',
  'address.line1': 'Service address', 'address.line2': 'Address line 2', 'address.region': 'State', 'address.country': 'Country', 'address.city': 'City', 'address.postal_code': 'Postal code',
  'issue.summary': 'Issue summary', 'issue.description': 'Issue description', 'appointment.preference': 'Appointment preference',
};

const factLabel = key => labels[key] || key.replace(/^product\.details\./, '').replaceAll('_', ' ').replace(/^./, letter => letter.toUpperCase());

export default function ConversationActions({ complaint, onUpdated }) {
  const [values, setValues] = useState({});
  const [text, setText] = useState('');
  const [field, setField] = useState('product.purchaseDate');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [documents, setDocuments] = useState([]);
  const [chooseAnother, setChooseAnother] = useState(false);
  const request = complaint.pendingUserRequest;
  const path = `/api/complaints/${encodeURIComponent(complaint.id)}`;
  useEffect(() => { setValues({}); setText(''); setError(''); setChooseAnother(false); }, [complaint.currentVersion]);
  useEffect(() => {
    if (request?.kind !== 'share') return undefined;
    const controller = new AbortController();
    Promise.all([api(`/api/products/${encodeURIComponent(complaint.productId)}/documents`, { signal: controller.signal }),
      api(`${path}/documents`, { signal: controller.signal })])
      .then(([product, chat]) => { if (!controller.signal.aborted) setDocuments([...new Map([...product, ...chat].map(d => [d.id, d])).values()]); })
      .catch(failure => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [request?.kind, complaint.productId, path, complaint.currentVersion]);

  async function action(name, extra = {}) {
    if (busy) return;
    setBusy(true); setError('');
    try {
      if (name === 'share' && !extra.documentVersion) {
        const metadata = await api(`/api/documents/${encodeURIComponent(extra.documentId)}/version`);
        extra.documentVersion = metadata.version;
      }
      onUpdated(await api(`${path}/${name}`, { method: 'POST', body: { expectedVersion: complaint.currentVersion, ...extra } })); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  const selectedDocument = documents.find(doc => doc.id === request?.candidates?.[0]?.id) || documents[0];
  const showChoices = chooseAnother || (documents.length > 1 && request?.candidates?.length !== 1);
  const visibleDocuments = showChoices ? documents : selectedDocument ? [selectedDocument] : [];
  const paused = complaint.status === 'PAUSED';
  if (complaint.scenarioId !== 'natural' || ['CLOSED', 'BOOKED', 'AWAITING_APPOINTMENT'].includes(complaint.status)) return null;
  return <section className="conversation-actions" aria-label="Conversation actions">
    {!paused && ['PROCESSING', 'ERROR', 'AWAITING_USER'].includes(complaint.status) ? <button type="button" className="text-button" disabled={busy} onClick={() => action('pause')}>Pause and correct</button> : null}
    {paused ? <>
      <p>Automation is paused. An answer already sent may need a correction.</p>
      <form onSubmit={event => { event.preventDefault(); action('input', { text, values: { [field]: text } }); }}>
        <label htmlFor="correction-field">Information to correct</label><select id="correction-field" value={field} onChange={event => setField(event.target.value)}>{Object.entries({ ...Object.fromEntries(Object.keys(complaint.factOverrides || {}).map(key => [key, factLabel(key)])), ...labels }).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
        <label>Correct value<input required maxLength={500} value={text} onChange={event => setText(event.target.value)} /></label>
        <div className="dialog-actions"><button disabled={busy}>Save correction and continue</button><button type="button" className="secondary" disabled={busy} onClick={() => action('resume')}>Resume conversation</button></div>
      </form>
    </> : null}
    {complaint.status === 'AWAITING_USER' && request ? <>
      <p>{request.prompt}</p>
      {request.kind === 'share' ? <div>
        <p className="hint">Review the file before sharing it with business support.</p>
        {!documents.length ? <p>Upload the requested document below, then refresh this conversation.</p> : null}
        <ul className="plain-list">{visibleDocuments.map(doc => <li className="document-choice" key={doc.id}>
          <a href={`/api/documents/${encodeURIComponent(doc.id)}/content`} target="_blank" rel="noopener noreferrer">{doc.originalName}</a>
          {doc.description ? <p className="hint">{doc.description}</p> : null}
          <button className="secondary" type="button" disabled={busy} onClick={() => action('share', { documentId: doc.id, documentVersion: doc.version })}>{showChoices ? `Share ${doc.originalName}` : 'Share this'}</button>
        </li>)}</ul>
        {!showChoices && documents.length ? <button className="text-button" type="button" onClick={() => setChooseAnother(true)}>Choose another</button> : null}
      </div> : <form onSubmit={event => { event.preventDefault(); action('input', { text, values }); }}>
        {request.fields?.length ? request.fields.map(key => <label key={key}>{factLabel(key)}
          <input required type={key === 'product.purchaseDate' || key === 'product.warrantyExpiry' ? 'date' : 'text'} maxLength={500} value={values[key] || ''} onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))} />
        </label>) : <label>Your clarification<textarea required maxLength={2000} value={text} onChange={event => setText(event.target.value)} /></label>}
        <button disabled={busy}>{busy ? 'Sending…' : 'Send details'}</button>
      </form>}
    </> : null}
    {error ? <p className="error" role="alert">{error}</p> : null}
  </section>;
}

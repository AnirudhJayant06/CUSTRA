import { useRef, useState } from 'react';
import { api } from '../api/client.js';
import Modal from './Modal.jsx';
export default function AddressDialog({ address = null, onClose, onSaved }) {
  const created = useRef(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [label, setLabel] = useState(address?.label || 'Home');
  async function submit(event) {
    event.preventDefault(); if (pending) return;
    const fields = new FormData(event.currentTarget);
    const body = Object.fromEntries(['line1', 'line2', 'city', 'region', 'postalCode', 'country'].map((key) => [key, String(fields.get(key) || '').trim()]));
    body.label = label.trim();
    setPending(true); setError('');
    try {
      const id = address?.id || created.current?.id;
      const saved = await api(id ? `/api/addresses/${id}` : '/api/addresses', { method: id ? 'PATCH' : 'POST', body });
      created.current = saved;
      if (fields.get('default')) await api(`/api/profile/default-address/${saved.id}`, { method: 'PUT' });
      onSaved(saved, Boolean(fields.get('default')));
    } catch (e) { setError(`${created.current && !address ? 'Address saved. Retry to finish without adding another. ' : ''}${e.message}`); } finally { setPending(false); }
  }
  return <Modal title={address ? 'Edit address' : 'Add address'} onClose={onClose} busy={pending}><form onSubmit={submit}><fieldset disabled={pending}>
    <label htmlFor="address-label">Label</label><div className="label-options">{['Home', 'Work', 'Other'].map((value) => <button className={label === value || value === 'Other' && !['Home', 'Work'].includes(label) ? 'selected secondary' : 'secondary'} type="button" key={value} onClick={() => setLabel(value === 'Other' ? '' : value)}>{value}</button>)}</div><input id="address-label" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={60} required placeholder="Address label" />
    <label htmlFor="address-line1">Address line 1</label><input id="address-line1" name="line1" defaultValue={address?.line1 || ''} required maxLength={180} autoComplete="address-line1" />
    <label htmlFor="address-line2">Address line 2 (optional)</label><input id="address-line2" name="line2" defaultValue={address?.line2 || ''} maxLength={180} autoComplete="address-line2" />
    <div className="form-columns"><div><label htmlFor="address-city">City</label><input id="address-city" name="city" required maxLength={100} defaultValue={address?.city || ''} autoComplete="address-level2" /></div><div><label htmlFor="address-region">State</label><input id="address-region" name="region" required maxLength={100} defaultValue={address?.region || ''} autoComplete="address-level1" /></div></div>
    <div className="form-columns"><div><label htmlFor="address-postal">PIN code</label><input id="address-postal" name="postalCode" required maxLength={20} defaultValue={address?.postalCode || ''} autoComplete="postal-code" /></div><div><label htmlFor="address-country">Country</label><input id="address-country" name="country" required maxLength={80} defaultValue={address?.country || 'India'} autoComplete="country-name" /></div></div>
    <label className="checkbox-row"><input name="default" type="checkbox" />Use as default address</label>
    {error ? <p className="error" role="alert">{error}</p> : null}<div className="dialog-actions"><button className="secondary" type="button" onClick={onClose}>Cancel</button><button className="primary">{pending ? 'Saving…' : address ? 'Save changes' : 'Save address'}</button></div>
  </fieldset></form></Modal>;
}

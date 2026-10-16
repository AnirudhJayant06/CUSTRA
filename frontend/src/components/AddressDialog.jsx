import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client.js';

export default function AddressDialog({ address = null, onClose, onSaved }) {
  const dialog = useRef(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const previous = document.activeElement;
    dialog.current?.focus();
    return () => previous?.focus();
  }, []);

  async function submit(event) {
    event.preventDefault();
    if (pending) return;
    const fields = new FormData(event.currentTarget);
    const body = Object.fromEntries(['label', 'line1', 'line2', 'city', 'region', 'postalCode', 'country']
      .map((name) => [name, String(fields.get(name) || '').trim()]));
    setPending(true);
    setError('');
    try {
      const saved = await api(address ? `/api/addresses/${encodeURIComponent(address.id)}` : '/api/addresses', {
        method: address ? 'PATCH' : 'POST', body,
      });
      onSaved(saved);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setPending(false);
    }
  }

  function handleKeys(event) {
    if (event.key === 'Escape' && !pending) onClose();
    if (event.key !== 'Tab') return;
    const focusable = Array.from(dialog.current.querySelectorAll('input, button')).filter((node) => !node.disabled);
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) {
      event.preventDefault(); last?.focus();
    }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  return (
    <div className="dialog-backdrop">
      <section className="dialog-card" role="dialog" aria-modal="true" aria-labelledby="address-title"
        tabIndex={-1} ref={dialog} onKeyDown={handleKeys}>
        <h2 id="address-title">{address ? 'Edit address' : 'Add address'}</h2>
        <p className="hint">This address will be saved in Account settings.</p>
        <form onSubmit={submit}>
          <fieldset disabled={pending}>
            <label htmlFor="address-label">Label</label><input id="address-label" name="label" required maxLength={60} defaultValue={address?.label || ''} />
            <label htmlFor="address-line1">Address line 1</label><input id="address-line1" name="line1" required maxLength={180} defaultValue={address?.line1 || ''} />
            <label htmlFor="address-line2">Address line 2</label><input id="address-line2" name="line2" maxLength={180} defaultValue={address?.line2 || ''} />
            <label htmlFor="address-city">City</label><input id="address-city" name="city" required maxLength={100} defaultValue={address?.city || ''} />
            <label htmlFor="address-region">State or region</label><input id="address-region" name="region" required maxLength={100} defaultValue={address?.region || ''} />
            <label htmlFor="address-postal">Postal code</label><input id="address-postal" name="postalCode" required maxLength={20} defaultValue={address?.postalCode || ''} />
            <label htmlFor="address-country">Country</label><input id="address-country" name="country" required maxLength={80} defaultValue={address?.country || 'India'} />
            {error ? <p className="error" role="alert">{error}</p> : null}
            <div className="dialog-actions">
              <button type="button" className="secondary" onClick={onClose}>Cancel</button>
              <button className="submit" type="submit">{pending ? 'Saving…' : address ? 'Update address' : 'Save address'}</button>
            </div>
          </fieldset>
        </form>
      </section>
    </div>
  );
}

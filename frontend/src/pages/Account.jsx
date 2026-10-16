import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client.js';
import AddressDialog from '../components/AddressDialog.jsx';

export default function Account() {
  const [draft, setDraft] = useState(null);
  const dirty = useRef(false);
  const [addresses, setAddresses] = useState([]);
  const [showAddress, setShowAddress] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  function changeField(field, value) {
    dirty.current = true;
    setDraft((current) => ({ ...current, [field]: value }));
  }

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    Promise.all([
      api('/api/profile', { signal: controller.signal }),
      api('/api/addresses', { signal: controller.signal }),
    ]).then(([currentProfile, currentAddresses]) => {
      if (!active) return;
      if (!dirty.current) setDraft(currentProfile);
      setAddresses(currentAddresses);
    }).catch((failure) => { if (active && failure.name !== 'AbortError') setError(failure.message); });
    return () => { active = false; controller.abort(); };
  }, []);

  async function save(event) {
    event.preventDefault();
    const data = { name: draft.name.trim(), phone: draft.phone.trim(), email: draft.email.trim() };
    setSaved(false);
    setError('');
    try {
      const updated = await api('/api/profile', { method: 'PATCH', body: data });
      setDraft(updated);
      dirty.current = false;
      setSaved(true);
    } catch (failure) {
      setError(failure.message);
    }
  }

  return (
    <div className="content-stack">
      <section className="form-card">
        <h1>Account settings</h1>
        <p className="hint">Saved details help the agent answer basic support questions.</p>
        {draft ? <form onSubmit={save}>
          <label htmlFor="profile-name">Name</label>
          <input id="profile-name" name="name" value={draft.name} onInput={(event) => changeField('name', event.currentTarget.value)} required maxLength={120} />
          <label htmlFor="profile-phone">Phone</label>
          <input id="profile-phone" name="phone" type="tel" value={draft.phone} onInput={(event) => changeField('phone', event.currentTarget.value)} required maxLength={40} />
          <label htmlFor="profile-email">Email</label>
          <input id="profile-email" name="email" type="email" value={draft.email} onInput={(event) => changeField('email', event.currentTarget.value)} required maxLength={254} />
          <button className="submit" type="submit">Save profile</button>
          {saved ? <p role="status">Profile saved.</p> : null}
        </form> : <p role="status">Loading profile…</p>}
        {error ? <p className="error" role="alert">{error}</p> : null}
      </section>
      <section className="form-card">
        <h2>Addresses</h2>
        <ul className="record-list">{addresses.map((address) =>
          <li key={address.id}><strong>{address.label}</strong>{address.isDemo ? ' · Demo address' : ''}<br />
            {address.line1}, {address.city}, {address.region} {address.postalCode}
            {!address.isDemo ? <button type="button" className="secondary record-action" onClick={() => setShowAddress(address)}>Edit</button> : null}
          </li>)}</ul>
        <button className="secondary" type="button" onClick={() => setShowAddress(true)}>Add address</button>
      </section>
      {showAddress ? <AddressDialog address={showAddress === true ? null : showAddress}
        onClose={() => setShowAddress(false)} onSaved={(address) => {
        setAddresses((current) => current.some((item) => item.id === address.id)
          ? current.map((item) => item.id === address.id ? address : item)
          : [...current, address]);
        setShowAddress(false);
      }} /> : null}
    </div>
  );
}

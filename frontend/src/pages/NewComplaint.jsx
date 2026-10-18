import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';
import useLoad from '../lib/useLoad.js';
import AddressDialog from '../components/AddressDialog.jsx';
import Modal from '../components/Modal.jsx';
import SchedulePicker, { slotDate } from '../components/SchedulePicker.jsx';
import Icon from '../components/Icon.jsx';
import { dateLabel, slotLabel } from '../lib/domain.js';
export default function NewComplaint() {
  const [params] = useSearchParams();
  const { data, error: loadError } = useLoad(['/api/products', '/api/addresses', '/api/profile', '/api/availability']);
  const [products = [], initialAddresses = [], savedProfile, availability = { slots: [] }] = data || [];
  const [addresses, setAddresses] = useState([]);
  const [profile, setProfile] = useState(null);
  const [productId, setProduct] = useState(params.get('productId') || '');
  const [addressId, setAddress] = useState('');
  const [description, setDescription] = useState('');
  const [preference, setPreference] = useState(null);
  const [dialog, setDialog] = useState('');
  const [editingAddress, setEditingAddress] = useState(false);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const operation = useRef(null);
  const inFlight = useRef(false);
  const navigate = useNavigate();
  useEffect(() => {
    if (!data) return;
    setAddresses(initialAddresses); setProfile(savedProfile);
    setAddress((value) => value || savedProfile.defaultAddressId || initialAddresses[0]?.id || '');
    setProduct((value) => value || (products.length === 1 ? products[0].id : ''));
  }, [data]);
  const selectedProduct = products.find((p) => p.id === productId);
  const selectedAddress = addresses.find((a) => a.id === addressId);
  const profileReady = profile && ['name', 'phone', 'email'].every((f) => profile[f]?.trim());
  async function submit(event) {
    event.preventDefault(); if (inFlight.current) return;
    if (!profileReady) { setDialog('phone'); setError('Complete your contact details to continue.'); return; }
    const body = { productId, addressId, contact: { name: profile.name, phone: profile.phone, email: profile.email }, description: description.trim(), preferredDate: preference ? slotDate(preference) : null, preferredSlotId: preference?.id || null };
    const fingerprint = JSON.stringify(body);
    if (operation.current?.fingerprint !== fingerprint) operation.current = { fingerprint, key: crypto.randomUUID() };
    inFlight.current = true; setPending(true); setError('');
    try {
      const saved = await api('/api/complaints', { method: 'POST', body, headers: { 'Idempotency-Key': operation.current.key } });
      navigate(`/complaints/${saved.id}`);
    } catch (failure) { setError(Object.values(failure.fieldErrors || {}).join(' ') || failure.message); } finally { inFlight.current = false; setPending(false); }
  }
  async function saveContact(e) {
    e.preventDefault(); const form = new FormData(e.currentTarget); setPending(true); setError('');
    const body = Object.fromEntries(['name', 'phone', 'email'].map((f) => [f, String(form.get(f) || profile[f] || '').trim()]));
    try { setProfile(current => ({ ...current, ...body })); setDialog(''); }
    catch (e) { setError(e.message); } finally { setPending(false); }
  }
  if (!data) return <p role={loadError ? 'alert' : 'status'}>{loadError || 'Loading your saved details…'}</p>;
  return <section className="page intake-page"><Link className="back-link" to={selectedProduct ? `/products/${productId}` : '/'}>← Back</Link><h1>Register complaint</h1>
    {!products.length ? <div className="empty-state"><p>Add a product before registering a complaint.</p><Link className="primary" to="/products/new">Add product</Link></div> : <form onSubmit={submit}><fieldset disabled={pending}>
      <label htmlFor="complaint-product">Saved product</label><select id="complaint-product" required value={productId} onChange={(e) => setProduct(e.target.value)}><option value="">Choose a product</option>{products.map((p) => <option key={p.id} value={p.id}>{p.displayName}</option>)}</select>
      <label htmlFor="description">What’s wrong?</label><textarea id="description" required maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="For example, the screen stays black when I switch it on." />
      <div className="slim-fields">
        <button type="button" className="slim-row" onClick={() => setDialog('address')}><Icon name="pin" /><span><strong>Service address</strong><small>{selectedAddress ? `${selectedAddress.label} · ${selectedAddress.city}` : 'Choose an address'}</small></span><Icon name="arrow" /></button>
        <button type="button" className="slim-row" onClick={() => setDialog('phone')}><Icon name="phone" /><span><strong>Phone number</strong><small>{profile?.phone ? `••••••${profile.phone.slice(-4)}` : 'Add contact details'}</small></span><Icon name="arrow" /></button>
        <button type="button" className="slim-row" onClick={() => setDialog('date')}><Icon name="calendar" /><span><strong>Preferred date</strong><small>{preference ? dateLabel(slotDate(preference)) : 'Choose a date (optional)'}</small></span><Icon name="arrow" /></button>
        <button type="button" className="slim-row" onClick={() => setDialog('time')}><Icon name="clock" /><span><strong>Preferred time</strong><small>{preference ? slotLabel(preference) : 'Choose a time (optional)'}</small></span><Icon name="arrow" /></button>
      </div><p className="hint">Preferred slot, subject to confirmation. Business support is simulated.</p>{preference ? <button type="button" className="text-button" onClick={() => setPreference(null)}>Clear preference</button> : null}
      {!profileReady ? <p className="hint">Complete your contact details using the Phone number row.</p> : null}
      {error ? <p className="error" role="alert">{error}</p> : null}<button className="primary full" disabled={!productId || !addressId}>{pending ? 'Registering…' : 'Register complaint'}</button>
    </fieldset></form>}
    {['date', 'time'].includes(dialog) ? <SchedulePicker initialMode={dialog === 'time' && preference ? 'time' : 'date'} slots={availability.slots} initialSlotId={preference?.id} onClose={() => setDialog('')} onSelect={(s) => { setPreference(s); setDialog(''); }} /> : null}
    {dialog === 'address' ? <Modal title="Service address" onClose={() => setDialog('')}><ul className="plain-list">{addresses.map((a) => <li key={a.id}><button className="slim-row" onClick={() => { setAddress(a.id); setDialog(''); }}><span><strong>{a.label}</strong><small>{a.line1}, {a.city}</small></span>{a.id === addressId ? <Icon name="check" /> : <Icon name="arrow" />}</button></li>)}</ul><button className="secondary" onClick={() => { setDialog(''); setEditingAddress(true); }}>Add address</button></Modal> : null}
    {editingAddress ? <AddressDialog onClose={() => setEditingAddress(false)} onSaved={(a) => { setAddresses((current) => [...current, a]); setAddress(a.id); setEditingAddress(false); }} /> : null}
    {dialog === 'phone' ? <Modal title={profileReady ? 'Phone number' : 'Contact details'} onClose={() => setDialog('')} busy={pending}><form onSubmit={saveContact}><fieldset disabled={pending}>{!profileReady ? <><label htmlFor="inline-name">Full name</label><input id="inline-name" name="name" required defaultValue={profile?.name} maxLength={120} /><label htmlFor="inline-email">Email</label><input id="inline-email" name="email" type="email" required defaultValue={profile?.email} maxLength={254} /></> : null}<label htmlFor="inline-phone">Phone number</label><input id="inline-phone" name="phone" type="tel" required defaultValue={profile?.phone} maxLength={40} />{error ? <p className="error" role="alert">{error}</p> : null}<p className="hint">Only for this complaint. Your Profile is unchanged.</p><button className="primary full">{pending ? 'Saving…' : 'Save details'}</button></fieldset></form></Modal> : null}
  </section>;
}

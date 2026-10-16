import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { api } from '../api/client.js';
import AddressDialog from '../components/AddressDialog.jsx';

export default function NewComplaint() {
  const [params] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [addresses, setAddresses] = useState([]);
  const [profile, setProfile] = useState(null);
  const [productId, setProductId] = useState(params.get('productId') || '');
  const [addressId, setAddressId] = useState('');
  const [issueSummary, setSummary] = useState('');
  const [description, setDescription] = useState('');
  const [showAddress, setShowAddress] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const operation = useRef(null);
  const inFlight = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api('/api/products', { signal: controller.signal }),
      api('/api/addresses', { signal: controller.signal }),
      api('/api/profile', { signal: controller.signal }),
    ]).then(([savedProducts, savedAddresses, savedProfile]) => {
      if (controller.signal.aborted) return;
      setProducts(savedProducts);
      setAddresses(savedAddresses);
      setProfile(savedProfile);
      setAddressId((current) => current || savedProfile.defaultAddressId || savedAddresses[0]?.id || '');
    }).catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); });
    return () => controller.abort();
  }, []);

  async function submit(event) {
    event.preventDefault();
    if (inFlight.current) return;
    const body = { productId, addressId, issueSummary: issueSummary.trim(), description: description.trim() };
    const fingerprint = JSON.stringify(body);
    if (!operation.current || operation.current.fingerprint !== fingerprint) {
      operation.current = { fingerprint, key: crypto.randomUUID() };
    }
    inFlight.current = true;
    setPending(true);
    setError('');
    try {
      const saved = await api('/api/complaints', { method: 'POST', body,
        headers: { 'Idempotency-Key': operation.current.key } });
      navigate(`/complaints/${saved.id}`);
    } catch (failure) {
      setError(failure.message);
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  const profileReady = profile && ['name', 'phone', 'email'].every((field) => profile[field]?.trim());

  return (
    <section className="form-card">
      <h1>Start a complaint</h1>
      <p className="hint">The Consumer Agent will answer a simulated business using your saved details.</p>
      {!profileReady ? <p>Complete your name, phone and email in <Link to="/account">Account settings</Link> before starting.</p> : null}
      <form onSubmit={submit}>
        <fieldset disabled={pending || !profileReady}>
          <label htmlFor="complaint-product">Saved product</label>
          <select id="complaint-product" value={productId} onChange={(event) => setProductId(event.target.value)} required>
            <option value="">Choose a product</option>
            {products.map((product) => <option key={product.id} value={product.id}>{product.displayName}</option>)}
          </select>
          <label htmlFor="complaint-address">Service address</label>
          <select id="complaint-address" value={addressId} onChange={(event) => setAddressId(event.target.value)} required>
            <option value="">Choose an address</option>
            {addresses.map((address) => <option key={address.id} value={address.id}>{address.label} — {address.line1}</option>)}
          </select>
          <button className="secondary record-action" type="button" onClick={() => setShowAddress(true)}>Add address</button>
          <label htmlFor="issue-summary">Issue summary</label>
          <input id="issue-summary" value={issueSummary} onChange={(event) => setSummary(event.target.value)} required maxLength={120} />
          <label htmlFor="issue-description">Issue description</label>
          <textarea id="issue-description" value={description} onChange={(event) => setDescription(event.target.value)} required maxLength={2000} rows={5} />
          <button className="submit" type="submit">{pending ? 'Starting…' : 'Start complaint'}</button>
        </fieldset>
        {error ? <p className="error" role="alert">{error}</p> : null}
      </form>
      {showAddress ? <AddressDialog onClose={() => setShowAddress(false)} onSaved={(address) => {
        setAddresses((current) => [...current, address]);
        setAddressId(address.id);
        setShowAddress(false);
      }} /> : null}
    </section>
  );
}

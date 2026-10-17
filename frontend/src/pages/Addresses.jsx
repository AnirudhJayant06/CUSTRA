import { useState } from 'react';
import { Link } from 'react-router-dom';
import useLoad from '../lib/useLoad.js';
import { api } from '../api/client.js';
import AddressDialog from '../components/AddressDialog.jsx';
import Icon from '../components/Icon.jsx';
export default function Addresses() {
  const { data, error, reload } = useLoad(['/api/addresses', '/api/profile']);
  const [editing, setEditing] = useState(null);
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  async function makeDefault(id) { if (busy) return; setBusy(true); setFailure(''); try { await api(`/api/profile/default-address/${id}`, { method: 'PUT' }); reload(); } catch (e) { setFailure(e.message); } finally { setBusy(false); } }
  return <section className="page"><Link className="back-link" to="/account">← Profile</Link><div className="section-heading"><h1>Addresses</h1><button className="text-button" onClick={() => setEditing(true)}>+ Add address</button></div>
    {data ? <ul className="plain-list">{data[0].map((a) => <li className="address-row" key={a.id}><Icon name={a.label.toLowerCase() === 'home' ? 'home' : 'pin'} size={28} /><div className="row-content"><div className="section-heading"><h2>{a.label}</h2>{!a.isDemo ? <button className="text-button" onClick={() => setEditing(a)}>Edit</button> : null}</div>{data[1].defaultAddressId === a.id ? <span className="status">Default</span> : null}<p>{a.line1}{a.line2 ? `, ${a.line2}` : ''}<br />{a.city}, {a.region} · {a.postalCode}<br />{a.country}</p>{data[1].defaultAddressId !== a.id ? <button disabled={busy} className="text-button" onClick={() => makeDefault(a.id)}>Set as default</button> : null}</div></li>)}</ul> : !error ? <p role="status">Loading addresses…</p> : null}
    <p className="hint">Default address is preselected for new complaints.</p>{error || failure ? <p role="alert" className="error">{failure || error}</p> : null}
    {editing ? <AddressDialog address={editing === true ? null : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} /> : null}</section>;
}

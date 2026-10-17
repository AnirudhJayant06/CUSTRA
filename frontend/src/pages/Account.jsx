import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api } from '../api/client.js';
import useLoad from '../lib/useLoad.js';
import Icon from '../components/Icon.jsx';
export default function Account() {
  const { data, error } = useLoad(['/api/profile']);
  const [draft, setDraft] = useState(null);
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  const { logout, loggingOut } = useOutletContext();
  useEffect(() => { if (data) setDraft(data[0]); }, [data]);
  async function save(e) {
    e.preventDefault(); if (busy) return;
    setBusy(true); setFailure(''); setMessage('');
    try { const saved = await api('/api/profile', { method: 'PATCH', body: { name: draft.name.trim(), phone: draft.phone.trim(), email: draft.email.trim() } }); setDraft(saved); setMessage('Profile saved.'); }
    catch (e) { setFailure(e.message); } finally { setBusy(false); }
  }
  return <section className="page"><Link className="back-link" to="/">← Home</Link><h1>Profile</h1>{draft ? <form onSubmit={save}><fieldset disabled={busy}>{[['name', 'Full name', 'text'], ['phone', 'Phone number', 'tel'], ['email', 'Email', 'email']].map(([key, label, type]) => <div key={key}><label htmlFor={`profile-${key}`}>{label}</label><input id={`profile-${key}`} value={draft[key]} type={type} required maxLength={key === 'email' ? 254 : key === 'phone' ? 40 : 120} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} /></div>)}<p className="hint">Used to register your complaints.</p><button className="primary full">{busy ? 'Saving…' : 'Save changes'}</button></fieldset></form> : !error ? <p role="status">Loading profile…</p> : null}
    {message ? <p role="status">{message}</p> : null}{error || failure ? <p role="alert" className="error">{failure || error}</p> : null}
    <Link className="slim-row account-row" to="/account/addresses"><Icon name="pin" /><span>Saved addresses</span><Icon name="arrow" /></Link><button className="text-button action-line" onClick={logout} disabled={loggingOut}><Icon name="logout" />{loggingOut ? 'Logging out…' : 'Log out'}</button>
  </section>;
}

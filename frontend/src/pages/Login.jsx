import { useState } from 'react';
import { api } from '../api/client.js';
import Brand from '../components/Brand.jsx';
export default function Login({ onSuccess }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  async function submit(e) { e.preventDefault(); if (pending) return; const fields = new FormData(e.currentTarget); setPending(true); setError(''); try { await api('/api/auth/login', { method: 'POST', body: { username: fields.get('username'), password: fields.get('password') } }); onSuccess(); } catch (failure) { setError(failure.message); } finally { setPending(false); } }
  return <main className="login-page"><Brand /><h1>Welcome to Custra</h1><p>Save your details once. Register complaints with less effort.</p><form onSubmit={submit}><fieldset disabled={pending}><label htmlFor="username">Username</label><input id="username" name="username" required autoComplete="username" /><label htmlFor="password">Password</label><input id="password" name="password" type="password" required autoComplete="current-password" /><button className="primary full">{pending ? 'Signing in…' : 'Sign in'}</button></fieldset>{error ? <p role="alert" className="error">{error}</p> : null}</form><p className="demo-note">Shared demo workspace · Fictional data only.<br />Business support and technician visits are simulated.</p></main>;
}

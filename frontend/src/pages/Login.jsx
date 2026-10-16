import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api/client.js';

export default function Login({ onSuccess }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function submit(event) {
    event.preventDefault();
    if (pending) return;
    const fields = new FormData(event.currentTarget);
    setPending(true);
    setError('');
    try {
      await api('/api/auth/login', { method: 'POST', body: {
        username: String(fields.get('username') || ''),
        password: String(fields.get('password') || ''),
      } });
      onSuccess();
      navigate('/', { replace: true });
    } catch (failure) {
      setError(failure.message || 'Could not sign in. Try again.');
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="shell">
      <header className="brand"><span className="brand-mark" aria-hidden="true">c.</span><span>custra<span className="brand-dot">.</span></span><span className="demo-label">DEMO</span></header>
      <main>
        <section className="intro" aria-labelledby="login-title">
          <p className="eyebrow">WELCOME TO CUSTRA</p>
          <h1 id="login-title">Sign in to the demo.</h1>
          <p className="intro-copy">This is a shared demo workspace. Use fictional information only.</p>
        </section>
        <section className="form-card" aria-label="Demo sign in">
          <form onSubmit={submit}>
            <fieldset disabled={pending}>
              <label htmlFor="username">Username</label>
              <input id="username" name="username" autoComplete="username" required />
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" autoComplete="current-password" required />
              <button className="submit" type="submit">{pending ? 'Signing in…' : 'Sign in'}</button>
            </fieldset>
            {error ? <p className="error response" role="alert">{error}</p> : null}
          </form>
        </section>
      </main>
    </div>
  );
}

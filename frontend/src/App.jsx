import { useEffect, useState } from 'react';
import { BrowserRouter, Link, Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom';

import { api } from './api/client.js';
import Login from './pages/Login.jsx';
import Account from './pages/Account.jsx';
import Vault from './pages/Vault.jsx';
import ProductDetail from './pages/ProductDetail.jsx';
import Complaints from './pages/Complaints.jsx';
import NewComplaint from './pages/NewComplaint.jsx';
import CaseDetail from './pages/CaseDetail.jsx';

function ProtectedLayout({ authenticated, onLogout }) {
  const navigate = useNavigate();
  const [logoutError, setLogoutError] = useState('');
  const [loggingOut, setLoggingOut] = useState(false);
  if (!authenticated) return <Navigate to="/login" replace />;

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    setLogoutError('');
    try {
      await api('/api/auth/logout', { method: 'POST' });
      onLogout();
      navigate('/login', { replace: true });
    } catch (failure) {
      if (failure.status !== 401) setLogoutError('Could not sign out. Check your connection and try again.');
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="shell">
      <header className="brand">
        <span className="brand-mark" aria-hidden="true">c.</span>
        <span>custra<span className="brand-dot">.</span></span>
        <span className="demo-label">DEMO</span>
      </header>
      <nav className="site-nav" aria-label="Main navigation">
        <Link to="/vault">Vault</Link>
        <Link to="/complaints">Complaints</Link>
        <Link to="/account">Account settings</Link>
        <button type="button" className="secondary" onClick={logout} disabled={loggingOut}>Sign out</button>
      </nav>
      {logoutError ? <p className="error" role="alert">{logoutError}</p> : null}
      <main className="app-main"><Outlet /></main>
    </div>
  );
}

function AppRoutes() {
  const [authenticated, setAuthenticated] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    api('/api/auth/session', { signal: controller.signal })
      .then(() => setAuthenticated(true))
      .catch((error) => { if (error.name !== 'AbortError') setAuthenticated(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const expired = () => setAuthenticated(false);
    window.addEventListener('custra:session-expired', expired);
    return () => window.removeEventListener('custra:session-expired', expired);
  }, []);

  if (authenticated === null) return <p className="shell" role="status">Checking your session…</p>;

  return (
    <Routes>
      <Route path="/login" element={authenticated
        ? <Navigate to="/vault" replace />
        : <Login onSuccess={() => setAuthenticated(true)} />} />
      <Route element={<ProtectedLayout authenticated={authenticated} onLogout={() => setAuthenticated(false)} />}>
        <Route path="/" element={<Navigate to="/vault" replace />} />
        <Route path="/vault" element={<Vault />} />
        <Route path="/account" element={<Account />} />
        <Route path="/products/:productId" element={<ProductDetail />} />
        <Route path="/complaints" element={<Complaints />} />
        <Route path="/complaints/new" element={<NewComplaint />} />
        <Route path="/complaints/:caseId" element={<CaseDetail />} />
      </Route>
      <Route path="*" element={<Navigate to={authenticated ? '/vault' : '/login'} replace />} />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}

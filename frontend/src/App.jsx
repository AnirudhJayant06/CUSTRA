import { useEffect, useState } from 'react';
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom';
import { api } from './api/client.js';
import Brand from './components/Brand.jsx';
import Icon from './components/Icon.jsx';
import Login from './pages/Login.jsx';
import Home from './pages/Home.jsx';
import Account from './pages/Account.jsx';
import Addresses from './pages/Addresses.jsx';
import Vault from './pages/Vault.jsx';
import ProductEditor from './pages/ProductEditor.jsx';
import ProductDetail from './pages/ProductDetail.jsx';
import Complaints from './pages/Complaints.jsx';
import NewComplaint from './pages/NewComplaint.jsx';
import CaseDetail from './pages/CaseDetail.jsx';
function ProtectedLayout({ authenticated, onLogout }) {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [loggingOut, setLoggingOut] = useState(false);
  if (!authenticated) return <Navigate to="/login" replace />;
  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true); setError('');
    try { await api('/api/auth/logout', { method: 'POST' }); onLogout(); navigate('/login', { replace: true }); }
    catch (failure) { if (failure.status !== 401) setError('Could not sign out. Check your connection and try again.'); }
    finally { setLoggingOut(false); }
  }
  return <div className="shell"><header className="app-header"><Link to="/" aria-label="Custra home"><Brand /></Link>
    <details className="profile-menu"><summary aria-label="Profile menu"><Icon name="user" /></summary><div className="menu-items" onClick={(e) => { if (e.target.closest('a')) e.currentTarget.parentElement.removeAttribute('open'); }}>
      <Link to="/account">Profile</Link><Link to="/account/addresses">Addresses</Link><Link to="/complaints?view=past">Past complaints</Link><button type="button" disabled={loggingOut} onClick={logout}>Log out</button>
    </div></details></header>
    {error ? <p className="error" role="alert">{error}</p> : null}
    <main className="app-main"><Outlet context={{ logout, loggingOut }} /></main>
    <nav className="bottom-nav" aria-label="Main navigation"><NavLink end to="/"><Icon name="home" />Home</NavLink><NavLink to="/vault"><Icon name="products" />Products</NavLink><NavLink to="/complaints"><Icon name="complaints" />Complaints</NavLink></nav>
  </div>;
}
function AppRoutes() {
  const [authenticated, setAuthenticated] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    api('/api/auth/session', { signal: controller.signal }).then(() => setAuthenticated(true)).catch((e) => { if (e.name !== 'AbortError') setAuthenticated(false); });
    return () => controller.abort();
  }, []);
  useEffect(() => { const expired = () => setAuthenticated(false); window.addEventListener('custra:session-expired', expired); return () => window.removeEventListener('custra:session-expired', expired); }, []);
  if (authenticated === null) return <p className="shell" role="status">Checking your session…</p>;
  return <Routes><Route path="/login" element={authenticated ? <Navigate to="/" replace /> : <Login onSuccess={() => setAuthenticated(true)} />} />
    <Route element={<ProtectedLayout authenticated={authenticated} onLogout={() => setAuthenticated(false)} />}>
      <Route index element={<Home />} /><Route path="/vault" element={<Vault />} /><Route path="/products/new" element={<ProductEditor />} />
      <Route path="/account" element={<Account />} /><Route path="/account/addresses" element={<Addresses />} /><Route path="/products/:productId" element={<ProductDetail />} />
      <Route path="/complaints" element={<Complaints />} /><Route path="/complaints/new" element={<NewComplaint />} /><Route path="/complaints/:caseId" element={<CaseDetail />} />
    </Route><Route path="*" element={<Navigate to={authenticated ? '/' : '/login'} replace />} /></Routes>;
}
export default function App() { return <BrowserRouter><AppRoutes /></BrowserRouter>; }

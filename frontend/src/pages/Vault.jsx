import { useState } from 'react';
import { Link } from 'react-router-dom';
import useLoad from '../lib/useLoad.js';
import { sortCases, caseName, dateLabel } from '../lib/domain.js';
import Icon from '../components/Icon.jsx';
export default function Vault() {
  const { data, error } = useLoad(['/api/products', '/api/catalog', '/api/complaints']);
  const [query, setQuery] = useState('');
  const [products = [], catalog = { categories: [] }, complaints = []] = data || [];
  const active = sortCases(complaints).filter((row) => row.status !== 'CLOSED');
  const categories = new Map(catalog.categories.map((row) => [row.id, row]));
  const needle = query.trim().toLocaleLowerCase();
  const visible = products.filter((p) => `${p.displayName} ${categories.get(p.categoryId)?.name} ${categories.get(p.categoryId)?.brands.find((b) => b.id === p.brandId)?.name}`.toLocaleLowerCase().includes(needle));
  return <section className="page"><h1>Products</h1><label className="search-field"><Icon name="search" /><input type="search" aria-label="Search products" placeholder="Search products or brands" value={query} onChange={(e) => setQuery(e.target.value)} /></label>
    {error ? <p role="alert" className="error">{error}</p> : null}
    {!data && !error ? <p role="status">Loading products…</p> : null}
    <div className="product-grid"><Link to="/products/new" className="product-tile add-tile"><span className="tile-icon"><Icon name="plus" size={34} /></span><span>Add product</span></Link>
      {visible.map((p) => <Link key={p.id} aria-label={p.displayName} to={`/products/${p.id}`} className="product-tile"><span className="tile-icon"><Icon name={p.categoryId} size={40} /></span><span>{p.displayName}</span>{active.some((c) => c.productId === p.id) ? <small className="tile-state">Active case</small> : null}</Link>)}
    </div>
    {data && !visible.length ? <p className="hint">{query ? 'No matching products.' : 'Add your first product to keep its details in one place.'}</p> : null}
    {active[0] ? <section className="resume-section"><h2>Continue where you left off</h2><Link className="resume-card" to={`/complaints/${active[0].id}`}><Icon name={active[0].factsSnapshot?.product?.categoryId} size={38} /><span><strong>{caseName(active[0])}</strong><small>{active[0].issueSummary}</small><small>{active[0].reference || 'Registration in progress'} · {dateLabel(active[0].createdAt)}</small><span className="text-action">View complaint →</span></span><Icon name="arrow" /></Link></section> : null}
  </section>;
}

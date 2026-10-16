import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../api/client.js';
import ProductForm from '../components/ProductForm.jsx';

export default function Vault() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api('/api/products', { signal: controller.signal }),
      api('/api/catalog', { signal: controller.signal }),
    ]).then(([saved, catalog]) => {
      setProducts(saved);
      setCategories(catalog.categories);
    }).catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); });
    return () => controller.abort();
  }, []);

  return (
    <div className="content-stack">
      <section className="form-card">
        <h1>Product Vault</h1>
        <p className="hint">Save basic product details manually. Documents are optional.</p>
        {products.length ? <ul className="record-list">{products.map((product) =>
          <li key={product.id}><Link to={`/products/${product.id}`}>{product.displayName}</Link></li>)}</ul>
          : <p>No products saved yet.</p>}
      </section>
      <section className="form-card">
        <h2>Add product</h2>
        {categories.length ? <ProductForm categories={categories} onSaved={(product) => {
          setProducts((current) => [...current, product]);
          navigate(`/products/${product.id}`);
        }} /> : <p role="status">Loading catalog…</p>}
        {error ? <p className="error" role="alert">{error}</p> : null}
      </section>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api, upload } from '../api/client.js';
import ProductForm from '../components/ProductForm.jsx';
import Complaints from './Complaints.jsx';

export default function ProductDetail() {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);
  const [centers, setCenters] = useState([]);
  const [categories, setCategories] = useState([]);
  const [editing, setEditing] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [tab, setTab] = useState('general');
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api(`/api/products/${encodeURIComponent(productId)}`, { signal: controller.signal }),
      api('/api/service-centers', { signal: controller.signal }),
      api('/api/catalog', { signal: controller.signal }),
      api(`/api/products/${encodeURIComponent(productId)}/documents`, { signal: controller.signal }),
    ]).then(([saved, listings, catalog, savedDocuments]) => {
      setProduct(saved);
      setCenters(listings.centers);
      setCategories(catalog.categories);
      setDocuments(savedDocuments);
    }).catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); });
    return () => controller.abort();
  }, [productId]);

  if (error && !product) return <p className="error" role="alert">{error}</p>;
  if (!product) return <p role="status">Loading product…</p>;

  const category = categories.find((item) => item.id === product.categoryId);
  const brand = category?.brands.find((item) => item.id === product.brandId);

  async function saveDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get('file');
    if (!(file instanceof File) || !file.name) return;
    setUploading(true);
    setError('');
    try {
      const data = new FormData();
      data.append('file', file);
      const saved = await upload(`/api/products/${encodeURIComponent(productId)}/documents`, data);
      setDocuments((current) => [...current, saved]);
      form.reset();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="content-stack">
      <section className="form-card">
        <Link to="/vault">← Vault</Link>
        <h1>{product.displayName}</h1>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="tabs" role="tablist" aria-label="Product details">
          <button type="button" role="tab" aria-selected={tab === 'general'} onClick={() => setTab('general')}>General info</button>
          <button type="button" role="tab" aria-selected={tab === 'complaints'} onClick={() => setTab('complaints')}>Complaints</button>
        </div>
        {tab === 'general' ? <div>
          <dl><dt>Brand</dt><dd>{brand?.name || product.brandId}</dd><dt>Category</dt><dd>{category?.name || product.categoryId}</dd>
            {product.purchaseDate ? <><dt>Purchase date</dt><dd>{product.purchaseDate}</dd></> : null}
            {product.warrantyExpiry ? <><dt>Entered warranty expiry</dt><dd>{product.warrantyExpiry}</dd></> : null}</dl>
          <button className="secondary record-action" type="button" onClick={() => setEditing((current) => !current)}>
            {editing ? 'Cancel edit' : 'Edit product'}
          </button>
          {editing ? <ProductForm categories={categories} product={product} onSaved={(saved) => {
            setProduct(saved);
            setEditing(false);
          }} /> : null}
          <h2>Documents</h2>
          <p className="hint">Optional storage for PDF, JPEG or PNG files. Files are not analyzed by the agent.</p>
          <form onSubmit={saveDocument}>
            <label htmlFor="product-document">Choose a document</label>
            <input id="product-document" name="file" type="file" required accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" />
            <button className="secondary record-action" type="submit" disabled={uploading}>{uploading ? 'Uploading…' : 'Upload document'}</button>
          </form>
          {documents.length ? <ul className="record-list">{documents.map((document) => {
            const contentUrl = `/api/documents/${encodeURIComponent(document.id)}/content`;
            return <li key={document.id}>
              <a href={contentUrl} target="_blank" rel="noopener noreferrer">{document.originalName}</a>
              {document.mediaType.startsWith('image/') ? <img className="document-preview" src={contentUrl} alt={`Stored ${document.originalName}`} /> : null}
            </li>;
          })}</ul> : <p>No documents saved for this product.</p>}
          <h2>Mock service centers</h2>
          <p className="hint">Fictional demo listings. No real appointment or contact is available here.</p>
          <ul className="record-list">{centers.map((center) => <li key={center.id}>
            <strong>{center.name}</strong> · Demo<br />{center.address}</li>)}</ul>
        </div> : <Complaints productId={productId} />}
      </section>
    </div>
  );
}

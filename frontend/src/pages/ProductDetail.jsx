import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import useLoad from '../lib/useLoad.js';
import { dateLabel, warrantyStatus, sortCases } from '../lib/domain.js';
import Icon from '../components/Icon.jsx';
import ComplaintRow from '../components/ComplaintRow.jsx';
import ProductForm from '../components/ProductForm.jsx';
import Modal from '../components/Modal.jsx';
import DocumentUpload from '../components/DocumentUpload.jsx';
export default function ProductDetail() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const { data, error, reload } = useLoad([`/api/products/${productId}`, '/api/catalog', `/api/products/${productId}/documents`, `/api/complaints?productId=${productId}`]);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  if (!data) return <p role={error ? 'alert' : 'status'} className={error ? 'error' : ''}>{error || 'Loading product…'}</p>;
  const [product, catalog, documents, cases] = data;
  const category = catalog.categories.find((c) => c.id === product.categoryId);
  const brand = category?.brands.find((b) => b.id === product.brandId);
  const current = sortCases(cases).filter((c) => c.status !== 'CLOSED');
  const past = sortCases(cases).filter((c) => c.status === 'CLOSED');
  async function deleteProduct() {
    if (deleting) return;
    setDeleting(true); setDeleteError('');
    try {
      await api(`/api/products/${encodeURIComponent(productId)}`, { method: 'DELETE' });
      navigate('/vault', { replace: true });
    } catch (failure) { setDeleteError(failure.message); }
    finally { setDeleting(false); }
  }
  return <section className={editing ? 'page compact-product-page' : 'page'}><div className="section-heading"><Link className="back-link" to="/vault">← Products</Link><button className="text-button" onClick={() => setEditing(!editing)}>{editing ? 'Cancel edit' : 'Edit product'}</button></div>
    {editing ? <><h1>Edit product</h1><ProductForm key={product.updatedAt || product.id} categories={catalog.categories} models={catalog.models} product={product} onSaved={() => { setEditing(false); reload(); }} /></> : <>
      <div className="product-identity"><span className="product-icon large"><Icon name={product.categoryId} size={60} /></span><div><h1>{product.displayName}</h1><p>{brand?.name || product.brandId} · {category?.name || product.categoryId}</p><span className="status">{warrantyStatus(product)}</span><p className="hint">Based on your saved details.</p></div></div>
      {current.length ? <section className="form-section"><h2>Current complaint{current.length > 1 ? 's' : ''}</h2><ul className="plain-list">{current.map((row) => <ComplaintRow key={row.id} row={row} />)}</ul></section> : null}
      <Link className={current.length ? 'text-action action-line' : 'primary full'} to={`/complaints/new?productId=${productId}`}><Icon name="plus" />{current.length ? 'Report another issue' : 'Register a complaint'}</Link>
      <section className="form-section"><h2>Product details</h2><dl className="detail-list"><div><dt>Model</dt><dd>{product.modelNumber || 'Not recorded'}</dd></div><div><dt>Purchase date</dt><dd>{dateLabel(product.purchaseDate)}</dd></div><div><dt>Warranty period</dt><dd>{product.warrantyMonths ? `${product.warrantyMonths} months` : 'Not recorded'}</dd></div><div><dt>Warranty until</dt><dd>{dateLabel(product.warrantyExpiry)}</dd></div></dl></section>
      <section className="form-section"><h2>Documents</h2>{documents.length ? <ul className="plain-list">{documents.map((doc) => <li className="document-row" key={doc.id}><Icon name="file" /><a href={`/api/documents/${doc.id}/content`} target="_blank" rel="noopener noreferrer">{doc.originalName}</a>{doc.processingStatus ? <span className="hint">{doc.reviewRequired ? 'Some details need confirmation' : ({ searchable: 'Ready for questions', failed: 'Stored — enter details manually if needed', processing: 'Preparing for questions…', not_indexable: 'Stored — no searchable details' })[doc.processingStatus] || 'Stored'}</span> : null}{doc.description ? <span className="hint">{doc.description}</span> : null}{doc.mediaType.startsWith('image/') ? <img className="document-preview" src={`/api/documents/${doc.id}/content`} alt={`Stored ${doc.originalName}`} /> : null}</li>)}</ul> : <p className="hint">No documents yet.</p>}
        <DocumentUpload path={`/api/products/${encodeURIComponent(productId)}/documents`} onUploaded={reload} />
      </section><details className="form-section"><summary>Past complaints ({past.length})</summary><ul className="plain-list">{past.map((row) => <ComplaintRow key={row.id} row={row} />)}</ul>{!past.length ? <p className="hint">No past complaints.</p> : null}</details>
      <button type="button" className="text-button danger-action" onClick={() => { setDeleteError(''); setShowDelete(true); }}>Delete product</button>
    </>}{error ? <p className="error" role="alert">{error}</p> : null}
    {showDelete ? <Modal title="Delete product?" onClose={() => setShowDelete(false)} busy={deleting}>
      <p>Remove {product.displayName} from your products and close any active complaints for it? Complaint history will remain available.</p>
      {deleteError ? <p className="error" role="alert">{deleteError}</p> : null}
      <div className="dialog-actions"><button className="secondary" disabled={deleting} onClick={() => setShowDelete(false)}>Cancel</button><button className="danger-button" disabled={deleting} onClick={deleteProduct}>{deleting ? 'Deleting…' : 'Delete product'}</button></div>
    </Modal> : null}</section>;
}

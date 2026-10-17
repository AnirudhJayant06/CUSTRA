import { useRef, useState } from 'react';
import { api, upload } from '../api/client.js';
import ModelPicker from './ModelPicker.jsx';
import AttachmentPicker from './AttachmentPicker.jsx';
const EMPTY_MODELS = [];
export default function ProductForm({ categories, models = EMPTY_MODELS, onSaved, product = null }) {
  const [categoryId, setCategory] = useState(product?.categoryId || '');
  const [brandId, setBrand] = useState(product?.brandId || '');
  const [nickname, setNickname] = useState(product?.nickname ?? product?.displayName ?? '');
  const [model, setModel] = useState(product?.modelNumber || '');
  const [customModel, setCustom] = useState(Boolean(product?.modelNumber && !models.some((m) => m.categoryId === product.categoryId && m.brandId === product.brandId && m.number === product.modelNumber)));
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [warrantyUnit, setUnit] = useState('months');
  const [duration, setDuration] = useState(String(product?.warrantyMonths || ''));
  const created = useRef(null);
  const category = categories.find((c) => c.id === categoryId);
  const brand = category?.brands.find((b) => b.id === brandId);
  const options = models.filter((m) => m.categoryId === categoryId && m.brandId === brandId);
  function clearModel() { setModel(''); setCustom(false); }
  function changeUnit(next) {
    // The selector changes the unit of the entered amount: 2 + Years = 24 months.
    setUnit(next);
  }
  async function submit(event) {
    event.preventDefault(); if (pending) return;
    const fields = new FormData(event.currentTarget);
    const months = duration ? Number(duration) * (warrantyUnit === 'years' ? 12 : 1) : null;
    if (months !== null && (!Number.isInteger(months) || months < 1 || months > 120)) { setError('Enter a warranty between 1 and 120 months (up to 10 years).'); return; }
    const body = { categoryId, brandId, nickname: nickname.trim(), modelNumber: model.trim() || null, purchaseDate: fields.get('purchaseDate') || null, warrantyMonths: months };
    setPending(true); setError('');
    try {
      const id = product?.id || created.current?.id;
      const saved = await api(id ? `/api/products/${encodeURIComponent(id)}` : '/api/products', { method: id ? 'PATCH' : 'POST', body });
      created.current = saved;
      if (file) { const data = new FormData(); data.append('file', file); await upload(`/api/products/${saved.id}/documents`, data); }
      onSaved(saved);
    } catch (failure) { setError(`${created.current && !product ? 'Product saved. ' : ''}${failure.message}${created.current && !product ? ' Retry to finish without creating another product.' : ''}`); }
    finally { setPending(false); }
  }
  return <form className="compact-product-form" onSubmit={submit}><fieldset disabled={pending}>
    <div className="identity-columns"><div><label htmlFor="category">Product type</label><select id="category" required value={categoryId} onChange={(e) => { setCategory(e.target.value); setBrand(''); clearModel(); }}><option value="">Choose type</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
      <div><label htmlFor="brand">Brand</label><select id="brand" required disabled={!category} value={brandId} onChange={(e) => { setBrand(e.target.value); clearModel(); }}><option value="">Choose brand</option>{category?.brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div></div>
    <ModelPicker options={options} value={model} custom={customModel} disabled={!brand} onChange={(value, custom) => { setModel(value); setCustom(custom); }} />
    <label htmlFor="nickname">Nickname <span className="optional">(optional)</span></label><input id="nickname" name="nickname" value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={120} placeholder="e.g. Living room TV" /><p className="hint nickname-hint">Leave blank to use {brand && category ? `${brand.name} ${category.name}` : 'Brand + product type'}.</p>
    <details className="optional-section" open={Boolean(product?.purchaseDate || product?.warrantyMonths)}><summary>Purchase &amp; warranty <span className="optional">optional</span></summary><div className="optional-content"><label htmlFor="purchase-date">Purchase date</label><input id="purchase-date" name="purchaseDate" type="date" defaultValue={product?.purchaseDate || ''} />
      <label htmlFor="warranty-duration">Warranty period</label><div className="warranty-input"><input id="warranty-duration" type="number" min={warrantyUnit === 'years' ? 1 / 12 : 1} max={warrantyUnit === 'years' ? 10 : 120} step="any" value={duration} onChange={(e) => setDuration(e.target.value)} /><select aria-label="Warranty unit" value={warrantyUnit} onChange={(e) => changeUnit(e.target.value)}><option value="months">Months</option><option value="years">Years</option></select></div><p className="hint">Based on your entries; coverage is not verified.</p></div></details>
    <AttachmentPicker file={file} onChange={setFile} disabled={pending} />
    {error ? <p className="error" role="alert">{error}</p> : null}<div className="product-save"><button className="primary full" type="submit">{pending ? 'Saving…' : product ? 'Save changes' : created.current ? 'Retry save' : 'Save product'}</button></div>
  </fieldset></form>;
}

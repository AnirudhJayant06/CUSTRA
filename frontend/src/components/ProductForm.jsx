import { useState } from 'react';

import { api } from '../api/client.js';

export default function ProductForm({ categories, onSaved, product = null }) {
  const initialCategory = categories.find((item) => item.id === product?.categoryId);
  const initialBrand = initialCategory?.brands.find((item) => item.id === product?.brandId);
  const [categoryName, setCategoryName] = useState(initialCategory?.name || '');
  const [brandName, setBrandName] = useState(initialBrand?.name || '');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const category = categories.find((item) => item.name.toLowerCase() === categoryName.trim().toLowerCase());
  const brand = category?.brands.find((item) => item.name.toLowerCase() === brandName.trim().toLowerCase());

  async function submit(event) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    if (!category || !brand) { setError('Choose a category and a brand from the suggestions.'); return; }
    const fields = new FormData(form);
    const body = {
      categoryId: category.id, brandId: brand.id,
      displayName: String(fields.get('displayName') || '').trim(),
      purchaseDate: fields.get('purchaseDate') || null,
      warrantyExpiry: fields.get('warrantyExpiry') || null,
    };
    setPending(true);
    setError('');
    try {
      const saved = await api(product ? `/api/products/${encodeURIComponent(product.id)}` : '/api/products', {
        method: product ? 'PATCH' : 'POST', body,
      });
      onSaved(saved);
      if (!product) {
        form.reset();
        setCategoryName('');
        setBrandName('');
      }
    } catch (failure) {
      setError(failure.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <fieldset disabled={pending}>
        <label htmlFor="category">Product category</label>
        <input id="category" list="categories" value={categoryName} required
          onChange={(event) => { setCategoryName(event.target.value); setBrandName(''); }} placeholder="Search categories" />
        <datalist id="categories">{categories.map((item) => <option value={item.name} key={item.id} />)}</datalist>
        <label htmlFor="brand">Brand</label>
        <input id="brand" list="brands" value={brandName} required disabled={!category}
          onChange={(event) => setBrandName(event.target.value)} placeholder="Search brands" />
        <datalist id="brands">{category?.brands.map((item) => <option value={item.name} key={item.id} />)}</datalist>
        <label htmlFor="display-name">Model or product name</label>
        <input id="display-name" name="displayName" required maxLength={120} placeholder="Example Model" defaultValue={product?.displayName || ''} />
        <label htmlFor="purchase-date">Purchase date (optional)</label>
        <input id="purchase-date" name="purchaseDate" type="date" defaultValue={product?.purchaseDate || ''} />
        <label htmlFor="warranty-expiry">Warranty expiry (optional)</label>
        <input id="warranty-expiry" name="warrantyExpiry" type="date" defaultValue={product?.warrantyExpiry || ''} />
        {error ? <p className="error" role="alert">{error}</p> : null}
        <button className="submit" type="submit">{pending ? 'Saving…' : product ? 'Update product' : 'Save product'}</button>
      </fieldset>
    </form>
  );
}

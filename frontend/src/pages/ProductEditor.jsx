import { Link, useNavigate } from 'react-router-dom';
import Icon from '../components/Icon.jsx';
import useLoad from '../lib/useLoad.js';
import ProductForm from '../components/ProductForm.jsx';
export default function ProductEditor() {
  const { data, error } = useLoad(['/api/catalog']);
  const navigate = useNavigate();
  return <section className="page compact-product-page"><div className="compact-title"><Link className="icon-button" aria-label="Back to products" to="/vault"><Icon name="back" /></Link><h1>Add product</h1></div>{error ? <p role="alert" className="error">{error}</p> : data ? <ProductForm categories={data[0].categories} models={data[0].models} onSaved={(p) => navigate(`/products/${p.id}`)} /> : <p role="status">Loading catalog…</p>}</section>;
}

import { useSearchParams, Link } from 'react-router-dom';
import useLoad from '../lib/useLoad.js';
import { sortCases } from '../lib/domain.js';
import ComplaintRow from '../components/ComplaintRow.jsx';
export default function Complaints({ productId }) {
  const [params, setParams] = useSearchParams();
  const past = params.get('view') === 'past';
  const { data, error } = useLoad([`/api/complaints${productId ? `?productId=${productId}` : ''}`]);
  const rows = sortCases(data?.[0] || []).filter((c) => (c.status === 'CLOSED') === past);
  return <section className="page"><div className="section-heading"><h1>Complaints</h1><Link to={`/complaints/new${productId ? `?productId=${productId}` : ''}`}>+ Register complaint</Link></div><div className="segments" role="group" aria-label="Complaint filter"><button className={!past ? 'selected' : ''} aria-pressed={!past} onClick={() => setParams({})}>Active</button><button className={past ? 'selected' : ''} aria-pressed={past} onClick={() => setParams({ view: 'past' })}>Past</button></div>
    {error ? <p role="alert" className="error">{error}</p> : !data ? <p role="status">Loading complaints…</p> : rows.length ? <ul className="plain-list">{rows.map((row) => <ComplaintRow row={row} key={row.id} />)}</ul> : <div className="empty-state"><h2>{past ? 'No past complaints' : 'No active complaints'}</h2><p>{past ? 'Resolved complaints will appear here after your confirmation.' : 'Register a complaint and Custra will use your saved details.'}</p></div>}
    <p className="demo-note">Demo support · Simulated technician visits</p></section>;
}

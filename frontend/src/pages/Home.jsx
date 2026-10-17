import { Link } from 'react-router-dom';
import useLoad from '../lib/useLoad.js';
import { sortCases, formatSlot, caseName } from '../lib/domain.js';
import ComplaintRow from '../components/ComplaintRow.jsx';
import Icon from '../components/Icon.jsx';
export default function Home() {
  const { data, error } = useLoad(['/api/complaints']);
  const rows = sortCases(data?.[0] || []);
  const active = rows.filter((row) => row.status !== 'CLOSED');
  const next = rows.filter((row) => row.status === 'BOOKED' && new Date(row.appointment?.start) > new Date()).sort((a, b) => a.appointment.start.localeCompare(b.appointment.start))[0];
  return <section className="page home-page"><Link className="primary full" to="/complaints/new"><Icon name="plus" />Register a complaint</Link>
    <div className="section-heading"><h1>Active complaints</h1><Link to="/complaints">View all</Link></div>
    {error ? <p className="error" role="alert">{error}</p> : !data ? <p role="status">Loading your complaints…</p> : active.length ? <ul className="plain-list">{active.slice(0, 2).map((row) => <ComplaintRow row={row} key={row.id} />)}</ul> : <div className="empty-state"><Icon name="complaints" size={36} /><h2>No active complaints</h2><p>Something not working? Choose a saved product and tell us what went wrong.</p><Link to="/vault">View your products →</Link></div>}
    {next ? <section><h2>Next technician visit</h2><Link className="visit-row" to={`/complaints/${next.id}`}><Icon name="calendar" size={30} /><span><strong>{formatSlot(next.appointment.start)}</strong><small>{caseName(next)}</small></span><Icon name="arrow" /></Link></section> : null}
    <p className="demo-note">Demo support · Simulated technician visits</p>
  </section>;
}

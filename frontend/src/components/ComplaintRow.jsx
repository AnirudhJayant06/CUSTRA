import { Link } from 'react-router-dom';
import Icon from './Icon.jsx';
import { caseAction, caseName, dateLabel, formatSlot, statusLabel } from '../lib/domain.js';
export default function ComplaintRow({ row }) {
  return <li className="complaint-row"><span className="product-icon"><Icon name={row.factsSnapshot?.product?.categoryId} size={34} /></span><div className="row-content">
    <h3>{caseName(row)}</h3><p>{row.issueSummary}</p><span className={`status status-${row.status.toLowerCase()}`}>{statusLabel(row.status, row.closureReason)}</span>
    <p className="metadata">{row.reference || `Case ${row.id.slice(0, 8)}`} · {dateLabel(row.createdAt)}</p>
    {row.appointment && row.closureReason !== 'product_deleted' ? <p className="metadata"><Icon name="calendar" size={15} /> Technician visit · {formatSlot(row.appointment.start)}</p> : null}
    <Link className="text-action" to={`/complaints/${row.id}`}>{caseAction(row)} <span aria-hidden="true">→</span></Link>
  </div></li>;
}

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import useCaseProgress from '../hooks/useCaseProgress.js';
import ConversationTimeline from '../components/ConversationTimeline.jsx';
import AppointmentDialog, { formatSlot } from '../components/AppointmentDialog.jsx';
import CasePhotos from '../components/CasePhotos.jsx';
import { statusLabel, caseName } from '../lib/domain.js';
import { api } from '../api/client.js';
import Icon from '../components/Icon.jsx';

export default function CaseDetail() {
  const { caseId } = useParams();
  const { complaint, events, pending, error, retry, setComplaint } = useCaseProgress(caseId);
  const [showAppointment, setShowAppointment] = useState(false);
  const [resolved, setResolved] = useState(false);
  const [closing, setClosing] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    if (complaint?.status === 'AWAITING_APPOINTMENT') setShowAppointment(true);
  }, [complaint?.status]);

  async function confirmResolution() {
    if (!resolved || closing) return;
    setClosing(true);
    setActionError('');
    try {
      setComplaint(await api(`/api/complaints/${encodeURIComponent(caseId)}/confirm-resolution`, {
        method: 'POST', body: { confirmed: true },
      }));
      retry();
    } catch (failure) {
      setActionError(failure.message);
    } finally {
      setClosing(false);
    }
  }

  if (!complaint) return error ? <p className="error" role="alert">{error}</p> : <p role="status">Loading complaint…</p>;
  const closed = complaint.status === 'CLOSED';
  const newComplaintHref = complaint.closureReason === 'product_deleted' ? '/complaints/new' : `/complaints/new?productId=${encodeURIComponent(complaint.productId)}`;
  return <section className="page case-page">
    <Link className="back-link" to="/complaints">← Complaints</Link>
    <h1>{caseName(complaint)}</h1>
    <p className={`status status-${complaint.status.toLowerCase()}`}>{statusLabel(complaint.status, complaint.closureReason)}</p>
    <p>{complaint.description}</p>
    <p className="hint">Custra answers using your saved details. Business support is simulated.</p>
    {complaint.reference ? <p className="response success">Complaint reference: <strong>{complaint.reference}</strong></p> : null}
    <ConversationTimeline events={events} pending={!closed && pending} closed={closed} />
    {!closed && (error || (complaint.status === 'ERROR' && complaint.recoveryPhase === 'advance')) ? <div>
      <p className="error" role="alert">{error || complaint.error?.message || 'The step could not finish.'}</p>
      <button className="secondary" type="button" onClick={retry} disabled={pending}>Retry saved step</button>
    </div> : null}
    {complaint.status === 'AWAITING_APPOINTMENT' || (complaint.status === 'ERROR' && complaint.recoveryPhase === 'book') ? <div className="response">
      <p>{complaint.recoveryPhase === 'book' ? 'Recover your pending technician visit confirmation.' : 'Registration is ready. Confirm your technician visit.'}</p>
      <button className="secondary" type="button" onClick={() => setShowAppointment(true)}>Confirm technician visit</button>
    </div> : null}
    {complaint.appointment && complaint.closureReason !== 'product_deleted' ? <div className="response success">
      <h2>Technician visit confirmed</h2>
      <p>{formatSlot(complaint.appointment.start)} IST</p>
      <p>Booking reference: {complaint.appointment.bookingReference}</p>
      {complaint.status === 'BOOKED' ? <div>
        <label className="checkbox-row"><input type="checkbox" checked={resolved} onChange={(event) => setResolved(event.target.checked)} /> The issue has been resolved.</label>
        <button type="button" className="secondary" disabled={!resolved || closing} onClick={confirmResolution}>Confirm issue resolved</button>
      </div> : <p>Closed after your confirmation.</p>}
    </div> : null}
    {actionError ? <p className="error" role="alert">{actionError}</p> : null}
    {closed ? <footer className="chat-closed-note" aria-label="Closed chat"><Icon name="lock" size={18} /><div><p>This chat is closed. You can start a new complaint if you need more help.</p><Link to={newComplaintHref}>Start a new complaint</Link></div></footer> : <CasePhotos key={caseId} caseId={caseId} />}
    {showAppointment && !closed ? <AppointmentDialog caseId={caseId} pendingSlotId={complaint.pendingSlotId} preferredSlotId={complaint.preferredSlotId}
      onClose={() => setShowAppointment(false)} onUpdated={(updated) => { setComplaint(updated); if (updated.status === 'BOOKED') retry(); }} /> : null}
  </section>;
}

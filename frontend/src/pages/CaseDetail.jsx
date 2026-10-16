import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import useCaseProgress from '../hooks/useCaseProgress.js';
import ConversationTimeline from '../components/ConversationTimeline.jsx';
import AppointmentDialog, { formatSlot } from '../components/AppointmentDialog.jsx';
import CasePhotos from '../components/CasePhotos.jsx';
import { api } from '../api/client.js';

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
  return <section className="form-card">
    <p className="eyebrow">SIMULATED BUSINESS SUPPORT</p>
    <h1>{complaint.issueSummary}</h1>
    <p>Status: {complaint.status.replaceAll('_', ' ')}</p>
    <p>{complaint.description}</p>
    <p className="hint">Your saved details are attached to this case. Registration and appointments are simulated.</p>
    {complaint.reference ? <p className="response success">Simulated complaint reference: <strong>{complaint.reference}</strong></p> : null}
    <ConversationTimeline events={events} pending={pending} />
    {error || (complaint.status === 'ERROR' && complaint.recoveryPhase === 'advance') ? <div>
      <p className="error" role="alert">{error || complaint.error?.message || 'The step could not finish.'}</p>
      <button className="secondary" type="button" onClick={retry} disabled={pending}>Retry saved step</button>
    </div> : null}
    {complaint.status === 'AWAITING_APPOINTMENT' || (complaint.status === 'ERROR' && complaint.recoveryPhase === 'book') ? <div className="response">
      <p>{complaint.recoveryPhase === 'book' ? 'Recover your pending appointment confirmation.' : 'Registration is ready. Choose your appointment to finish.'}</p>
      <button className="secondary" type="button" onClick={() => setShowAppointment(true)}>Choose appointment</button>
    </div> : null}
    {complaint.appointment ? <div className="response success">
      <h2>Simulated appointment confirmed</h2>
      <p>{formatSlot(complaint.appointment.start)} IST</p>
      <p>Booking reference: {complaint.appointment.bookingReference}</p>
      {complaint.status === 'BOOKED' ? <div>
        <label><input type="checkbox" checked={resolved} onChange={(event) => setResolved(event.target.checked)} /> The issue has been resolved.</label>
        <button type="button" className="secondary" disabled={!resolved || closing} onClick={confirmResolution}>Confirm issue resolved</button>
      </div> : <p>Closed after your confirmation.</p>}
    </div> : null}
    {actionError ? <p className="error" role="alert">{actionError}</p> : null}
    <CasePhotos key={caseId} caseId={caseId} />
    {showAppointment ? <AppointmentDialog caseId={caseId} pendingSlotId={complaint.pendingSlotId}
      onClose={() => setShowAppointment(false)} onUpdated={(updated) => { setComplaint(updated); if (updated.status === 'BOOKED') retry(); }} /> : null}
  </section>;
}

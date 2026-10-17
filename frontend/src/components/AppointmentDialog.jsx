import { useEffect, useRef, useState } from 'react';

import Modal from './Modal.jsx';
import { api } from '../api/client.js';

export const formatSlot = (value) => new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata',
}).format(new Date(value));

export default function AppointmentDialog({ caseId, pendingSlotId, preferredSlotId, onClose, onUpdated }) {
  const requestKey = useRef(crypto.randomUUID());
  const [slots, setSlots] = useState([]);
  const selectedId = pendingSlotId || preferredSlotId;
  const selected = slots.find((s) => s.id === selectedId) || (!selectedId ? slots[0] : null);
  const [loaded, setLoaded] = useState(false);
  const [locked, setLocked] = useState(Boolean(pendingSlotId));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const path = `/api/complaints/${encodeURIComponent(caseId)}`;

  useEffect(() => {
    const controller = new AbortController();
    api(`${path}/slots`, { signal: controller.signal }).then((choices) => { setSlots(choices); setLoaded(true); })
      .catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); });
    return () => controller.abort();
  }, [path]);

  async function submit(event) {
    event.preventDefault();
    if (!selected || pending) return;
    setPending(true);
    setLocked(true);
    setError('');
    try {
      const updated = await api(`${path}/appointment`, { method: 'POST', body: { slotId: selected.id },
        headers: { 'Idempotency-Key': requestKey.current } });
      onUpdated(updated);
      if (updated.status === 'BOOKED') onClose();
      else setError(updated.error?.message || 'Confirmation is pending. Retry this slot.');
    } catch (failure) {
      setError(failure.message);
      const latest = await api(path).catch(() => null);
      if (latest) {
        onUpdated(latest);
        if (latest.status === 'BOOKED') onClose();
        else if (latest.status === 'AWAITING_APPOINTMENT' && !latest.pendingSlotId) {
          setLocked(false);
          requestKey.current = crypto.randomUUID();
          setSlots(await api(`${path}/slots`).catch(() => []));
        }
      }
    } finally {
      setPending(false);
    }
  }

  return <Modal title="Confirm technician visit" onClose={onClose} busy={pending} dismissOnBackdrop className="appointment-dialog">
    <p className="hint">Simulated visit · All times IST.</p>
    <form onSubmit={submit}><fieldset disabled={pending}>
      {selected && loaded ? <div className="visit-summary"><strong>{formatSlot(selected.start)}</strong></div> : <p>{loaded ? 'Your preferred time is unavailable. Close this window and try again later.' : 'Loading visit time…'}</p>}
      {error ? <p className="error" role="alert">{error}</p> : null}
      <div className="dialog-actions"><button className="primary full" type="submit" disabled={!selected || !loaded}>{pending ? 'Confirming…' : locked ? 'Retry confirmation' : 'Confirm visit'}</button></div>
    </fieldset></form>
  </Modal>;
}

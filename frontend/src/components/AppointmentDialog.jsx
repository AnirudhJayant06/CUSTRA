import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client.js';

export const formatSlot = (value) => new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata',
}).format(new Date(value));

export default function AppointmentDialog({ caseId, pendingSlotId, onClose, onUpdated }) {
  const dialog = useRef(null);
  const requestKey = useRef(crypto.randomUUID());
  const [slots, setSlots] = useState([]);
  const [selected, setSelected] = useState(pendingSlotId || '');
  const [locked, setLocked] = useState(Boolean(pendingSlotId));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const path = `/api/complaints/${encodeURIComponent(caseId)}`;

  useEffect(() => {
    const previous = document.activeElement;
    const element = dialog.current;
    element.showModal();
    return () => { element.close(); previous?.focus(); };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api(`${path}/slots`, { signal: controller.signal }).then(setSlots)
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
      const updated = await api(`${path}/appointment`, { method: 'POST', body: { slotId: selected },
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

  return <dialog className="dialog-card appointment-dialog" ref={dialog} aria-labelledby="appointment-title"
    onCancel={(event) => { event.preventDefault(); if (!pending) onClose(); }}>
    <h2 id="appointment-title">Choose an appointment</h2>
    <p>Simulated availability · All times in IST (Asia/Kolkata).</p>
    <form onSubmit={submit}>
      <fieldset disabled={pending}>
        <legend>Available dated slots</legend>
        {slots.map((slot) => <label className="slot-option" key={slot.id}>
          <input type="radio" name="slot" value={slot.id} checked={selected === slot.id}
            disabled={locked && selected !== slot.id} onChange={() => setSelected(slot.id)} />
          {formatSlot(slot.start)} – {new Intl.DateTimeFormat('en-IN', { timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(slot.end))}
        </label>)}
        {!slots.length && !error ? <p role="status">Loading slots…</p> : null}
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="dialog-actions">
          <button className="secondary" type="button" onClick={onClose}>Choose later</button>
          <button className="submit" type="submit" disabled={!selected}>{pending ? 'Confirming…' : locked ? 'Retry confirmation' : 'Confirm appointment'}</button>
        </div>
      </fieldset>
    </form>
  </dialog>;
}

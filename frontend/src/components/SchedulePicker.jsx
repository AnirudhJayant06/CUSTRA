import { useState } from 'react';
import Modal from './Modal.jsx';
import { dateLabel, slotLabel, timeLabel } from '../lib/domain.js';
export const slotDate = (slot) => slot.date || slot.start.slice(0, 10);
export default function SchedulePicker({ slots, initialSlotId = '', onClose, onSelect, confirmLabel = 'Save preference', locked = false, initialMode }) {
  const initial = slots.find((s) => s.id === initialSlotId);
  const dates = [...new Set(slots.map(slotDate))].sort();
  const [selectedDate, setDate] = useState(initial ? slotDate(initial) : '');
  const [selectedId, setSelected] = useState(initial?.id || '');
  const [mode, setMode] = useState(initialMode || (initial ? 'time' : 'date'));
  const [month, setMonth] = useState((initial ? slotDate(initial) : dates[0] || new Date().toISOString()).slice(0, 7));
  const [year, mon] = month.split('-').map(Number);
  const firstWeekday = new Date(Date.UTC(year, mon - 1, 1)).getUTCDay();
  const dayCount = new Date(Date.UTC(year, mon, 0)).getUTCDate();
  const selected = slots.find((s) => s.id === selectedId && s.available !== false);
  const offered = slots.filter((s) => slotDate(s) === selectedDate);
  const hours = Array.from({ length: 9 }, (_, i) => i + 9);
  const times = offered.length ? hours.map((hour) => {
    const start = `${selectedDate}T${String(hour).padStart(2, '0')}:00:00+05:30`;
    return offered.find((s) => new Date(s.start).getTime() === new Date(start).getTime()) || { id: `unavailable-${hour}`, start, end: `${selectedDate}T${String(hour + 1).padStart(2, '0')}:00:00+05:30`, available: false };
  }) : [];
  function moveMonth(delta) {
    const next = new Date(Date.UTC(year, mon - 1 + delta, 1)).toISOString().slice(0, 7);
    setMonth(next);
  }
  return <Modal title={mode === 'date' ? 'Preferred date' : 'Preferred time'} onClose={onClose} className="schedule-dialog" dismissOnBackdrop>
    {mode === 'date' ? <><div className="calendar-heading"><button className="icon-button" aria-label="Previous month" disabled={!dates.length || month <= dates[0].slice(0, 7) || locked} onClick={() => moveMonth(-1)}>‹</button><strong>{new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(year, mon - 1, 1)))}</strong><button className="icon-button" aria-label="Next month" disabled={!dates.length || month >= dates.at(-1).slice(0, 7) || locked} onClick={() => moveMonth(1)}>›</button></div>
      <div className="calendar-grid">{['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => <span className="weekday" key={d}>{d}</span>)}{Array.from({ length: firstWeekday }, (_, i) => <span key={`blank-${i}`} />)}{Array.from({ length: dayCount }, (_, i) => {
        const value = `${month}-${String(i + 1).padStart(2, '0')}`;
        const available = slots.some((s) => slotDate(s) === value && s.available !== false);
        return <button key={value} className={selectedDate === value ? 'selected' : ''} type="button" disabled={!available || locked && value !== selectedDate} aria-label={`${dateLabel(value)}${available ? '' : ', unavailable'}`} aria-pressed={selectedDate === value} onClick={() => { if (selectedDate !== value) setSelected(''); setDate(value); setMode('time'); }}>{i + 1}</button>;
      })}</div><p className="hint">Choose an available date · Demo availability · IST</p>{!dates.length ? <p role="status">No visit times are available. Please try later.</p> : null}</> : <>
      <div className="section-heading"><strong>{dateLabel(selectedDate)}</strong><button className="text-button" disabled={locked} onClick={() => setMode('date')}>Change date</button></div><p className="hint">All times IST · Demo availability</p>
      <div className="time-grid" role="radiogroup" aria-label="Visit times">{times.map((s) => <label className={`time-tile ${selectedId === s.id ? 'selected' : ''} ${s.available === false ? 'unavailable' : ''}`} key={s.id}>
        <input type="radio" name="visit-time" aria-label={slotLabel(s)} value={s.id} checked={selectedId === s.id} disabled={s.available === false || locked && selectedId !== s.id} onChange={() => setSelected(s.id)} /><span>{timeLabel(s.start)}<br />{timeLabel(s.end)}</span><small>{s.available === false ? 'Unavailable' : selectedId === s.id ? 'Selected' : 'Available'}</small>
      </label>)}</div><div className="dialog-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={!selected} onClick={() => onSelect(selected)}>{confirmLabel}</button></div>
    </>}
  </Modal>;
}
